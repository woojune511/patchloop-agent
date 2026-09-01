from __future__ import annotations

from pathlib import Path

from patchloop.agent import workflow_causal_alternative_rapid_activation_qualification_v2 as q
from patchloop.evals.live_verifier_registry import live_verifier_registry
from patchloop.util import sha256_bytes

REPOSITORY = Path(__file__).resolve().parents[1]


def test_activation_v2_preserves_v17_behavior_and_limits_source_change() -> None:
    first = q.build_workflow_causal_alternative_rapid_activation_qualification_v2(REPOSITORY)
    second = q.build_workflow_causal_alternative_rapid_activation_qualification_v2(REPOSITORY)

    assert first == second
    assert first["predecessor_qualification"] == {
        "path": (
            "experiments/lean-harness-causal-alternative-activation-public-"
            "qualification-20260826-v1.json"
        ),
        "bytes": 5_235,
        "file_sha256": ("sha256:72576cdcf05a9337bcee415d3200bfe76f04fd8b13b3231b02140fb6b2cd448e"),
        "content_hash": ("sha256:45f469b256c50b7259b7c1df6a59e3b4fe8f598f67733ef93a96733b72191f85"),
    }
    transition = first["source_transition"]
    assert transition["permitted_changed_paths"] == [
        "patchloop/contracts.py",
        "tests/test_workflow_causal_alternative_activation_qualification.py",
    ]
    assert transition["observed_changed_paths"] == [
        "patchloop/contracts.py",
        "tests/test_workflow_causal_alternative_activation_qualification.py",
    ]
    assert transition["qualified_behavior_unchanged"] is True
    unchanged = [row for row in transition["rows"] if not row["changed"]]
    assert len(unchanged) == len(q.WORKFLOW_SOURCE_FILES) - 2


def test_activation_v2_binds_exact_registry_and_v8_v17_pair() -> None:
    value = q.build_workflow_causal_alternative_rapid_activation_qualification_v2(REPOSITORY)
    registry = live_verifier_registry()

    assert value["experiment_id"] == q.EXPERIMENT_ID
    assert value["plan_schema"] == q.PLAN_SCHEMA
    assert value["plan_kind"] == q.PLAN_KIND
    assert value["verifier_id"] == q.VERIFIER_ID
    assert value["verifier_descriptor_hash"] == registry.descriptor_hash_for(
        experiment_id=q.EXPERIMENT_ID,
        plan_schema=q.PLAN_SCHEMA,
        plan_kind=q.PLAN_KIND,
    )
    assert value["variant_contracts"] == {
        "lean-harness-v8": {
            "tool_schema_version": "v12",
            "context_policy_version": "phase-evidence-v18",
        },
        "lean-harness-v17": {
            "tool_schema_version": "v21",
            "context_policy_version": "phase-evidence-v27",
        },
    }


def test_activation_v2_is_zero_call_and_grants_no_authority() -> None:
    value = q.build_workflow_causal_alternative_rapid_activation_qualification_v2(REPOSITORY)

    assert value["evidence_boundary"] == {
        "provider_calls": 0,
        "docker_calls": 0,
        "task_calls": 0,
        "evaluator_calls": 0,
        "visible_check_calls": 0,
        "added_model_cost_usd": "0",
    }
    assert value["manifest_admission_exercised"] is False
    assert value["production_order_rehearsal_exercised"] is False
    assert value["candidate_created_by_qualification"] is False
    assert value["runtime_activation_authorized"] is False
    assert value["paid_execution_authorized"] is False
    assert value["quality_improvement_established"] is False
    assert value["generalization_established"] is False


def test_stored_activation_is_exact_when_materialized() -> None:
    stored = q.load_workflow_causal_alternative_rapid_activation_qualification_v2(REPOSITORY)
    expected = q.build_workflow_causal_alternative_rapid_activation_qualification_v2(REPOSITORY)
    raw = (REPOSITORY / q.QUALIFICATION_PATH).read_bytes()

    assert stored == expected
    assert raw == q.qualification_bytes(stored)
    assert len(raw) == 10_735
    assert sha256_bytes(raw) == (
        "sha256:073000189b6cd5466e5d1cce849af9477bfc710aa6034680b354728e11e803ff"
    )
    assert stored["content_hash"] == (
        "sha256:2e404ef926633a2398a263a037601e08713a6e66db322aab340d102d15f6747c"
    )
