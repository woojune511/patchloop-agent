from __future__ import annotations

import json
from pathlib import Path

from patchloop.agent.workflow_lifecycle_binding_qualification import (
    IMMUTABLE_INPUTS,
    QUALIFICATION_PATH,
    SOURCE_FILES,
    build_lifecycle_binding_qualification,
    qualification_bytes,
)
from patchloop.util import sha256_json

ROOT = Path(__file__).resolve().parents[1]


def test_v28_qualification_is_deterministic_source_bound_and_zero_call() -> None:
    first = build_lifecycle_binding_qualification(ROOT)
    second = build_lifecycle_binding_qualification(ROOT)

    assert qualification_bytes(first) == qualification_bytes(second)
    assert first["status"] == "offline-qualified"
    assert first["candidate_created"] is False
    assert first["external_calls"] == 0
    assert [item["path"] for item in first["source_files"]] == list(SOURCE_FILES)
    assert [item["path"] for item in first["immutable_inputs"]] == list(IMMUTABLE_INPUTS)
    for key in (
        "provider_calls",
        "docker_calls",
        "evaluator_calls",
        "visible_check_calls",
        "network_calls",
    ):
        assert first["evidence_boundary"][key] == 0


def test_v28_qualification_covers_registry_feedback_and_r24_shape() -> None:
    scenarios = build_lifecycle_binding_qualification(ROOT)["scenarios"]
    registry = scenarios["single_component_registry_request"]
    record = scenarios["bound_public_plan_record"]
    feedback = scenarios["exact_relation_mismatch_feedback"]
    r24 = scenarios["r24_public_mismatch_shape"]

    assert registry["owners_field_absent"] is True
    assert registry["states_field_absent"] is True
    assert registry["free_form_affected_components_absent"] is True
    assert registry["integer_component_references"]["type"] == "integer"
    assert record["transition_component_indices"] == [0, 1]
    assert record["mutation_owner_component_index"] == 0
    assert record["private_or_hidden_material_used"] is False
    assert feedback["collision_indices"] == [0, 1]
    assert feedback["unchanged_state_indices"] == [1]
    assert feedback["duplicate_transition_indices"] == [0]
    assert feedback["out_of_range_transition_indices"] == [4]
    assert feedback["projected_exact_mismatch"] is True
    assert feedback["tampered_relation_hash_rejected"] is True
    assert r24["affected_started_rows"] == 2
    assert r24["rejected_plan_attempts"] == 3
    assert r24["exact_mismatch_feedback_was_absent"] is True
    assert r24["semantic_fix_correctness_established"] is False


def test_stored_v28_qualification_is_an_exact_byte_audit() -> None:
    raw = (ROOT / QUALIFICATION_PATH).read_bytes()
    document = json.loads(raw)

    assert raw == qualification_bytes(build_lifecycle_binding_qualification(ROOT))
    assert raw == qualification_bytes(document)
    assert document["content_hash"] == sha256_json(
        {key: value for key, value in document.items() if key != "content_hash"}
    )
