from __future__ import annotations

import json
from pathlib import Path

from patchloop.agent import (
    workflow_causal_plan_projection_rapid_activation_qualification as qualification,
)
from patchloop.util import sha256_bytes

REPOSITORY = Path(__file__).resolve().parents[1]


def test_superseded_rapid_activation_is_immutable_zero_call_evidence() -> None:
    raw = (REPOSITORY / qualification.QUALIFICATION_PATH).read_bytes()
    stored = json.loads(raw)

    assert len(raw) == 11_055
    assert sha256_bytes(raw) == (
        "sha256:2d4f2c797679c58162dc659d39f844c4eac08fc07d4c2d1de1fef17494cd10bb"
    )
    assert stored["content_hash"] == (
        "sha256:ad363df97aa1eb6012174198337c8cb6be32110d88386a4713714b99fb4625a7"
    )
    assert raw == qualification.qualification_bytes(stored)
    assert stored["predecessor_qualification"] == {
        "path": (
            "experiments/lean-harness-causal-plan-projection-activation-public-"
            "qualification-20260826-v1.json"
        ),
        "bytes": 5_438,
        "file_sha256": ("sha256:7f4b75a80c8085cdcf3beca1f9693077f97596ba719f3bdece5c9d5553cefa8b"),
        "content_hash": ("sha256:359b3bc8b2067bcd9b42f3c8dbbc5d8894d04a0611948c44a1d83d2995979754"),
    }
    assert stored["source_transition"]["observed_changed_paths"] == ["patchloop/contracts.py"]
    assert stored["source_transition"]["qualified_behavior_unchanged"] is True
    assert stored["experiment_id"] == (
        "rapid-public-dev-anyio-causal-plan-projection-ab-20260826-r14"
    )
    assert stored["plan_schema"] == "experiment-execution-plan-v21"
    assert stored["verifier_id"] == "rapid-r14-candidate-v21-plan-v21"
    assert stored["variant_contracts"] == {
        "lean-harness-v8": {
            "tool_schema_version": "v12",
            "context_policy_version": "phase-evidence-v18",
        },
        "lean-harness-v18": {
            "tool_schema_version": "v22",
            "context_policy_version": "phase-evidence-v28",
        },
    }
    assert stored["evidence_boundary"] == {
        "provider_calls": 0,
        "docker_calls": 0,
        "task_calls": 0,
        "evaluator_calls": 0,
        "visible_check_calls": 0,
        "added_model_cost_usd": "0",
    }
    assert stored["candidate_created_by_qualification"] is False
    assert stored["paid_execution_authorized"] is False
