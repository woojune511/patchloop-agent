from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest

from patchloop.errors import ContractError, RecoveryError
from patchloop.evals import rapid_public_development_v13 as rapid
from patchloop.evals.live_verifier_registry import live_verifier_registry
from patchloop.util import sha256_bytes, sha256_json

REPOSITORY = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def candidate() -> dict[str, Any]:
    return rapid.load_consumed_rapid_public_development_v13_candidate(REPOSITORY)


def test_candidate_is_exact_zero_call_and_binds_v8_v12_qualification(
    candidate: dict[str, Any],
) -> None:
    raw = (REPOSITORY / rapid.CANDIDATE_PATH).read_bytes()
    assert raw == rapid.candidate_bytes(candidate)
    assert len(raw) == 21_582
    assert sha256_bytes(raw) == (
        "sha256:31ab3c6e63c29c72ed1900c15855c182e34df1aba861cdf0d480a3ae449a5407"
    )
    assert candidate["execution_hash"] == (
        "sha256:c64654b6bdba62483ff0b3c282d7dd9d950445b5b4c962cda88e0222700e5212"
    )
    assert candidate["content_hash"] == (
        "sha256:eb443160a6153d637f98eccbaac1c9c8b234d337397b72c18b8d74c872a01660"
    )
    assert candidate["runtime_build_hash"] == (
        "sha256:211138904135db88b603a218ea5896cbfb52821fa1e1dfe1371058a44bd6c172"
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
    assert successor["runtime_versions"] == ["lean-harness-v11", "lean-harness-v12"]
    assert successor["tool_schema_versions"] == ["v15", "v16"]
    assert successor["context_policy_versions"] == [
        "phase-evidence-v21",
        "phase-evidence-v22",
    ]
    assert successor["quality_improvement_established"] is False

    transition = selection["source_transition"]
    assert transition["qualified_snapshot_preserved"] is True
    assert transition["unchanged_workflow_source_count"] == len(rapid.WORKFLOW_SOURCE_FILES)
    assert transition["permitted_changed_paths"] == []
    assert all(row["unchanged"] is True for row in transition["source_rows"])
    assert candidate["predecessor_candidate"]["path"].endswith(
        "rapid-public-dev-anyio-workflow-ab-20260824-r10-candidate-v16.json"
    )
    assert candidate["predecessor_result"]["path"].endswith(
        "rapid-public-dev-anyio-workflow-ab-20260824-r10-cbe3f560b03b.jsonl"
    )
    assert candidate["selection_evidence_hash"] == sha256_json(selection)


def test_six_manifests_preserve_v8_v12_pairing_and_registry_admission(
    candidate: dict[str, Any],
) -> None:
    registry = live_verifier_registry()
    plan = rapid._plan(candidate, approved=True)
    plan_decision = registry.validate_authorization_plan(plan)
    assert plan_decision.accepted is True
    assert plan_decision.verifier_id == rapid.VERIFIER_ID
    assert plan_decision.requires_row_capability is True

    counts = {"lean-harness-v8": 0, "lean-harness-v12": 0}
    for row in candidate["schedule"]:
        manifest = rapid.build_rapid_v13_run_manifest(
            candidate,
            row["order"],
            repository=REPOSITORY,
        )
        counts[row["variant"]] += 1
        expected = (
            ("v12", "phase-evidence-v18")
            if row["variant"] == "lean-harness-v8"
            else ("v16", "phase-evidence-v22")
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
    assert counts == {"lean-harness-v8": 3, "lean-harness-v12": 3}


def test_consumed_rehearsal_is_exact_and_stopped_before_dispatch(
    candidate: dict[str, Any],
) -> None:
    stored = rapid.load_rapid_public_development_v13_rehearsal(
        candidate,
        repository=REPOSITORY,
    )
    raw = (REPOSITORY / rapid.REHEARSAL_PATH).read_bytes()

    assert raw == rapid.rehearsal_bytes(stored)
    assert len(raw) == 3_082
    assert sha256_bytes(raw) == (
        "sha256:408e3420c535e03a29afcc6d5a9d12fe1d6a4c8c20467084edf31732aaaec250"
    )
    assert stored["content_hash"] == (
        "sha256:1a9569a3bdb645a6220b3408bd6e398eef9a7dc55ac431b2ba3810856bb2e2b3"
    )
    assert stored["verified_manifest_count"] == 6
    assert stored["verifier_id"] == "rapid-r11-candidate-v17-plan-v17"
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
    changed["variant_contracts"]["lean-harness-v12"]["tool_schema_version"] = "v15"
    changed["execution_hash"] = sha256_json({key: changed[key] for key in rapid._EXECUTION_KEYS})
    content = {key: value for key, value in changed.items() if key != "content_hash"}
    changed["content_hash"] = sha256_json(content)
    with pytest.raises(RecoveryError):
        rapid._validate_candidate(changed)

    assert rapid._result_bundle_path(candidate, REPOSITORY).exists()
    with pytest.raises(
        (ContractError, RecoveryError),
        match=(
            "result already exists and cannot be retried|current binding differs|"
            "workflow successor v2 qualification source differs"
        ),
    ):
        rapid.run_rapid_public_development_v13(
            repository=REPOSITORY,
            approve_live_cost=False,
            approved_execution_hash=None,
        )
