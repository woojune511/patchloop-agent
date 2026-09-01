"""Second zero-call source activation qualification for the Lean V17 Rapid seam."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from patchloop.agent.workflow_causal_alternative_activation_qualification import (
    QUALIFICATION_PATH as PREDECESSOR_QUALIFICATION_PATH,
)
from patchloop.agent.workflow_causal_alternative_activation_qualification import (
    SOURCE_FILES as WORKFLOW_SOURCE_FILES,
)
from patchloop.agent.workflow_causal_alternative_activation_qualification import (
    build_workflow_causal_alternative_activation_qualification,
)
from patchloop.agent.workflow_causal_alternative_activation_qualification import (
    qualification_bytes as predecessor_qualification_bytes,
)
from patchloop.contracts import RAPID_ANYIO_CAUSAL_ACTIVATION_AB_EXPERIMENT_ID
from patchloop.errors import ContractError
from patchloop.evals.live_verifier_registry import live_verifier_registry
from patchloop.evals.rapid_public_development_v4 import _runtime_build_binding
from patchloop.util import canonical_json, ensure_within, sha256_bytes, sha256_json

SCHEMA_VERSION = "lean-causal-alternative-rapid-activation-qualification-v2"
QUALIFICATION_PATH = Path(
    "experiments/lean-harness-causal-alternative-rapid-activation-qualification-20260826-v2.json"
)
EXPERIMENT_ID = "rapid-public-dev-anyio-causal-activation-ab-20260826-r13"
PLAN_SCHEMA = "experiment-execution-plan-v20"
PLAN_KIND = "rapid-public-development-batch-v1"
VERIFIER_ID = "rapid-r13-candidate-v20-plan-v20"
PREDECESSOR_FILE_BYTES = 5_235
PREDECESSOR_FILE_SHA256 = "sha256:72576cdcf05a9337bcee415d3200bfe76f04fd8b13b3231b02140fb6b2cd448e"
PREDECESSOR_CONTENT_HASH = "sha256:45f469b256c50b7259b7c1df6a59e3b4fe8f598f67733ef93a96733b72191f85"
PERMITTED_SOURCE_CHANGES = (
    "patchloop/contracts.py",
    "tests/test_workflow_causal_alternative_activation_qualification.py",
)
ACTIVATION_SOURCE_FILES = (
    "patchloop/agent/workflow_causal_alternative_rapid_activation_qualification_v2.py",
    "patchloop/evals/live_verifier_registry.py",
    "patchloop/evals/rapid_public_development_v16.py",
)


def _identity(root: Path, relative: str) -> dict[str, Any]:
    selected = ensure_within(root, relative)
    if selected.is_symlink() or not selected.is_file():
        raise ContractError(f"causal Rapid activation source is unavailable: {relative}")
    raw = selected.read_bytes()
    return {"path": relative, "bytes": len(raw), "file_sha256": sha256_bytes(raw)}


def _predecessor(root: Path) -> tuple[dict[str, Any], bytes]:
    selected = ensure_within(root, PREDECESSOR_QUALIFICATION_PATH.as_posix())
    if selected.is_symlink() or not selected.is_file():
        raise ContractError("causal Rapid predecessor qualification is unavailable")
    raw = selected.read_bytes()
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, ValueError) as exc:
        raise ContractError("causal Rapid predecessor qualification is invalid") from exc
    if not (
        isinstance(value, dict)
        and len(raw) == PREDECESSOR_FILE_BYTES
        and sha256_bytes(raw) == PREDECESSOR_FILE_SHA256
        and value.get("content_hash") == PREDECESSOR_CONTENT_HASH
        and predecessor_qualification_bytes(value) == raw
        and value.get("runtime_activation_authorized") is False
        and value.get("rapid_candidate_created") is False
    ):
        raise ContractError("causal Rapid predecessor qualification differs")
    return value, raw


def _semantic_projection(value: dict[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if key not in {"content_hash", "source_files"}}


def _source_transition(
    root: Path,
    predecessor: dict[str, Any],
    current: dict[str, Any],
) -> dict[str, Any]:
    prior_by_path = {item["path"]: item for item in predecessor["source_files"]}
    current_by_path = {item["path"]: item for item in current["source_files"]}
    if tuple(prior_by_path) != WORKFLOW_SOURCE_FILES or tuple(current_by_path) != (
        WORKFLOW_SOURCE_FILES
    ):
        raise ContractError("causal Rapid activation source inventory differs")
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
        raise ContractError("causal Rapid activation change surface differs")
    if _semantic_projection(predecessor) != _semantic_projection(current):
        raise ContractError("causal Rapid activation changed qualified behavior")
    return {
        "schema_version": "lean-causal-alternative-source-transition-v1",
        "permitted_changed_paths": list(PERMITTED_SOURCE_CHANGES),
        "observed_changed_paths": changed,
        "change_role": "r13-manifest-opt-in-and-predecessor-audit-only",
        "qualified_behavior_unchanged": True,
        "rows": rows,
    }


def build_workflow_causal_alternative_rapid_activation_qualification_v2(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    predecessor, predecessor_raw = _predecessor(root)
    current = build_workflow_causal_alternative_activation_qualification(root)
    transition = _source_transition(root, predecessor, current)
    if RAPID_ANYIO_CAUSAL_ACTIVATION_AB_EXPERIMENT_ID != EXPERIMENT_ID:
        raise ContractError("causal Rapid experiment registration differs")
    descriptor_hash = live_verifier_registry().descriptor_hash_for(
        experiment_id=EXPERIMENT_ID,
        plan_schema=PLAN_SCHEMA,
        plan_kind=PLAN_KIND,
    )
    runtime_build_hash, dependencies = _runtime_build_binding(root)
    body = {
        "schema_version": SCHEMA_VERSION,
        "status": "offline-qualified",
        "scope": "lean-v17-r13-manifest-and-verifier-activation",
        "predecessor_qualification": {
            "path": PREDECESSOR_QUALIFICATION_PATH.as_posix(),
            "bytes": len(predecessor_raw),
            "file_sha256": sha256_bytes(predecessor_raw),
            "content_hash": predecessor["content_hash"],
        },
        "current_virtual_qualification": {
            "content_hash": current["content_hash"],
            "scenario_set_hash": sha256_json(current["scenarios"]),
            "source_files": current["source_files"],
        },
        "causal_activation_contract": {
            "immutable_predecessor": predecessor["immutable_predecessor"],
            "runtime_identity": predecessor["scenarios"]["runtime_identity"],
            "generic_plan_surface": predecessor["scenarios"]["generic_plan_surface"],
            "restore_trigger": predecessor["scenarios"]["restore_trigger"],
            "bounded_workflow": predecessor["scenarios"]["bounded_workflow"],
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
            "lean-harness-v17": {
                "tool_schema_version": "v21",
                "context_policy_version": "phase-evidence-v27",
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
        raise ContractError("causal Rapid activation qualification hash differs")
    return (canonical_json(value) + "\n").encode("utf-8")


def materialize_workflow_causal_alternative_rapid_activation_qualification_v2(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    value = build_workflow_causal_alternative_rapid_activation_qualification_v2(root)
    selected = ensure_within(root, QUALIFICATION_PATH.as_posix())
    raw = qualification_bytes(value)
    if selected.exists() and selected.read_bytes() != raw:
        raise ContractError("causal Rapid activation qualification already differs")
    selected.parent.mkdir(parents=True, exist_ok=True)
    selected.write_bytes(raw)
    return value


def load_workflow_causal_alternative_rapid_activation_qualification_v2(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    selected = ensure_within(root, QUALIFICATION_PATH.as_posix())
    try:
        raw = selected.read_bytes()
        value = json.loads(raw)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ContractError("causal Rapid activation qualification is unavailable") from exc
    if qualification_bytes(value) != raw:
        raise ContractError("causal Rapid activation qualification bytes differ")
    if value != build_workflow_causal_alternative_rapid_activation_qualification_v2(root):
        raise ContractError("causal Rapid activation qualification source binding differs")
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
    "build_workflow_causal_alternative_rapid_activation_qualification_v2",
    "load_workflow_causal_alternative_rapid_activation_qualification_v2",
    "materialize_workflow_causal_alternative_rapid_activation_qualification_v2",
    "qualification_bytes",
]
