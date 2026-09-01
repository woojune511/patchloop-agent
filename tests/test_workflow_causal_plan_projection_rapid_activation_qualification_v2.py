from __future__ import annotations

import copy
from pathlib import Path

import pytest

from patchloop.agent import (
    workflow_causal_plan_projection_rapid_activation_qualification_v2 as qualification,
)
from patchloop.errors import ContractError
from patchloop.util import sha256_bytes

REPOSITORY = Path(__file__).resolve().parents[1]


def test_second_rapid_activation_build_is_deterministic_and_zero_call() -> None:
    first = qualification.build_workflow_causal_plan_projection_rapid_activation_qualification_v2(
        REPOSITORY
    )
    second = qualification.build_workflow_causal_plan_projection_rapid_activation_qualification_v2(
        REPOSITORY
    )

    assert first == second
    assert first["source_transition"]["observed_changed_paths"] == [
        "patchloop/contracts.py",
        "tests/test_workflow_causal_plan_projection_activation_qualification.py",
    ]
    assert first["source_transition"]["qualified_behavior_unchanged"] is True
    assert first["superseded_activation"] == {
        "path": (
            "experiments/lean-harness-causal-plan-projection-rapid-activation-"
            "qualification-20260826-v1.json"
        ),
        "bytes": 11_055,
        "file_sha256": ("sha256:2d4f2c797679c58162dc659d39f844c4eac08fc07d4c2d1de1fef17494cd10bb"),
        "content_hash": ("sha256:ad363df97aa1eb6012174198337c8cb6be32110d88386a4713714b99fb4625a7"),
        "superseded_zero_call": True,
    }
    assert first["experiment_id"] == (
        "rapid-public-dev-anyio-causal-plan-projection-ab-20260826-r14"
    )
    assert first["plan_schema"] == "experiment-execution-plan-v21"
    assert first["verifier_id"] == "rapid-r14-candidate-v21-plan-v21"
    assert first["evidence_boundary"] == {
        "provider_calls": 0,
        "docker_calls": 0,
        "task_calls": 0,
        "evaluator_calls": 0,
        "visible_check_calls": 0,
        "added_model_cost_usd": "0",
    }
    assert first["candidate_created_by_qualification"] is False
    assert first["paid_execution_authorized"] is False


def test_stored_second_rapid_activation_matches_current_source() -> None:
    stored = qualification.load_workflow_causal_plan_projection_rapid_activation_qualification_v2(
        REPOSITORY
    )
    raw = (REPOSITORY / qualification.QUALIFICATION_PATH).read_bytes()

    assert raw == qualification.qualification_bytes(stored)
    assert len(raw) == 11_556
    assert sha256_bytes(raw) == (
        "sha256:3a7af92e0e23715fadd86f5cbf3a868a55485fa3786d8af7ca2a0746501f47e2"
    )
    assert stored["content_hash"] == (
        "sha256:b0d10f8e6118db17535ed3919571e83afd937efd676d9ed55a2914a80249d898"
    )
    assert stored == (
        qualification.build_workflow_causal_plan_projection_rapid_activation_qualification_v2(
            REPOSITORY
        )
    )


def test_second_source_transition_rejects_unqualified_behavior_change() -> None:
    predecessor, _ = qualification._predecessor(REPOSITORY)
    current = copy.deepcopy(predecessor)
    for path in qualification.PERMITTED_SOURCE_CHANGES:
        item = next(row for row in current["source_files"] if row["path"] == path)
        item["bytes"] += 1
        item["file_sha256"] = "sha256:" + ("0" if path.endswith("contracts.py") else "1") * 64
    current["scenarios"]["preserved_limits"]["targeted_first_changed"] = True

    with pytest.raises(ContractError, match="changed qualified behavior"):
        qualification._source_transition(predecessor, current)
