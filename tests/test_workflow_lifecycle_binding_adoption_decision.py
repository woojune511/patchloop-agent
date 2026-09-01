from __future__ import annotations

import copy
import json
import socket
import subprocess
from pathlib import Path

import pytest

from patchloop.agent import workflow_lifecycle_binding_adoption_decision as adoption
from patchloop.agent.runner import AgentRunner
from patchloop.errors import ContractError
from patchloop.util import sha256_json

ROOT = Path(__file__).resolve().parents[1]


def _forbidden(*_args, **_kwargs):
    raise AssertionError("V28 adoption decision permits no external or runner work")


@pytest.fixture(autouse=True)
def no_external_or_runner_work(monkeypatch):
    monkeypatch.setattr(socket.socket, "connect", _forbidden)
    monkeypatch.setattr(socket, "create_connection", _forbidden)
    monkeypatch.setattr(subprocess, "run", _forbidden)
    monkeypatch.setattr(subprocess, "Popen", _forbidden)
    monkeypatch.setattr(AgentRunner, "start", _forbidden)
    monkeypatch.setattr(AgentRunner, "resume", _forbidden)


def test_decision_is_repeatable_adopts_treatment_only_and_is_zero_call() -> None:
    first = adoption.build_lifecycle_binding_adoption_decision(ROOT)
    second = adoption.build_lifecycle_binding_adoption_decision(ROOT)

    assert adoption.decision_bytes(first) == adoption.decision_bytes(second)
    assert first["status"] == "package-adoption-recorded"
    assert first["decision"] == {
        "adoption_status": "adopted-for-future-rapid-treatment",
        "selected_control_runtime": "lean-harness-v27",
        "selected_treatment_runtime": "lean-harness-v28",
        "eligible_for_separate_candidate_preparation": True,
        "candidate_preparation_authorized_in_this_work_item": False,
        "default_runtime_changed": False,
        "quality_or_generalization_promotion": False,
        "live_execution_ready": False,
        "reason": first["decision"]["reason"],
    }
    assert all(first["adoption_criteria"].values())
    assert first["candidate_created"] is first["rehearsal_created"] is False
    assert first["runtime_source_modified"] is False
    assert first["external_calls"] == 0
    assert first["paid_execution_authorized"] is False


def test_decision_binds_exact_frozen_activation_review() -> None:
    value = adoption.build_lifecycle_binding_adoption_decision(ROOT)
    binding = value["activation_review"]

    assert binding["bytes"] == adoption.ACTIVATION_REVIEW_BYTES
    assert binding["file_sha256"] == adoption.ACTIVATION_REVIEW_FILE_SHA256
    assert binding["content_hash"] == adoption.ACTIVATION_REVIEW_CONTENT_HASH
    assert binding["status"] == "activation-reviewed-candidate-decision-ready"


def test_comparison_contract_is_one_bounded_official_false_variable() -> None:
    value = adoption.build_lifecycle_binding_adoption_decision(ROOT)
    comparison = value["comparison_contract"]

    assert comparison == {
        "official": False,
        "control_runtime": "lean-harness-v27",
        "treatment_runtime": "lean-harness-v28",
        "declared_comparison_variable": "lifecycle-plan-feedback-package",
        "recommended_rows_per_arm": 3,
        "balanced_interleaved_schedule_required": True,
        "same_task_image_model_memory_budget_evaluator_required": True,
        "task_version_change_allowed": False,
        "runner_continuity_check_allowed": False,
        "semantic_or_timeout_fix_may_be_bundled": False,
        "exact_schedule_selected": False,
        "cost_reserve_or_cap_selected": False,
    }


def test_selection_and_later_promotion_are_not_conflated() -> None:
    value = adoption.build_lifecycle_binding_adoption_decision(ROOT)
    interpretation = value["precommitted_interpretation"]

    assert interpretation["legacy_unbound_terminal_count_max"] == 0
    assert interpretation["admission_loop_budget_terminal_count_max"] == 0
    assert interpretation["harness_admission_infrastructure_failure_count_max"] == 0
    assert interpretation["treatment_evaluator_reach_floor"] == "2/3"
    assert interpretation["treatment_reach_submission_success_not_lower_than_control"]
    assert interpretation["treatment_mean_settled_row_cost_ratio_max"] == "1.25"
    assert interpretation["incomplete_schedule_is_noncomparative"] is True
    assert interpretation["quality_or_generalization_claim_allowed"] is False
    assert value["quality_improvement_established"] is False
    assert value["generalization_established"] is False


def test_all_review_residual_risks_remain_literal_and_ordered() -> None:
    value = adoption.build_lifecycle_binding_adoption_decision(ROOT)
    assert tuple(value["residual_risks"]) == adoption.EXPECTED_RESIDUAL_RISKS


