from __future__ import annotations

import json
from pathlib import Path

from patchloop.agent.workflow_finalization_successor_qualification import (
    IMMUTABLE_PREDECESSOR_FILES,
    QUALIFICATION_PATH,
    SOURCE_FILES,
    build_workflow_finalization_successor_qualification,
    qualification_bytes,
)
from patchloop.util import sha256_bytes

ROOT = Path(__file__).resolve().parents[1]

EXPECTED_PREDECESSOR_HASHES = {
    "experiments/lean-harness-workflow-successor-v2-public-qualification-20260825-v1.json": (
        "sha256:68c66708a2615fb93bfa8eb86fb829692721e5ee90b49bff060c74c8ff45aed0"
    ),
    (
        "reports/rapid-development/artifacts/"
        "rapid-public-dev-anyio-workflow-revision-ab-20260825-r11-candidate-v17.json"
    ): ("sha256:31ab3c6e63c29c72ed1900c15855c182e34df1aba861cdf0d480a3ae449a5407"),
    (
        "reports/rapid-development/artifacts/"
        "rapid-public-dev-anyio-workflow-revision-ab-20260825-r11-"
        "candidate-v17-rehearsal-v14.json"
    ): ("sha256:408e3420c535e03a29afcc6d5a9d12fe1d6a4c8c20467084edf31732aaaec250"),
    (
        "reports/rapid-development/"
        "rapid-public-dev-anyio-workflow-revision-ab-20260825-r11-c64654b6bdba.jsonl"
    ): ("sha256:66fed2b61499f5d58b4812228591b45cba75390c6ddbe8f9bfe4612191734424"),
    (
        "reports/rapid-development/artifacts/"
        "rapid-public-dev-anyio-workflow-revision-ab-20260825-r11-"
        "workflow-diagnosis-v1.json"
    ): ("sha256:622744647a01e246170cc1d95d1c4e75c76297dc4d5b71023d15dc2493ef3e05"),
}


def test_workflow_finalization_successor_qualification_binds_the_single_fix() -> None:
    value = build_workflow_finalization_successor_qualification(ROOT)
    scenarios = {item["scenario_id"]: item["observed"] for item in value["scenarios"]}

    assert value["successor_runtime"] == "lean-harness-v13"
    assert value["tool_schema_version"] == "v17"
    assert value["context_policy_version"] == "phase-evidence-v23"
    assert value["scope"] == "single-r11-v12-finalization-request-projection-failure-class"
    assert scenarios["consumed-v12-finalization-schema-mismatch-reproduced"] == {
        "validation_error": True,
        "error_count": 18,
        "phase_tool_surface_mode_rejected": True,
        "provider_dispatches": 0,
    }
    retained = scenarios["v13-workflow-surface-retained-through-reserve"]
    assert retained["request_mode"] == "finalization"
    assert retained["surface_schema"] == "lean-workflow-tool-surface-v2"
    assert retained["decision_hash"] == retained["surface_decision_hash"]
    assert (
        retained["effective_max_output_tokens"] == retained["workflow_effective_max_output_tokens"]
    )
    assert retained["legacy_phase_surface_accepted"] is False
    assert tuple(item["path"] for item in value["source_files"]) == SOURCE_FILES
    assert tuple(item["path"] for item in value["immutable_predecessors"]) == (
        IMMUTABLE_PREDECESSOR_FILES
    )


def test_workflow_finalization_successor_qualification_is_deterministic_and_zero_call() -> None:
    first = build_workflow_finalization_successor_qualification(ROOT)
    second = build_workflow_finalization_successor_qualification(ROOT)

    assert first == second
    assert qualification_bytes(first) == qualification_bytes(second)
    assert first["evidence_boundary"] == {
        "public_only": True,
        "private_task_spec_read": False,
        "hidden_evaluator_content_read": False,
        "reference_patch_read": False,
        "reasoning_text_read": False,
        "provider_calls": 0,
        "docker_calls": 0,
        "evaluator_calls": 0,
        "visible_check_calls": 0,
        "added_cost_usd": "0",
    }
    assert first["runtime_activation_authorized"] is False
    assert first["paid_execution_authorized"] is False
    assert first["quality_improvement_established"] is False


def test_workflow_finalization_successor_preserves_predecessor_hashes() -> None:
    value = build_workflow_finalization_successor_qualification(ROOT)
    observed = {item["path"]: item["file_sha256"] for item in value["immutable_predecessors"]}

    assert observed == EXPECTED_PREDECESSOR_HASHES


def test_workflow_finalization_successor_qualification_artifact_is_immutable_predecessor() -> None:
    raw = (ROOT / QUALIFICATION_PATH).read_bytes()
    stored = json.loads(raw)

    assert len(raw) == 5_266
    assert sha256_bytes(raw) == (
        "sha256:ffbff31ad0d885277bec8961341658a567687d8b9d536ad8104b6d818ba3616d"
    )
    assert stored["content_hash"] == (
        "sha256:951e3820d811d18a12d53e8844b96272b40cb6695849dc991aee3ddff8a42552"
    )
    assert raw == qualification_bytes(stored)
