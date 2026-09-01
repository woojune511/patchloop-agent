from __future__ import annotations

import copy
import json
import socket
import subprocess
from pathlib import Path

import pytest

from patchloop.agent import workflow_lifecycle_binding_activation_review as review
from patchloop.agent.runner import AgentRunner
from patchloop.errors import ContractError
from patchloop.util import sha256_json

ROOT = Path(__file__).resolve().parents[1]


def _forbidden(*_args, **_kwargs):
    raise AssertionError("V28 activation review permits no external or runner work")


@pytest.fixture(autouse=True)
def no_external_or_runner_work(monkeypatch):
    monkeypatch.setattr(socket.socket, "connect", _forbidden)
    monkeypatch.setattr(socket, "create_connection", _forbidden)
    monkeypatch.setattr(subprocess, "run", _forbidden)
    monkeypatch.setattr(subprocess, "Popen", _forbidden)
    monkeypatch.setattr(AgentRunner, "start", _forbidden)
    monkeypatch.setattr(AgentRunner, "resume", _forbidden)


def test_review_is_repeatable_eligible_not_adopted_and_zero_call() -> None:
    first = review.build_lifecycle_binding_activation_review(ROOT)
    second = review.build_lifecycle_binding_activation_review(ROOT)

    assert review.review_bytes(first) == review.review_bytes(second)
    assert first["status"] == "activation-reviewed-candidate-decision-ready"
    assert first["decision"] == {
        "adoption_status": "eligible-not-adopted",
        "eligible_for_separate_adoption_decision": True,
        "candidate_design_authorized_by_review": False,
        "live_execution_ready": False,
        "provider_acceptance_observed": False,
        "candidate_created": False,
        "next_work": "separate-v27-v28-rapid-package-adoption-decision",
        "reason": first["decision"]["reason"],
    }
    assert all(first["activation_criteria"].values())
    assert first["candidate_created"] is first["rehearsal_created"] is False
    assert first["runtime_source_modified"] is False
    assert first["external_calls"] == 0
    assert first["paid_execution_authorized"] is False
    assert first["qualification"]["file_sha256"] == review.QUALIFICATION_FILE_SHA256
    assert first["qualification"]["content_hash"] == review.QUALIFICATION_CONTENT_HASH


def test_review_binds_v29_runtime_but_keeps_live_manifest_closed() -> None:
    value = review.build_lifecycle_binding_activation_review(ROOT)
    observations = value["source_observations"]

    assert observations["runtime_contract"]["selects_tool_schemas_v29"] is True
    assert observations["static_provider_schema_admission"]["policy_version"] == (
        "responses-strict-tool-admission-v1"
    )
    assert observations["static_provider_schema_admission"]["provider_acceptance_observed"] is False
    assert observations["manifest_admission"]["runtime_pair_occurrences"] == 1
    assert observations["manifest_admission"]["all_occurrences_require_mock_provider"] is True
    assert observations["manifest_admission"]["live_manifest_admitted"] is False


def test_review_keeps_semantic_timeout_and_attribution_limits_explicit() -> None:
    value = review.build_lifecycle_binding_activation_review(ROOT)
    package = value["package_assessment"]
    constraints = value["future_candidate_constraints"]

    assert package["single_mechanism_attribution_allowed"] is False
    assert package["semantic_task_failure_addressed"] is False
    assert package["provider_timeout_addressed"] is False
    assert package["quality_effect_established"] is False
    assert constraints["recommended_control_runtime"] == "lean-harness-v27"
    assert constraints["recommended_treatment_runtime"] == "lean-harness-v28"
    assert constraints["candidate_design_authorized_by_review"] is False
    assert constraints["historical_retry_or_resume_allowed"] is False
    assert constraints["official"] is False