@pytest.mark.parametrize(
    "damage,criterion",
    [
        ("readiness", "activation_review_is_ready_and_unadopted"),
        ("failure_class", "observed_contract_friction_is_directly_addressed"),
        ("semantic_claim", "semantic_and_infrastructure_unknowns_are_not_reclassified"),
        ("comparison", "comparison_variable_and_scope_are_bounded"),
        ("fairness", "fair_comparison_inputs_remain_fixed"),
        ("authority", "candidate_and_external_gates_remain_separate"),
        ("risk", "residual_risks_are_preserved_exactly"),
        ("external", "evidence_boundary_is_public_and_zero_call"),
    ],
)
def test_adoption_criteria_fail_closed_on_missing_or_overstated_review(damage, criterion) -> None:
    review = json.loads((ROOT / adoption.ACTIVATION_REVIEW_PATH).read_bytes())
    if damage == "readiness":
        review["decision"]["adoption_status"] = "adopted"
    elif damage == "failure_class":
        review["package_assessment"]["observed_public_failure_class_addressed"] = "other"
    elif damage == "semantic_claim":
        review["package_assessment"]["semantic_task_failure_addressed"] = True
    elif damage == "comparison":
        review["future_candidate_constraints"]["package_is_single_comparison_variable"] = False
    elif damage == "fairness":
        review["future_candidate_constraints"][
            "same_task_image_model_memory_budget_evaluator_required"
        ] = False
    elif damage == "authority":
        review["candidate_created"] = True
    elif damage == "risk":
        review["residual_risks"].pop()
    else:
        review["evidence_boundary"]["provider_calls"] = 1
    criteria = adoption.adoption_criteria(review)
    assert criteria[criterion] is False
    assert not all(criteria.values())


def test_frozen_review_tamper_stops_before_rebuild(tmp_path, monkeypatch) -> None:
    path = tmp_path / adoption.ACTIVATION_REVIEW_PATH
    path.parent.mkdir(parents=True)
    path.write_bytes(b"tampered review")
    monkeypatch.setattr(adoption, "build_lifecycle_binding_activation_review", _forbidden)

    with pytest.raises(ContractError, match="frozen V28 activation-review bytes differ"):
        adoption.build_lifecycle_binding_adoption_decision(tmp_path)


def test_changed_reviewed_source_cannot_be_silently_adopted(monkeypatch) -> None:
    value = json.loads((ROOT / adoption.ACTIVATION_REVIEW_PATH).read_bytes())
    changed = copy.deepcopy(value)
    changed["review_source_files"][0]["file_sha256"] = "sha256:" + "f" * 64
    changed["content_hash"] = sha256_json(
        {key: item for key, item in changed.items() if key != "content_hash"}
    )
    monkeypatch.setattr(
        adoption,
        "build_lifecycle_binding_activation_review",
        lambda _root: changed,
    )

    with pytest.raises(ContractError, match="activation-review source binding differs"):
        adoption.build_lifecycle_binding_adoption_decision(ROOT)


def test_decision_artifact_is_append_only_and_hash_bound(tmp_path, monkeypatch) -> None:
    body = {"schema_version": "synthetic-decision", "external_calls": 0}
    value = {**body, "content_hash": sha256_json(body)}
    monkeypatch.setattr(adoption, "build_lifecycle_binding_adoption_decision", lambda _root: value)
    monkeypatch.setattr(adoption, "DECISION_PATH", Path("synthetic-decision.json"))
    adoption.materialize_lifecycle_binding_adoption_decision(tmp_path)
    target = tmp_path / adoption.DECISION_PATH
    before = target.read_bytes()
    adoption.materialize_lifecycle_binding_adoption_decision(tmp_path)
    assert target.read_bytes() == before
    value["external_calls"] = 1
    with pytest.raises(ContractError, match="content hash differs"):
        adoption.decision_bytes(value)
    value["content_hash"] = sha256_json(
        {key: item for key, item in value.items() if key != "content_hash"}
    )
    with pytest.raises(ContractError, match="never overwrite"):
        adoption.materialize_lifecycle_binding_adoption_decision(tmp_path)
    assert target.read_bytes() == before


def test_materialization_requires_identical_rebuilds(tmp_path, monkeypatch) -> None:
    calls = []

    def changing(_root):
        body = {"schema_version": "synthetic-decision", "sequence": len(calls)}
        calls.append(body)
        return {**body, "content_hash": sha256_json(body)}

    monkeypatch.setattr(adoption, "build_lifecycle_binding_adoption_decision", changing)
    monkeypatch.setattr(adoption, "DECISION_PATH", Path("synthetic-decision.json"))
    with pytest.raises(ContractError, match="not byte-identical"):
        adoption.materialize_lifecycle_binding_adoption_decision(tmp_path)
    assert not (tmp_path / adoption.DECISION_PATH).exists()


def test_stored_decision_is_an_exact_byte_audit() -> None:
    raw = (ROOT / adoption.DECISION_PATH).read_bytes()
    document = json.loads(raw)

    assert raw == adoption.decision_bytes(adoption.build_lifecycle_binding_adoption_decision(ROOT))
    assert raw == adoption.decision_bytes(document)
