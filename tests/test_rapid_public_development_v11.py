from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest

from patchloop.errors import RecoveryError
from patchloop.evals import rapid_public_development_v11 as rapid
from patchloop.evals.live_verifier_registry import live_verifier_registry
from patchloop.util import sha256_bytes, sha256_json

REPOSITORY = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def candidate() -> dict[str, Any]:
    return rapid.load_consumed_rapid_public_development_v11_candidate(
        repository=REPOSITORY
    )


def test_candidate_is_exact_zero_call_and_binds_ordered_qualification(
    candidate: dict[str, Any],
) -> None:
    raw = (REPOSITORY / rapid.CANDIDATE_PATH).read_bytes()
    assert raw == rapid.candidate_bytes(candidate)
    assert len(raw) == 16_821
    assert sha256_bytes(raw) == (
        "sha256:503b0f12251192750a024b38eef3886c931be031ab9d9e88e06581145ff82614"
    )
    assert candidate["execution_hash"] == (
        "sha256:db9e887fea43844c29fed588e80094fc32792c9c7a56f3606290c4a52de15807"
    )
    assert candidate["content_hash"] == (
        "sha256:a131abad398ba46cbbc24461689f34734a69c2868cb7053675c4827eb24373d0"
    )
    assert candidate["runtime_build_hash"] == (
        "sha256:26c22aaced0579331860202a8a47860c76f3e8d278050dbde5eac281449b9415"
    )
    assert candidate["official"] is False
    assert candidate["source_qualified"] is True
    assert candidate["execution_authorized"] is False
    assert candidate["provider_calls_made"] == candidate["docker_calls_made"] == 0
    assert candidate["added_model_cost_usd"] == 0.0

    selection = candidate["selection_evidence"]
    successor = selection["ordered_correction_successor"]
    assert successor["file_sha256"] == rapid.COMPLETION_QUALIFICATION_FILE_SHA256
    assert successor["content_hash"] == rapid.COMPLETION_QUALIFICATION_CONTENT_HASH
    assert successor["scenario_set_hash"] == rapid.COMPLETION_QUALIFICATION_SCENARIO_SET_HASH
    assert successor["runtime_policy_version"] == "lean-harness-v8"
    assert successor["tool_schema_version"] == "v12"
    assert successor["context_policy_version"] == "phase-evidence-v18"
    assert successor["quality_improvement_established"] is False

    transition = selection["source_transition"]
    assert transition["qualified_snapshot_preserved"] is True
    assert transition["unchanged_mechanical_source_count"] == len(rapid.COMPLETION_SOURCE_FILES)
    assert transition["permitted_changed_paths"] == []
    assert all(row["unchanged"] is True for row in transition["source_rows"])
    assert candidate["predecessor_candidate"]["path"].endswith(
        "rapid-public-dev-anyio-ordered-correction-20260824-r9-candidate-v12.json"
    )
    assert candidate["predecessor_result"]["path"].endswith(
        "rapid-public-dev-anyio-completion-policy-20260823-r8-553f7cfca404.jsonl"
    )
    assert candidate["selection_evidence_hash"] == sha256_json(selection)


def test_six_manifests_preserve_pairing_and_registry_admission(
    candidate: dict[str, Any],
) -> None:
    registry = live_verifier_registry()
    plan = rapid._plan(candidate, approved=True)
    plan_decision = registry.validate_authorization_plan(plan)
    assert plan_decision.accepted is True
    assert plan_decision.verifier_id == rapid.VERIFIER_ID
    assert plan_decision.requires_row_capability is True

    for row in candidate["schedule"]:
        manifest = rapid.build_rapid_v11_run_manifest(
            candidate,
            row["order"],
            repository=REPOSITORY,
        )
        assert manifest.tool_schema_version == row["tool_schema_version"]
        assert manifest.context_policy_version == row["context_policy_version"]
        if row["variant"] == "lean-harness-v8":
            assert (manifest.tool_schema_version, manifest.context_policy_version) == (
                "v12",
                "phase-evidence-v18",
            )
        decision = registry.verify_manifest(
            plan=plan,
            manifest=manifest,
            authorization_plan_path="<test-rehearsal>",
            authorization_plan_hash=sha256_bytes(rapid._plan_bytes(plan)),
            repository=REPOSITORY,
            runner_root=None,
            batch_validation=True,
        )
        assert decision.accepted is True
        assert decision.verifier_id == rapid.VERIFIER_ID


def test_consumed_rehearsal_is_canonical_and_stops_before_dispatch(
    candidate: dict[str, Any],
) -> None:
    stored = rapid.load_rapid_public_development_v11_rehearsal(
        candidate,
        repository=REPOSITORY,
    )
    raw = (REPOSITORY / rapid.REHEARSAL_PATH).read_bytes()

    assert raw == rapid.rehearsal_bytes(stored)
    assert len(raw) == 3_078
    assert sha256_bytes(raw) == (
        "sha256:ea91dd4450f58ca925c49ecf9719d0144237423b6fdfa252e876206c915406a1"
    )
    assert stored["content_hash"] == (
        "sha256:7ef366ec53053cdcecd77b241eec3c2c1b17f063ccb1b1d08db589f4b29e2a29"
    )
    assert stored["verified_manifest_count"] == 6
    assert stored["verifier_id"] == "rapid-r9-candidate-v13-plan-v13"
    assert stored["provider_calls_made"] == 0
    assert stored["docker_calls_made"] == 0
    assert stored["task_calls_made"] == 0
    assert stored["evaluator_calls_made"] == 0
    assert stored["added_model_cost_usd"] == 0.0
    assert stored["first_provider_boundary"]["provider_dispatch_blocked"] is True
    assert stored["second_provider_boundary"]["provider_dispatch_blocked"] is True


def test_candidate_tamper_and_unapproved_live_entry_fail_closed(
    candidate: dict[str, Any],
) -> None:
    changed = copy.deepcopy(candidate)
    changed["variant_contracts"]["lean-harness-v8"]["tool_schema_version"] = "v11"
    content = {key: value for key, value in changed.items() if key != "content_hash"}
    changed["execution_hash"] = sha256_json({key: changed[key] for key in rapid._EXECUTION_KEYS})
    changed["content_hash"] = sha256_json(content)
    with pytest.raises(RecoveryError):
        rapid._validate_candidate(changed)

    with pytest.raises(RecoveryError):
        rapid.run_rapid_public_development_v11(
            repository=REPOSITORY,
            approve_live_cost=False,
            approved_execution_hash=None,
        )
