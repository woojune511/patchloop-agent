from __future__ import annotations

import json
from pathlib import Path

from patchloop.agent.workflow_semantic_progress_activation_qualification import (
    QUALIFICATION_PATH,
    qualification_bytes,
)
from patchloop.util import sha256_bytes

ROOT = Path(__file__).resolve().parents[1]


def _stored() -> tuple[dict[str, object], bytes]:
    raw = (ROOT / QUALIFICATION_PATH).read_bytes()
    return json.loads(raw), raw


def test_activation_qualification_binds_only_the_r12_contract_seam() -> None:
    value, _ = _stored()

    assert value["status"] == "offline-qualified"
    assert value["experiment_id"] == ("rapid-public-dev-anyio-semantic-progress-ab-20260825-r12")
    assert value["plan_schema"] == "experiment-execution-plan-v18"
    assert value["verifier_id"] == "rapid-r12-candidate-v18-plan-v18"
    assert value["source_transition"]["observed_changed_paths"] == [
        "patchloop/contracts.py",
        "tests/test_workflow_semantic_progress_successor_qualification.py",
    ]
    assert value["source_transition"]["qualified_behavior_unchanged"] is True
    assert value["semantic_progress_contract"] == {
        "predecessor_runtime": "lean-harness-v14",
        "successor_runtime": "lean-harness-v15",
        "tool_schema_version": "v19",
        "context_policy_version": "phase-evidence-v25",
        "workflow_policy_version": "public-failure-signature-no-progress-reset-v1",
        "contamination_disclosed": True,
        "excluded_fixture_content_used": False,
    }


def test_activation_qualification_is_deterministic_and_zero_call() -> None:
    first, first_raw = _stored()
    second, second_raw = _stored()

    assert first_raw == second_raw
    assert qualification_bytes(first) == qualification_bytes(second)
    assert first["evidence_boundary"] == {
        "provider_calls": 0,
        "docker_calls": 0,
        "task_calls": 0,
        "evaluator_calls": 0,
        "visible_check_calls": 0,
        "added_model_cost_usd": "0",
    }
    assert first["manifest_admission_exercised"] is False
    assert first["production_order_rehearsal_exercised"] is False
    assert first["runtime_activation_authorized"] is False
    assert first["paid_execution_authorized"] is False
    assert first["quality_improvement_established"] is False


def test_activation_qualification_artifact_is_preserved() -> None:
    stored, raw = _stored()

    assert raw == qualification_bytes(stored)
    assert len(raw) == 9_899
    assert sha256_bytes(raw) == (
        "sha256:93b2b239d030cfe33ba3771f312977a68a6a4c2c705eb30fe0b03ebab289f72a"
    )
    assert stored["content_hash"] == (
        "sha256:c1d71caf106094f8b4d4c877d813825c62ed0621a0bfef8ffba54e497e47c9e2"
    )
