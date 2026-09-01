"""Deterministic zero-call qualification for opt-in Lean V20 epoch parity."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from patchloop.agent.lean_runtime import (
    LEAN_CONTEXT_POLICY_VERSION_V20,
    LEAN_REQUEST_EVIDENCE_SCHEMA_V20,
    LEAN_RUNTIME_POLICY_VERSION_V20,
    LEAN_SEMANTIC_PROGRESS_EPOCH_PARITY_POLICY_VERSION_V20,
    LEAN_TOOL_SCHEMA_VERSION_V20,
)
from patchloop.agent.workflow_semantic_progress_epoch_parity import (
    SEMANTIC_PROGRESS_EVENT_DOMAIN_SCHEMA,
    project_semantic_progress_event_domain,
    select_semantic_progress_epoch_events,
)
from patchloop.contracts import EventType, RunEvent
from patchloop.errors import ContractError, RecoveryError
from patchloop.util import canonical_json, ensure_within, sha256_bytes, sha256_json

SCHEMA_VERSION = "lean-semantic-progress-epoch-parity-qualification-v1"
QUALIFICATION_PATH = Path(
    "experiments/lean-harness-semantic-progress-epoch-parity-public-qualification-20260827-v1.json"
)
RUN_ID = "run_r15_shaped_semantic_progress_epoch_parity"

IMMUTABLE_PREDECESSORS = {
    (
        "experiments/lean-harness-exploration-gate-activation-public-qualification-20260827-v1.json"
    ): {
        "bytes": 4_925,
        "file_sha256": ("sha256:a25881f54e66a11ef6f3ca9b41d0cf44ce7a37ec1b2fe7fd1efbade0994462c5"),
        "content_hash": ("sha256:1beb02b77f1b4d9985babe4e64dab4e09cc805bc87fabfa9733dec3f0d2bcb9a"),
    },
    (
        "reports/rapid-development/"
        "rapid-public-dev-anyio-v5-exploration-ab-20260827-r15-3e5890091927.jsonl"
    ): {
        "bytes": 6_755,
        "file_sha256": ("sha256:cec339cb9682956ec2bcbdcd5cd81d4e9d0f2539e538d545bff4821836787e88"),
        "final_event_hash": (
            "sha256:23c7a4e99868864c38de15ac5d3b4ba8fe7a3df0dc865207030510555d1ccdd3"
        ),
    },
    (
        "reports/rapid-development/artifacts/"
        "rapid-public-dev-anyio-v5-exploration-ab-20260827-r15-"
        "workflow-diagnosis-v1.json"
    ): {
        "bytes": 6_162,
        "file_sha256": ("sha256:4382b8bd3e391c801803447c27bb7fe62c24c825a17e2ad5d9d075625ea956d7"),
        "content_hash": ("sha256:52c2afaa7cbd87a36aa06bc9c0ba427cbc16948f817095548a79c1a7dff1ec00"),
    },
}

SOURCE_FILES = (
    "patchloop/agent/workflow_semantic_progress_epoch_parity.py",
    "patchloop/agent/workflow_semantic_progress_epoch_parity_qualification.py",
    "patchloop/agent/lean_runtime.py",
    "patchloop/agent/tools.py",
    "patchloop/agent/runner.py",
    "patchloop/contracts.py",
    "scripts/build_lean_harness_semantic_progress_epoch_parity_qualification.py",
    "tests/test_workflow_semantic_progress_epoch_parity.py",
    "tests/test_workflow_semantic_progress_epoch_parity_qualification.py",
    "tests/test_workflow_successor_v2_runner.py",
)


def _source_identity(root: Path, relative: str) -> dict[str, Any]:
    selected = ensure_within(root, relative)
    if selected.is_symlink() or not selected.is_file():
        raise ContractError(f"semantic epoch-parity source is unavailable: {relative}")
    raw = selected.read_bytes()
    return {
        "path": relative,
        "bytes": len(raw),
        "file_sha256": sha256_bytes(raw),
    }


def _predecessor_identity(root: Path, relative: str) -> dict[str, Any]:
    identity = _source_identity(root, relative)
    expected = IMMUTABLE_PREDECESSORS[relative]
    selected = ensure_within(root, relative)
    raw = selected.read_bytes()
    if "content_hash" in expected:
        try:
            document = json.loads(raw)
        except (UnicodeDecodeError, ValueError) as exc:
            raise ContractError("semantic epoch-parity predecessor is not JSON") from exc
        content_hash = document.get("content_hash")
        if content_hash != sha256_json(
            {key: item for key, item in document.items() if key != "content_hash"}
        ):
            raise ContractError("semantic epoch-parity predecessor content hash differs")
        identity["content_hash"] = content_hash
    if "final_event_hash" in expected:
        try:
            final_event = json.loads(raw.splitlines()[-1])
        except (IndexError, UnicodeDecodeError, ValueError) as exc:
            raise ContractError("semantic epoch-parity predecessor is not JSONL") from exc
        if final_event.get("event") != "batch-completed":
            raise ContractError("semantic epoch-parity predecessor lacks completion")
        identity["final_event_hash"] = final_event.get("content_hash")
    if {key: identity.get(key) for key in expected} != expected:
        raise ContractError(f"immutable semantic epoch predecessor differs: {relative}")
    return identity


def _event(
    sequence: int,
    event_type: EventType,
    *,
    run_id: str = RUN_ID,
) -> RunEvent:
    return RunEvent(
        event_id=f"evt_r15_epoch_parity_{sequence}",
        run_id=run_id,
        sequence=sequence,
        type=event_type,
        timestamp=datetime(2026, 8, 27, tzinfo=UTC),
        actor="qualification",
        correlation_id=None,
        payload={},
    )


def _r15_shaped_request_events() -> tuple[RunEvent, ...]:
    return (
        _event(74, EventType.TOOL_SUCCEEDED),
        _event(103, EventType.TOOL_SUCCEEDED),
        _event(106, EventType.MUTATION_BASELINE_RESTORED),
        _event(135, EventType.TOOL_SUCCEEDED),
        _event(152, EventType.MODEL_CALLED),
    )


def _recovery_message(callable_: Any) -> str:
    try:
        callable_()
    except RecoveryError as exc:
        return str(exc)
    raise ContractError("semantic epoch-parity qualification expected rejection")


def _scenarios() -> dict[str, Any]:
    request_events = _r15_shaped_request_events()
    request_domain = project_semantic_progress_event_domain(
        run_id=RUN_ID,
        events=request_events,
    )
    request_selection = select_semantic_progress_epoch_events(
        domain=request_domain,
        events=request_events,
    )
    dispatch_events = (*request_events, _event(153, EventType.TOOL_CALLED))
    dispatch_selection = select_semantic_progress_epoch_events(
        domain=request_domain,
        events=dispatch_events,
    )
    independently_recomputed_dispatch_domain = project_semantic_progress_event_domain(
        run_id=RUN_ID,
        events=dispatch_events,
    )
    tampered = request_domain.model_copy(update={"epoch_event_sequences": (103, 135, 152)})
    foreign = (*request_events, _event(153, EventType.TOOL_CALLED, run_id="foreign"))
    non_monotonic = (
        _event(2, EventType.MODEL_CALLED),
        _event(1, EventType.TOOL_CALLED),
    )

    return {
        "runtime_identity": {
            "runtime_policy_version": LEAN_RUNTIME_POLICY_VERSION_V20,
            "tool_schema_version": LEAN_TOOL_SCHEMA_VERSION_V20,
            "context_policy_version": LEAN_CONTEXT_POLICY_VERSION_V20,
            "request_evidence_schema": LEAN_REQUEST_EVIDENCE_SCHEMA_V20,
            "epoch_parity_policy_version": (LEAN_SEMANTIC_PROGRESS_EPOCH_PARITY_POLICY_VERSION_V20),
            "event_domain_schema": SEMANTIC_PROGRESS_EVENT_DOMAIN_SCHEMA,
        },
        "r15_shaped_epoch": {
            "request_source_event_sequences": [event.sequence for event in request_events],
            "latest_restore_event_sequence": (request_domain.latest_restore_event_sequence),
            "request_epoch_event_sequences": list(request_domain.epoch_event_sequences),
            "request_selected_event_sequences": [event.sequence for event in request_selection],
            "dispatch_appended_event_sequence": 153,
            "dispatch_selected_event_sequences": [event.sequence for event in dispatch_selection],
            "independent_full_dispatch_domain_differs": (
                independently_recomputed_dispatch_domain != request_domain
            ),
            "request_domain_hash": request_domain.content_hash,
            "event_type_sequence_hash": request_domain.event_type_sequence_hash,
            "event_payloads_projected": request_domain.event_payloads_projected,
        },
        "fail_closed": {
            "tampered_domain": _recovery_message(
                lambda: select_semantic_progress_epoch_events(
                    domain=tampered,
                    events=request_events,
                )
            ),
            "foreign_run": _recovery_message(
                lambda: project_semantic_progress_event_domain(
                    run_id=RUN_ID,
                    events=foreign,
                )
            ),
            "non_monotonic_prefix": _recovery_message(
                lambda: project_semantic_progress_event_domain(
                    run_id=RUN_ID,
                    events=non_monotonic,
                )
            ),
        },
        "preserved_limits": {
            "v18_behavior_modified": False,
            "v19_behavior_modified": False,
            "r15_retry_allowed": False,
            "request_payloads_or_reasoning_replayed": False,
            "runtime_activation_is_opt_in": True,
            "rapid_candidate_created": False,
        },
    }


def build_workflow_semantic_progress_epoch_parity_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    predecessors = [_predecessor_identity(root, relative) for relative in IMMUTABLE_PREDECESSORS]
    body = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime(2026, 8, 27, tzinfo=UTC).isoformat(),
        "status": "offline-qualified",
        "scope": "lean-v20-public-semantic-progress-epoch-parity",
        "scenarios": _scenarios(),
        "source_files": [_source_identity(root, relative) for relative in SOURCE_FILES],
        "immutable_predecessors": predecessors,
        "evidence_boundary": {
            "public_synthetic_event_envelopes_only": True,
            "event_payloads_read": False,
            "task_fixture_files_read": False,
            "private_task_spec_read": False,
            "hidden_evaluator_content_read": False,
            "reference_patch_read": False,
            "reasoning_text_read": False,
            "provider_calls": 0,
            "docker_calls": 0,
            "evaluator_calls": 0,
            "visible_check_calls": 0,
            "workspace_mutations": 0,
            "added_cost_usd": "0",
        },
        "runtime_surface_activated": True,
        "rapid_candidate_created": False,
        "paid_execution_authorized": False,
        "quality_improvement_established": False,
        "generalization_established": False,
    }
    return {**body, "content_hash": sha256_json(body)}


def qualification_bytes(value: dict[str, Any]) -> bytes:
    body = {key: item for key, item in value.items() if key != "content_hash"}
    if value.get("content_hash") != sha256_json(body):
        raise ContractError("semantic epoch-parity qualification hash differs")
    return (canonical_json(value) + "\n").encode("utf-8")


def materialize_workflow_semantic_progress_epoch_parity_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    value = build_workflow_semantic_progress_epoch_parity_qualification(root)
    target = ensure_within(root, QUALIFICATION_PATH.as_posix())
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(qualification_bytes(value))
    return value


def load_workflow_semantic_progress_epoch_parity_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    target = ensure_within(root, QUALIFICATION_PATH.as_posix())
    try:
        raw = target.read_bytes()
        value = json.loads(raw)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ContractError("semantic epoch-parity qualification is unavailable") from exc
    if qualification_bytes(value) != raw:
        raise ContractError("semantic epoch-parity qualification bytes differ")
    if value != build_workflow_semantic_progress_epoch_parity_qualification(root):
        raise ContractError("semantic epoch-parity source binding differs")
    return value


__all__ = [
    "IMMUTABLE_PREDECESSORS",
    "QUALIFICATION_PATH",
    "SCHEMA_VERSION",
    "SOURCE_FILES",
    "build_workflow_semantic_progress_epoch_parity_qualification",
    "load_workflow_semantic_progress_epoch_parity_qualification",
    "materialize_workflow_semantic_progress_epoch_parity_qualification",
    "qualification_bytes",
]
