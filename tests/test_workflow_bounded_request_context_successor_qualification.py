from __future__ import annotations

import json
from pathlib import Path

import pytest

from patchloop.agent.completion_loop_successor import project_current_edit_correction_context
from patchloop.agent.workflow_bounded_request_context_successor import (
    project_bounded_investigation_request_context,
)
from patchloop.agent.workflow_bounded_request_context_successor_qualification import (
    IMMUTABLE_V23_INPUTS,
    QUALIFICATION_PATH,
    SOURCE_FILES,
    _source_context,
    build_bounded_request_context_successor_qualification,
    qualification_bytes,
)
from patchloop.errors import ContractError
from patchloop.util import canonical_json, sha256_bytes

ROOT = Path(__file__).resolve().parents[1]


def test_v24_qualification_is_deterministic_source_bound_and_zero_call() -> None:
    first = build_bounded_request_context_successor_qualification(ROOT)
    second = build_bounded_request_context_successor_qualification(ROOT)

    assert qualification_bytes(first) == qualification_bytes(second)
    assert first["status"] == "offline-qualified"
    assert first["candidate_created"] is False
    assert first["external_calls"] == 0
    assert [item["path"] for item in first["source_files"]] == list(SOURCE_FILES)
    assert [item["path"] for item in first["immutable_v23_inputs"]] == list(IMMUTABLE_V23_INPUTS)
    assert all(
        first["evidence_boundary"][key] == 0
        for key in (
            "provider_calls",
            "docker_calls",
            "evaluator_calls",
            "visible_check_calls",
            "network_calls",
        )
    )


def test_v24_qualification_records_exact_surface_and_bounded_copy() -> None:
    value = build_bounded_request_context_successor_qualification(ROOT)
    scenarios = value["scenarios"]
    surface = scenarios["exact_pre_plan_surface"]
    bounded = scenarios["bounded_context"]

    assert surface["run_check_removed"] is True
    assert surface["projected_tool_names"] == [
        "search_files",
        "read_file",
        "record_work_plan",
    ]
    assert surface["inactive_projection_changes_surface"] is False
    assert bounded["projected_context_bytes"] < bounded["source_context_bytes"]
    assert bounded["retained_search_inventory_count"] == 0
    assert bounded["retained_detail_count"] <= 3
    assert bounded["retained_token_observation_count"] <= 3
    assert bounded["retained_usable_source_body_count"] >= 1
    assert bounded["source_ledger_content_hash"] == bounded["projected_ledger_source_hash"]
    assert bounded["durable_event_changed"] is False
    assert bounded["durable_ledger_changed"] is False


def test_v24_projection_does_not_mutate_source_and_rejects_ledger_tamper() -> None:
    correction = project_current_edit_correction_context(_source_context())
    source_before = correction.rendered

    project_bounded_investigation_request_context(correction)

    assert correction.rendered == source_before
    tampered = json.loads(source_before)
    tampered["investigation_ledger"]["searches"] = []
    tampered_correction = project_current_edit_correction_context(canonical_json(tampered))
    with pytest.raises(ContractError, match="source ledger hash differs"):
        project_bounded_investigation_request_context(tampered_correction)


def test_stored_v24_qualification_is_a_byte_audit() -> None:
    raw = (ROOT / QUALIFICATION_PATH).read_bytes()
    value = json.loads(raw)

    assert raw == qualification_bytes(value)
    assert sha256_bytes(raw).startswith("sha256:")
