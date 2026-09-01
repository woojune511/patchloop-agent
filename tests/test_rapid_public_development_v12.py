from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest

from patchloop.errors import RecoveryError
from patchloop.evals import rapid_public_development_v12 as rapid
from patchloop.evals.live_verifier_registry import live_verifier_registry
from patchloop.util import sha256_bytes, sha256_json

REPOSITORY = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def candidate() -> dict[str, Any]:
    return rapid.load_consumed_rapid_public_development_v12_candidate(REPOSITORY)


def test_candidate_is_exact_zero_call_and_binds_v8_v10_qualification(
    candidate: dict[str, Any],
) -> None:
    raw = (REPOSITORY / rapid.CANDIDATE_PATH).read_bytes()
    assert raw == rapid.candidate_bytes(candidate)
    assert len(raw) == 20_309
    assert sha256_bytes(raw) == (
        "sha256:91f759e4cc6f5b68ac376a5ab1b0ab585311b0e3ba35b9fa8d2d0fd6e092ac99"
    )
    assert candidate["execution_hash"] == (
        "sha256:cbe3f560b03b88d36d201b052622a5f732798e4241b95fecce0005c5cea322fa"
    )
    assert candidate["content_hash"] == (
        "sha256:089d73958e6a93d6ffa349edd9b98dc97d7fcc9daaccf3f4695de3481a33ed4e"
    )
    assert candidate["runtime_build_hash"] == (
        "sha256:f8c3fb149986b4a7a253af07a1779e0456cefc14174526f7d431ca1bc6a16511"
    )
    assert candidate["official"] is False
    assert candidate["source_qualified"] is True
    assert candidate["execution_authorized"] is False
    assert candidate["provider_calls_made"] == candidate["docker_calls_made"] == 0
    assert candidate["added_model_cost_usd"] == 0.0

    selection = candidate["selection_evidence"]
    successor = selection["workflow_successor"]
    assert successor["file_sha256"] == rapid.WORKFLOW_QUALIFICATION_FILE_SHA256
    assert successor["content_hash"] == rapid.WORKFLOW_QUALIFICATION_CONTENT_HASH
    assert successor["scenario_set_hash"] == rapid.WORKFLOW_QUALIFICATION_SCENARIO_SET_HASH
    assert successor["runtime_versions"] == ["lean-harness-v9", "lean-harness-v10"]
    assert successor["tool_schema_versions"] == ["v13", "v14"]
    assert successor["context_policy_versions"] == [
        "phase-evidence-v19",
        "phase-evidence-v20",
    ]
    assert successor["quality_improvement_established"] is False

    transition = selection["source_transition"]
    assert transition["qualified_snapshot_preserved"] is True
    assert transition["unchanged_workflow_source_count"] == len(rapid.WORKFLOW_SOURCE_FILES)
    assert transition["permitted_changed_paths"] == []
    assert all(row["unchanged"] is True for row in transition["source_rows"])
    assert candidate["predecessor_candidate"]["path"].endswith(
        "rapid-public-dev-anyio-ordered-correction-20260824-r9-candidate-v13.json"
    )
    assert candidate["predecessor_result"]["path"].endswith(
        "rapid-public-dev-anyio-ordered-correction-20260824-r9-db9e887fea43.jsonl"
    )
    assert candidate["selection_evidence_hash"] == sha256_json(selection)


def test_six_manifests_preserve_v8_v10_pairing_and_registry_admission(
    candidate: dict[str, Any],
) -> None:
    registry = live_verifier_registry()
    plan = rapid._plan(candidate, approved=True)
    plan_decision = registry.validate_authorization_plan(plan)
    assert plan_decision.accepted is True
    assert plan_decision.verifier_id == rapid.VERIFIER_ID
    assert plan_decision.requires_row_capability is True

    counts = {"lean-harness-v8": 0, "lean-harness-v10": 0}
    for row in candidate["schedule"]:
        manifest = rapid.build_rapid_v12_run_manifest(
            candidate,
            row["order"],
            repository=REPOSITORY,
        )
        counts[row["variant"]] += 1
        expected = (
            ("v12", "phase-evidence-v18")
            if row["variant"] == "lean-harness-v8"
            else ("v14", "phase-evidence-v20")
        )
        assert (manifest.tool_schema_version, manifest.context_policy_version) == expected
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
    assert counts == {"lean-harness-v8": 3, "lean-harness-v10": 3}


def test_consumed_rehearsal_bytes_still_bind_the_dispatch_boundary(
    candidate: dict[str, Any],
) -> None:
    stored = rapid.load_rapid_public_development_v12_rehearsal(
        candidate,
        repository=REPOSITORY,
    )
    raw = (REPOSITORY / rapid.REHEARSAL_PATH).read_bytes()

    assert raw == rapid.rehearsal_bytes(stored)
    assert len(raw) == 3_073
    assert sha256_bytes(raw) == (
        "sha256:5ac3e1d9302078c4832113f8d93dedb4303362448068ac8c15586ee55d055a7d"
    )
    assert stored["content_hash"] == (
        "sha256:19cdbfa3b8906d8d8c66b73a0484292b45c04c8525e12a3b12555bef3f537ef8"
    )
    assert stored["verified_manifest_count"] == 6
    assert stored["verifier_id"] == "rapid-r10-candidate-v16-plan-v16"
    assert stored["provider_calls_made"] == 0
    assert stored["docker_calls_made"] == 0
    assert stored["task_calls_made"] == 0
    assert stored["evaluator_calls_made"] == 0
    assert stored["added_model_cost_usd"] == 0.0
    assert stored["first_provider_boundary"]["provider_dispatch_blocked"] is True
    assert stored["second_provider_boundary"]["provider_dispatch_blocked"] is True


def test_candidate_tamper_and_consumed_result_remain_closed(
    candidate: dict[str, Any],
) -> None:
    changed = copy.deepcopy(candidate)
    changed["variant_contracts"]["lean-harness-v10"]["tool_schema_version"] = "v13"
    changed["execution_hash"] = sha256_json({key: changed[key] for key in rapid._EXECUTION_KEYS})
    content = {key: value for key, value in changed.items() if key != "content_hash"}
    changed["content_hash"] = sha256_json(content)
    with pytest.raises(RecoveryError):
        rapid._validate_candidate(changed)

    assert rapid._result_bundle_path(candidate, REPOSITORY).is_file()
    assert candidate["execution_authorized"] is False
