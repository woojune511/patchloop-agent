from __future__ import annotations

import json
from pathlib import Path

from patchloop.agent.workflow_semantic_progress_epoch_parity_qualification import (
    IMMUTABLE_PREDECESSORS,
    QUALIFICATION_PATH,
    SOURCE_FILES,
    build_workflow_semantic_progress_epoch_parity_qualification,
    qualification_bytes,
)
from patchloop.util import sha256_bytes

ROOT = Path(__file__).resolve().parents[1]


def test_epoch_parity_qualification_is_deterministic_and_zero_call() -> None:
    first = build_workflow_semantic_progress_epoch_parity_qualification(ROOT)
    second = build_workflow_semantic_progress_epoch_parity_qualification(ROOT)

    assert qualification_bytes(first) == qualification_bytes(second)
    assert first["status"] == "offline-qualified"
    assert first["runtime_surface_activated"] is True
    assert first["rapid_candidate_created"] is False
    assert first["paid_execution_authorized"] is False
    assert first["quality_improvement_established"] is False
    assert all(
        first["evidence_boundary"][key] == 0
        for key in (
            "provider_calls",
            "docker_calls",
            "evaluator_calls",
            "visible_check_calls",
            "workspace_mutations",
        )
    )


def test_epoch_parity_qualification_reproduces_r15_request_dispatch_boundary() -> None:
    scenarios = build_workflow_semantic_progress_epoch_parity_qualification(ROOT)["scenarios"]

    assert scenarios["runtime_identity"] == {
        "runtime_policy_version": "lean-harness-v20",
        "tool_schema_version": "v24",
        "context_policy_version": "phase-evidence-v30",
        "request_evidence_schema": "lean-harness-request-evidence-v20",
        "epoch_parity_policy_version": "post-restore-semantic-progress-epoch-parity-v1",
        "event_domain_schema": "semantic-progress-event-domain-v1",
    }
    epoch = scenarios["r15_shaped_epoch"]
    assert epoch["latest_restore_event_sequence"] == 106
    assert epoch["request_epoch_event_sequences"] == [135, 152]
    assert epoch["request_selected_event_sequences"] == [135, 152]
    assert epoch["dispatch_selected_event_sequences"] == [135, 152]
    assert epoch["independent_full_dispatch_domain_differs"] is True
    assert epoch["event_payloads_projected"] is False
    assert all(
        "differs" in value or "foreign" in value or "order" in value
        for value in scenarios["fail_closed"].values()
    )


def test_epoch_parity_qualification_binds_sources_and_consumed_predecessors() -> None:
    value = build_workflow_semantic_progress_epoch_parity_qualification(ROOT)

    assert [item["path"] for item in value["source_files"]] == list(SOURCE_FILES)
    assert [item["path"] for item in value["immutable_predecessors"]] == list(
        IMMUTABLE_PREDECESSORS
    )
    for item in value["immutable_predecessors"]:
        assert {
            key: item[key] for key in IMMUTABLE_PREDECESSORS[item["path"]]
        } == IMMUTABLE_PREDECESSORS[item["path"]]


def test_stored_epoch_parity_qualification_is_a_byte_audit() -> None:
    raw = (ROOT / QUALIFICATION_PATH).read_bytes()
    value = json.loads(raw)

    assert raw == qualification_bytes(value)
    assert sha256_bytes(raw).startswith("sha256:")
