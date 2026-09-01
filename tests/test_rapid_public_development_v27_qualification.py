from __future__ import annotations

import json
from pathlib import Path

import pytest

from patchloop.errors import ContractError
from patchloop.evals import rapid_public_development_v27 as rapid
from patchloop.evals import rapid_public_development_v27_qualification as qualification
from patchloop.util import sha256_json

ROOT = Path(__file__).resolve().parents[1]


def test_qualification_source_scope_includes_new_gates_and_mock_tests():
    assert len(qualification.SOURCE_FILES) == len(set(qualification.SOURCE_FILES))
    assert {
        "patchloop/agent/provider_request_gate.py",
        "patchloop/evals/provider_request_batch_qualification.py",
        "patchloop/evals/rapid_v27_package_binding.py",
        "tests/test_provider_request_gate_runner.py",
    } <= set(qualification.SOURCE_FILES)
    for relative in qualification.SOURCE_FILES:
        identity = qualification._source_identity(ROOT, relative)
        assert identity["bytes"] > 0 and identity["file_sha256"].startswith("sha256:")


def test_qualification_serialization_rejects_tampering():
    body = {"schema_version": qualification.SCHEMA_VERSION, "fixture_only": True}
    value = {**body, "content_hash": sha256_json(body)}
    assert qualification.qualification_bytes(value) == qualification.qualification_bytes(value)
    value["fixture_only"] = False
    with pytest.raises(ContractError, match="hash"):
        qualification.qualification_bytes(value)


def test_qualification_file_requires_all_pre_count_boundaries(monkeypatch):
    candidate = rapid.build_rapid_public_development_v27_candidate(repository=ROOT)
    rehearsal = rapid._build_rehearsal_for(candidate, repository=ROOT)
    assert len(rehearsal["all_pre_count_boundaries"]) == 6
    assert all(item["provider_dispatch_blocked"] for item in rehearsal["all_pre_count_boundaries"])
    assert all(
        item["provider_request_policy"] == candidate["provider_request_contract"]["policy_version"]
        for item in rehearsal["all_row_capabilities"]
    )
    assert rehearsal["later_phase_requests_observed"] is False
    assert rehearsal["provider_acceptance_observed"] is False


def test_entire_qualification_before_materialization_is_deterministic():
    candidate = rapid.build_rapid_public_development_v27_candidate(repository=ROOT)
    rehearsal = rapid._build_rehearsal_for(candidate, repository=ROOT)
    first = qualification._qualification_for(candidate, rehearsal, repository=ROOT)
    second = qualification._qualification_for(candidate, rehearsal, repository=ROOT)
    assert qualification.qualification_bytes(first) == qualification.qualification_bytes(second)
    assert first["candidate_created"] is first["rehearsal_created"] is False
    assert first["status"] == "offline-dry-validation"
    assert first["pre_count_boundary"]["row_request_count"] == 6
    assert first["production_shaped_image_request_start_mock"]["pre_count_gate_count"] == 6
    compatibility = first["empty_argument_schema_compatibility"]
    assert len(compatibility["lean-harness-v25"]["equivalent_empty_required_paths"]) == 2
    assert compatibility["lean-harness-v27"]["equivalent_empty_required_paths"] == []
    assert all(row["provider_request_bytes_modified"] is False for row in compatibility.values())
    assert first["evidence_boundary"]["provider_calls"] == 0
    assert first["paid_execution_authorized"] is False


def test_stored_qualification_twice_if_frozen():
    if not (ROOT / qualification.QUALIFICATION_PATH).exists():
        pytest.skip("qualification intentionally freezes after offline tests")
    stored = json.loads((ROOT / qualification.QUALIFICATION_PATH).read_bytes())
    first = qualification.build_rapid_public_development_v27_qualification(ROOT)
    second = qualification.build_rapid_public_development_v27_qualification(ROOT)
    assert qualification.qualification_bytes(first) == qualification.qualification_bytes(second)
    assert stored == first
    assert stored["pre_count_boundary"]["row_request_count"] == 6
    assert stored["production_shaped_image_request_start_mock"]["pre_count_gate_count"] == 6
    assert stored["evidence_boundary"]["provider_calls"] == 0
    assert stored["evidence_boundary"]["docker_calls"] == 0
    assert stored["evidence_boundary"]["evaluator_calls"] == 0
    assert stored["paid_execution_authorized"] is False
    candidate = rapid.load_rapid_public_development_v27_candidate(ROOT)
    assert qualification.validate_stored_qualification(candidate, repository=ROOT) == stored


def test_live_qualification_preflight_is_read_only_and_rejects_source_drift(monkeypatch):
    if not (ROOT / qualification.QUALIFICATION_PATH).exists():
        pytest.skip("qualification intentionally freezes after offline tests")
    candidate = rapid.load_rapid_public_development_v27_candidate(ROOT)
    monkeypatch.setattr(
        qualification,
        "run_provider_request_batch_mock",
        lambda *a, **k: pytest.fail("live preflight reran mocks"),
    )
    qualification.validate_stored_qualification(candidate, repository=ROOT)
    original = qualification._source_identity

    def changed(root, relative):
        descriptor = original(root, relative)
        if relative == "patchloop/agent/provider_request_gate.py":
            return {**descriptor, "file_sha256": "sha256:" + "0" * 64}
        return descriptor

    monkeypatch.setattr(qualification, "_source_identity", changed)
    with pytest.raises(ContractError, match="no longer binds"):
        qualification.validate_stored_qualification(candidate, repository=ROOT)