@pytest.mark.parametrize(
    "damage,criterion",
    [
        ("runtime", "runtime_identity_exact"),
        ("registry", "component_registry_removes_repeated_free_form_relations"),
        ("record", "normalized_record_is_public_plan_bound_not_semantic_oracle"),
        ("feedback", "exact_feedback_is_bounded_deterministic_and_tamper_closed"),
        ("retry", "one_retry_repeated_rejection_and_restart_are_qualified"),
        ("r24", "r24_shape_is_public_and_diagnostic_not_semantic_proof"),
        ("routing", "runtime_routes_v29_and_static_schema_is_locally_admitted"),
        ("live", "live_manifest_and_external_authority_stay_closed"),
        ("external", "qualification_is_zero_call_noncreating_and_source_bound"),
    ],
)
def test_activation_criteria_fail_closed_on_missing_or_overstated_evidence(
    damage, criterion
) -> None:
    qualification = json.loads((ROOT / review.QUALIFICATION_PATH).read_bytes())
    observations = review.source_observations(ROOT)
    if damage == "runtime":
        qualification["runtime_identity"]["tool_schema_version"] = "v28"
    elif damage == "registry":
        qualification["scenarios"]["single_component_registry_request"]["owners_field_absent"] = (
            False
        )
    elif damage == "record":
        qualification["scenarios"]["bound_public_plan_record"][
            "private_or_hidden_material_used"
        ] = True
    elif damage == "feedback":
        qualification["scenarios"]["exact_relation_mismatch_feedback"][
            "tampered_relation_hash_rejected"
        ] = False
    elif damage == "retry":
        qualification["validated_test_surfaces"][
            "second_rejection_stops_before_third_plan_dispatch"
        ] = False
    elif damage == "r24":
        qualification["scenarios"]["r24_public_mismatch_shape"][
            "semantic_fix_correctness_established"
        ] = True
    elif damage == "routing":
        observations["runtime_contract"]["selects_tool_schemas_v29"] = False
    elif damage == "live":
        observations["manifest_admission"]["live_manifest_admitted"] = True
    else:
        qualification["evidence_boundary"]["provider_calls"] = 1
    criteria = review.activation_criteria(qualification, observations)
    assert criteria[criterion] is False
    assert not all(criteria.values())


def test_frozen_qualification_tamper_stops_before_rebuild(tmp_path, monkeypatch) -> None:
    path = tmp_path / review.QUALIFICATION_PATH
    path.parent.mkdir(parents=True)
    path.write_bytes(b"tampered qualification")
    monkeypatch.setattr(review, "build_lifecycle_binding_qualification", _forbidden)

    with pytest.raises(ContractError, match="frozen V28 qualification bytes differ"):
        review.build_lifecycle_binding_activation_review(tmp_path)


def test_changed_qualified_source_cannot_be_silently_reviewed(monkeypatch) -> None:
    value = json.loads((ROOT / review.QUALIFICATION_PATH).read_bytes())
    changed = copy.deepcopy(value)
    changed["source_files"][0]["file_sha256"] = "sha256:" + "f" * 64
    changed["content_hash"] = sha256_json(
        {key: item for key, item in changed.items() if key != "content_hash"}
    )
    monkeypatch.setattr(
        review,
        "build_lifecycle_binding_qualification",
        lambda _root: changed,
    )

    with pytest.raises(ContractError, match="qualification source binding differs"):
        review.build_lifecycle_binding_activation_review(ROOT)


def test_review_artifact_is_append_only_and_hash_bound(tmp_path, monkeypatch) -> None:
    body = {"schema_version": "synthetic-review", "external_calls": 0}
    value = {**body, "content_hash": sha256_json(body)}
    monkeypatch.setattr(review, "build_lifecycle_binding_activation_review", lambda _root: value)
    monkeypatch.setattr(review, "REVIEW_PATH", Path("synthetic-review.json"))
    review.materialize_lifecycle_binding_activation_review(tmp_path)
    target = tmp_path / review.REVIEW_PATH
    before = target.read_bytes()
    review.materialize_lifecycle_binding_activation_review(tmp_path)
    assert target.read_bytes() == before
    value["external_calls"] = 1
    with pytest.raises(ContractError, match="content hash differs"):
        review.review_bytes(value)
    value["content_hash"] = sha256_json(
        {key: item for key, item in value.items() if key != "content_hash"}
    )
    with pytest.raises(ContractError, match="never overwrite"):
        review.materialize_lifecycle_binding_activation_review(tmp_path)
    assert target.read_bytes() == before


def test_materialization_requires_identical_rebuilds(tmp_path, monkeypatch) -> None:
    calls = []

    def changing(_root):
        body = {"schema_version": "synthetic-review", "sequence": len(calls)}
        calls.append(body)
        return {**body, "content_hash": sha256_json(body)}

    monkeypatch.setattr(review, "build_lifecycle_binding_activation_review", changing)
    monkeypatch.setattr(review, "REVIEW_PATH", Path("synthetic-review.json"))
    with pytest.raises(ContractError, match="not byte-identical"):
        review.materialize_lifecycle_binding_activation_review(tmp_path)
    assert not (tmp_path / review.REVIEW_PATH).exists()


def test_stored_review_is_an_exact_byte_audit() -> None:
    raw = (ROOT / review.REVIEW_PATH).read_bytes()
    document = json.loads(raw)

    assert raw == review.review_bytes(review.build_lifecycle_binding_activation_review(ROOT))
    assert raw == review.review_bytes(document)
