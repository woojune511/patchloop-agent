from __future__ import annotations

import json
from pathlib import Path

from patchloop.agent.workflow_semantic_progress_epoch_parity_rapid_activation_qualification import (
    QUALIFICATION_PATH,
    SOURCE_FILES,
    qualification_bytes,
)
from patchloop.util import sha256_bytes

ROOT = Path(__file__).resolve().parents[1]


def _stored() -> tuple[bytes, dict[str, object]]:
    raw = (ROOT / QUALIFICATION_PATH).read_bytes()
    return raw, json.loads(raw)


def test_consumed_v20_rapid_activation_is_canonical_and_zero_call() -> None:
    raw, value = _stored()

    assert raw == qualification_bytes(value)
    assert value["status"] == "offline-qualified"
    assert value["runtime_activation_authorized"] is False
    assert value["rapid_candidate_created_by_qualification"] is False
    assert value["paid_execution_authorized"] is False
    assert all(
        value["evidence_boundary"][key] == 0
        for key in (
            "provider_calls",
            "docker_calls",
            "task_calls",
            "evaluator_calls",
            "visible_check_calls",
            "workspace_mutations",
        )
    )


def test_consumed_v20_rapid_activation_binds_recorded_runtime_and_delta() -> None:
    _, value = _stored()

    assert value["runtime_identity"] == {
        "runtime_policy_version": "lean-harness-v20",
        "tool_schema_version": "v24",
        "context_policy_version": "phase-evidence-v30",
        "request_evidence_schema": "lean-harness-request-evidence-v20",
        "exploration_gate_policy_version": "public-boundary-and-unknown-closure-v1",
        "exploration_gate_activation_policy_version": (
            "gateway-owned-public-exploration-closure-v1"
        ),
        "epoch_parity_policy_version": ("post-restore-semantic-progress-epoch-parity-v1"),
    }
    preservation = value["source_preservation"]
    assert preservation["qualified_behavior_unchanged"] is True
    assert preservation["permitted_admission_source_changes"] == ["patchloop/contracts.py"]
    assert preservation["transition"]["observed_changed_paths"] == ["patchloop/contracts.py"]
    assert [item["path"] for item in value["source_files"]] == list(SOURCE_FILES)


def test_stored_v20_rapid_activation_is_a_canonical_byte_audit() -> None:
    raw, value = _stored()

    assert raw == qualification_bytes(value)
    assert len(raw) == 7_860
    assert sha256_bytes(raw) == (
        "sha256:c4a1a973ff2cfe57042ca8384dd6d18741f3e12430eabfd25a93ce3f7a7885e5"
    )
    assert value["content_hash"] == (
        "sha256:1f782f27413891c16eed944a2f77f20a9981fe33075cc13691a96ceeecd5de99"
    )
