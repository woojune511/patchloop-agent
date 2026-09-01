"""Second zero-call source activation qualification for the Lean V18 Rapid seam."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from patchloop.agent.workflow_causal_plan_projection_activation_qualification import (
    QUALIFICATION_PATH as PREDECESSOR_QUALIFICATION_PATH,
)
from patchloop.agent.workflow_causal_plan_projection_activation_qualification import (
    SOURCE_FILES as WORKFLOW_SOURCE_FILES,
)
from patchloop.agent.workflow_causal_plan_projection_activation_qualification import (
    build_workflow_causal_plan_projection_activation_qualification,
)
from patchloop.agent.workflow_causal_plan_projection_activation_qualification import (
    qualification_bytes as predecessor_qualification_bytes,
)
from patchloop.agent.workflow_causal_plan_projection_rapid_activation_qualification import (
    qualification_bytes as superseded_qualification_bytes,
)
from patchloop.contracts import (
    RAPID_ANYIO_CAUSAL_PLAN_PROJECTION_AB_EXPERIMENT_ID,
)
from patchloop.errors import ContractError
from patchloop.evals.live_verifier_registry import live_verifier_registry
from patchloop.evals.rapid_public_development_v4 import _runtime_build_binding
from patchloop.util import canonical_json, ensure_within, sha256_bytes, sha256_json

SCHEMA_VERSION = "lean-causal-plan-projection-rapid-activation-qualification-v2"
QUALIFICATION_PATH = Path(
    "experiments/"
    "lean-harness-causal-plan-projection-rapid-activation-qualification-20260826-v2.json"
)
EXPERIMENT_ID = "rapid-public-dev-anyio-causal-plan-projection-ab-20260826-r14"
PLAN_SCHEMA = "experiment-execution-plan-v21"
PLAN_KIND = "rapid-public-development-batch-v1"
VERIFIER_ID = "rapid-r14-candidate-v21-plan-v21"
PREDECESSOR_FILE_BYTES = 5_438
PREDECESSOR_FILE_SHA256 = "sha256:7f4b75a80c8085cdcf3beca1f9693077f97596ba719f3bdece5c9d5553cefa8b"
PREDECESSOR_CONTENT_HASH = "sha256:359b3bc8b2067bcd9b42f3c8dbbc5d8894d04a0611948c44a1d83d2995979754"
PERMITTED_SOURCE_CHANGES = (
    "patchloop/contracts.py",
    "tests/test_workflow_causal_plan_projection_activation_qualification.py",
)
SUPERSEDED_ACTIVATION_PATH = Path(
    "experiments/"
    "lean-harness-causal-plan-projection-rapid-activation-qualification-20260826-v1.json"
)
SUPERSEDED_ACTIVATION_BYTES = 11_055
SUPERSEDED_ACTIVATION_FILE_SHA256 = (
    "sha256:2d4f2c797679c58162dc659d39f844c4eac08fc07d4c2d1de1fef17494cd10bb"
)
SUPERSEDED_ACTIVATION_CONTENT_HASH = (
    "sha256:ad363df97aa1eb6012174198337c8cb6be32110d88386a4713714b99fb4625a7"
)
ACTIVATION_SOURCE_FILES = (
    "patchloop/agent/workflow_causal_plan_projection_rapid_activation_qualification_v2.py",
    "patchloop/evals/live_verifier_registry.py",
    "patchloop/evals/rapid_public_development_v17.py",
)


def _identity(root: Path, relative: str) -> dict[str, Any]:
    selected = ensure_within(root, relative)
    if selected.is_symlink() or not selected.is_file():
        raise ContractError(f"causal-plan Rapid activation source is unavailable: {relative}")
    raw = selected.read_bytes()
    return {"path": relative, "bytes": len(raw), "file_sha256": sha256_bytes(raw)}


def _predecessor(root: Path) -> tuple[dict[str, Any], bytes]:
    selected = ensure_within(root, PREDECESSOR_QUALIFICATION_PATH.as_posix())
    if selected.is_symlink() or not selected.is_file():
        raise ContractError("causal-plan Rapid predecessor qualification is unavailable")
    raw = selected.read_bytes()
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, ValueError) as exc:
        raise ContractError("causal-plan Rapid predecessor qualification is invalid") from exc
    if not (
        isinstance(value, dict)
        and len(raw) == PREDECESSOR_FILE_BYTES
        and sha256_bytes(raw) == PREDECESSOR_FILE_SHA256
        and value.get("content_hash") == PREDECESSOR_CONTENT_HASH
        and predecessor_qualification_bytes(value) == raw
        and value.get("runtime_activation_authorized") is True
        and value.get("rapid_candidate_created") is False
        and value.get("paid_execution_authorized") is False
    ):
        raise ContractError("causal-plan Rapid predecessor qualification differs")
    return value, raw


def _semantic_projection(value: dict[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if key not in {"content_hash", "source_files"}}


def _source_transition(
    predecessor: dict[str, Any],
    current: dict[str, Any],
) -> dict[str, Any]:
    prior_by_path = {item["path"]: item for item in predecessor["source_files"]}
    current_by_path = {item["path"]: item for item in current["source_files"]}
    if tuple(prior_by_path) != WORKFLOW_SOURCE_FILES or tuple(current_by_path) != (
        WORKFLOW_SOURCE_FILES
    ):
        raise ContractError("causal-plan Rapid activation source inventory differs")
    rows: list[dict[str, Any]] = []
    changed: list[str] = []
    for relative in WORKFLOW_SOURCE_FILES:
        prior = prior_by_path[relative]
        now = current_by_path[relative]
        is_changed = prior != now
        if is_changed:
            changed.append(relative)
        rows.append(
            {
                "path": relative,
                "predecessor_bytes": prior["bytes"],
                "predecessor_file_sha256": prior["file_sha256"],
                "current_bytes": now["bytes"],
                "current_file_sha256": now["file_sha256"],
                "changed": is_changed,
            }
        )
    if tuple(changed) != PERMITTED_SOURCE_CHANGES:
        raise ContractError("causal-plan Rapid activation change surface differs")
    if _semantic_projection(predecessor) != _semantic_projection(current):
        raise ContractError("causal-plan Rapid activation changed qualified behavior")
    return {
        "schema_version": "lean-causal-plan-projection-source-transition-v1",
        "permitted_changed_paths": list(PERMITTED_SOURCE_CHANGES),
        "observed_changed_paths": changed,
        "change_role": "r14-manifest-opt-in-and-predecessor-audit-only",
        "qualified_behavior_unchanged": True,
        "rows": rows,
    }


def _superseded_activation(root: Path) -> dict[str, Any]:
    selected = ensure_within(root, SUPERSEDED_ACTIVATION_PATH.as_posix())
    if selected.is_symlink() or not selected.is_file():
        raise ContractError("superseded causal-plan Rapid activation is unavailable")
    raw = selected.read_bytes()
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, ValueError) as exc:
        raise ContractError("superseded causal-plan Rapid activation is invalid") from exc
    if not (
        isinstance(value, dict)
        and len(raw) == SUPERSEDED_ACTIVATION_BYTES
        and sha256_bytes(raw) == SUPERSEDED_ACTIVATION_FILE_SHA256
        and value.get("content_hash") == SUPERSEDED_ACTIVATION_CONTENT_HASH
        and superseded_qualification_bytes(value) == raw
        and value.get("candidate_created_by_qualification") is False
        and value.get("paid_execution_authorized") is False
    ):
        raise ContractError("superseded causal-plan Rapid activation differs")
    return {
        "path": SUPERSEDED_ACTIVATION_PATH.as_posix(),
        "bytes": len(raw),
        "file_sha256": sha256_bytes(raw),
        "content_hash": value["content_hash"],
        "superseded_zero_call": True,
    }


def build_workflow_causal_plan_projection_rapid_activation_qualification_v2(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    predecessor, predecessor_raw = _predecessor(root)
    superseded = _superseded_activation(root)
    current = build_workflow_causal_plan_projection_activation_qualification(root)
    transition = _source_transition(predecessor, current)
    if RAPID_ANYIO_CAUSAL_PLAN_PROJECTION_AB_EXPERIMENT_ID != EXPERIMENT_ID:
        raise ContractError("causal-plan Rapid experiment registration differs")
    descriptor_hash = live_verifier_registry().descriptor_hash_for(
        experiment_id=EXPERIMENT_ID,
        plan_schema=PLAN_SCHEMA,
        plan_kind=PLAN_KIND,
    )
    runtime_build_hash, dependencies = _runtime_build_binding(root)
    body = {
        "schema_version": SCHEMA_VERSION,
        "status": "offline-qualified",
        "scope": "lean-v18-r14-manifest-and-verifier-activation-v2",
        "predecessor_qualification": {
            "path": PREDECESSOR_QUALIFICATION_PATH.as_posix(),
            "bytes": len(predecessor_raw),
            "file_sha256": sha256_bytes(predecessor_raw),
            "content_hash": predecessor["content_hash"],
        },
        "superseded_activation": superseded,
        "current_virtual_qualification": {
            "content_hash": current["content_hash"],
            "scenario_set_hash": sha256_json(current["scenarios"]),
            "source_files": current["source_files"],
        },
        "causal_plan_projection_contract": {
            "immutable_predecessors": predecessor["immutable_predecessors"],
            "runtime_identity": predecessor["scenarios"]["runtime_identity"],
            "dynamic_model_surface": predecessor["scenarios"]["dynamic_model_surface"],
            "cross_reset_evidence_boundary": predecessor["scenarios"][
                "cross_reset_evidence_boundary"
            ],
            "durable_v2_binding": predecessor["scenarios"]["durable_v2_binding"],
            "preserved_limits": predecessor["scenarios"]["preserved_limits"],
            "preservation_boundary": predecessor["preservation_boundary"],
        },
        "source_transition": transition,
        "activation_source_files": [_identity(root, item) for item in ACTIVATION_SOURCE_FILES],
        "runtime_build_schema": "rapid-runtime-build-v1",
        "runtime_build_hash": runtime_build_hash,
        "runtime_dependencies": dependencies,
        "experiment_id": EXPERIMENT_ID,
        "plan_schema": PLAN_SCHEMA,
        "plan_kind": PLAN_KIND,
        "verifier_id": VERIFIER_ID,
        "verifier_descriptor_hash": descriptor_hash,
        "variant_contracts": {
            "lean-harness-v8": {
                "tool_schema_version": "v12",
                "context_policy_version": "phase-evidence-v18",
            },
            "lean-harness-v18": {
                "tool_schema_version": "v22",
                "context_policy_version": "phase-evidence-v28",
            },
        },
        "manifest_admission_exercised": False,
        "production_order_rehearsal_exercised": False,
        "evidence_boundary": {
            "provider_calls": 0,
            "docker_calls": 0,
            "task_calls": 0,
            "evaluator_calls": 0,
            "visible_check_calls": 0,
            "added_model_cost_usd": "0",
        },
        "candidate_created_by_qualification": False,
        "runtime_activation_authorized": False,
        "paid_execution_authorized": False,
        "quality_improvement_established": False,
        "generalization_established": False,
    }
    return {**body, "content_hash": sha256_json(body)}


def qualification_bytes(value: dict[str, Any]) -> bytes:
    body = {key: item for key, item in value.items() if key != "content_hash"}
    if value.get("content_hash") != sha256_json(body):
        raise ContractError("causal-plan Rapid activation qualification hash differs")
    return (canonical_json(value) + "\n").encode("utf-8")


def materialize_workflow_causal_plan_projection_rapid_activation_qualification_v2(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    value = build_workflow_causal_plan_projection_rapid_activation_qualification_v2(root)
    selected = ensure_within(root, QUALIFICATION_PATH.as_posix())
    raw = qualification_bytes(value)
    if selected.exists() and selected.read_bytes() != raw:
        raise ContractError("causal-plan Rapid activation qualification already differs")
    selected.parent.mkdir(parents=True, exist_ok=True)
    selected.write_bytes(raw)
    return value


def load_workflow_causal_plan_projection_rapid_activation_qualification_v2(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    selected = ensure_within(root, QUALIFICATION_PATH.as_posix())
    try:
        raw = selected.read_bytes()
        value = json.loads(raw)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ContractError("causal-plan Rapid activation qualification is unavailable") from exc
    if qualification_bytes(value) != raw:
        raise ContractError("causal-plan Rapid activation qualification bytes differ")
    if value != build_workflow_causal_plan_projection_rapid_activation_qualification_v2(root):
        raise ContractError("causal-plan Rapid activation qualification source binding differs")
    return value


__all__ = [
    "ACTIVATION_SOURCE_FILES",
    "EXPERIMENT_ID",
    "PLAN_KIND",
    "PLAN_SCHEMA",
    "QUALIFICATION_PATH",
    "SCHEMA_VERSION",
    "VERIFIER_ID",
    "WORKFLOW_SOURCE_FILES",
    "build_workflow_causal_plan_projection_rapid_activation_qualification_v2",
    "load_workflow_causal_plan_projection_rapid_activation_qualification_v2",
    "materialize_workflow_causal_plan_projection_rapid_activation_qualification_v2",
    "qualification_bytes",
]
