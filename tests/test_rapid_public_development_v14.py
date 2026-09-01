from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from patchloop.errors import ContractError, RecoveryError
from patchloop.evals import rapid_public_development_v14 as rapid
from patchloop.evals.live_verifier_registry import live_verifier_registry
from patchloop.util import sha256_bytes, sha256_json

REPOSITORY = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def candidate() -> dict[str, Any]:
    return rapid.load_consumed_rapid_public_development_v14_candidate(REPOSITORY)


def test_candidate_is_exact_zero_call_and_binds_v8_v15_qualification(
    candidate: dict[str, Any],
) -> None:
    raw = (REPOSITORY / rapid.CANDIDATE_PATH).read_bytes()
    assert raw == rapid.candidate_bytes(candidate)
    assert len(raw) == 33_368
    assert sha256_bytes(raw) == (
        "sha256:996896537b63914b7bd22ca07dbbecc83d6f4114449fe519214ab7ecf2340ecb"
    )
    assert candidate["execution_hash"] == (
        "sha256:4d4fbf5839ed3a498c99fe513c11c83fa3b90e2a75452c8bebd10ed0c572ac20"
    )
    assert candidate["content_hash"] == (
        "sha256:ce41bb9572131ccd10617b16489224440b536550ffc79a6812314a1b858368ce"
    )
    assert candidate["runtime_build_hash"] == (
        "sha256:34599cb84d6c2560ba15f5ebf3958fea8f07c509b2c4da20e1752138b88bbbd5"
    )
    assert candidate["official"] is False
    assert candidate["source_qualified"] is True
    assert candidate["execution_authorized"] is False
    assert candidate["provider_calls_made"] == candidate["docker_calls_made"] == 0
    assert candidate["added_model_cost_usd"] == 0.0

    selection = candidate["selection_evidence"]
    activation = selection["semantic_progress_activation"]
    contract = activation["semantic_progress_contract"]
    assert activation["runtime_build_hash"] == candidate["runtime_build_hash"]
    assert activation["predecessor_qualification"]["file_sha256"] == (
        "sha256:c13b4e6cf4c80b4eaa9c9d1016ab5e3bbdae881341c6a751a611266bb33fe7f0"
    )
    assert contract["predecessor_runtime"] == "lean-harness-v14"
    assert contract["successor_runtime"] == "lean-harness-v15"
    assert contract["tool_schema_version"] == "v19"
    assert contract["context_policy_version"] == "phase-evidence-v25"
    assert contract["contamination_disclosed"] is True
    assert contract["excluded_fixture_content_used"] is False
    assert activation["quality_improvement_established"] is False

    transition = selection["source_transition"]
    assert transition["qualified_snapshot_preserved"] is True
    assert transition["unchanged_workflow_source_count"] == len(rapid.WORKFLOW_SOURCE_FILES)
    assert transition["permitted_changed_paths"] == []
    assert all(row["unchanged"] is True for row in transition["source_rows"])
    assert candidate["predecessor_candidate"]["path"].endswith(
        "rapid-public-dev-anyio-workflow-revision-ab-20260825-r11-candidate-v17.json"
    )
    assert candidate["predecessor_result"]["path"].endswith(
        "rapid-public-dev-anyio-workflow-revision-ab-20260825-r11-c64654b6bdba.jsonl"
    )
    assert candidate["selection_evidence_hash"] == sha256_json(selection)


def test_six_manifests_preserve_v8_v15_pairing_and_registry_admission(
    candidate: dict[str, Any],
) -> None:
    registry = live_verifier_registry()
    plan = rapid._plan(candidate, approved=True)
    plan_decision = registry.validate_authorization_plan(plan)
    assert plan_decision.accepted is True
    assert plan_decision.verifier_id == rapid.VERIFIER_ID
    assert plan_decision.requires_row_capability is True

    counts = {"lean-harness-v8": 0, "lean-harness-v15": 0}
    for row in candidate["schedule"]:
        manifest = rapid.build_rapid_v14_run_manifest(
            candidate,
            row["order"],
            repository=REPOSITORY,
        )
        counts[row["variant"]] += 1
        expected = (
            ("v12", "phase-evidence-v18")
            if row["variant"] == "lean-harness-v8"
            else ("v19", "phase-evidence-v25")
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
    assert counts == {"lean-harness-v8": 3, "lean-harness-v15": 3}


def test_consumed_rehearsal_is_exact_and_stopped_before_dispatch(
    candidate: dict[str, Any],
) -> None:
    stored = rapid.load_rapid_public_development_v14_rehearsal(
        candidate,
        repository=REPOSITORY,
    )
    raw = (REPOSITORY / rapid.REHEARSAL_PATH).read_bytes()

    assert raw == rapid.rehearsal_bytes(stored)
    assert len(raw) == 3_082
    assert sha256_bytes(raw) == (
        "sha256:f2f091c2c7e0cf983fdd410916ee4d46d7cdc6f4a4cde9727ded8fc9d3dd21ca"
    )
    assert stored["content_hash"] == (
        "sha256:9f029f86b4d0ceca73dc96d7a01768e21b1227aeabb35444195e8112b33fa7a1"
    )
    assert stored["verified_manifest_count"] == 6
    assert stored["verifier_id"] == "rapid-r12-candidate-v18-plan-v18"
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
    changed["variant_contracts"]["lean-harness-v15"]["tool_schema_version"] = "v18"
    changed["execution_hash"] = sha256_json({key: changed[key] for key in rapid._EXECUTION_KEYS})
    content = {key: value for key, value in changed.items() if key != "content_hash"}
    changed["content_hash"] = sha256_json(content)
    with pytest.raises(RecoveryError):
        rapid._validate_candidate(changed)

    with pytest.raises(
        (ContractError, RecoveryError),
        match=(
            "result already exists and cannot be retried|current binding differs|"
            "semantic-progress activation change surface differs"
        ),
    ):
        rapid.run_rapid_public_development_v14(
            repository=REPOSITORY,
            approve_live_cost=True,
            approved_execution_hash=candidate["execution_hash"],
        )


def test_consumed_result_bundle_is_exact_append_only_and_not_promoted(
    candidate: dict[str, Any],
) -> None:
    path = rapid._result_bundle_path(candidate, REPOSITORY)
    raw = path.read_bytes()
    events = [json.loads(line) for line in raw.decode("utf-8").splitlines()]

    assert len(raw) == 9_575
    assert sha256_bytes(raw) == (
        "sha256:da653feb1578ffca9234fd6b976f6d62a1518dd73b0a5397bef5f5b820f4ca16"
    )
    assert len(events) == 8
    previous = None
    for event in events:
        body = {key: value for key, value in event.items() if key != "content_hash"}
        assert body["previous_event_hash"] == previous
        assert event["content_hash"] == sha256_json(body)
        previous = event["content_hash"]

    rows = [event for event in events if event["event"] == "row-terminal"]
    assert [row["order"] for row in rows] == [1, 2, 3, 4, 5, 6]
    assert [row["variant"] for row in rows] == [
        "lean-harness-v8",
        "lean-harness-v15",
        "lean-harness-v15",
        "lean-harness-v8",
        "lean-harness-v8",
        "lean-harness-v15",
    ]
    assert [row["outcome_kind"] for row in rows] == [
        "agent_failure",
        "task_failure",
        "agent_failure",
        "agent_failure",
        "agent_failure",
        "agent_failure",
    ]

    summary = events[-1]
    assert summary["event"] == "batch-completed"
    assert summary["content_hash"] == (
        "sha256:ac45cceea6a27632c03f0674fcf99d3bee1356ce4b207c734d39376b12a9fc26"
    )
    assert summary["attempted_rows"] == summary["started_rows"] == 6
    assert summary["harness_admission_failures"] == summary["token_terminals"] == 0
    assert summary["agent_failures"] == 5
    assert summary["evaluator_reached"] == summary["submissions_completed"] == 1
    assert summary["successes_at_budget"] == 0
    assert summary["model_calls"] == 180
    assert summary["tool_calls"] == 175
    assert summary["model_cost_nanos"] == 2_658_231_750
    assert summary["external_claim_authorized"] is False
    assert summary["confirmatory_promotion_automatic"] is False

    v8 = [row for row in rows if row["variant"] == "lean-harness-v8"]
    v15 = [row for row in rows if row["variant"] == "lean-harness-v15"]
    assert sum(row["model_cost_nanos"] for row in v8) == 1_742_169_750
    assert sum(row["model_cost_nanos"] for row in v15) == 916_062_000
    assert sum(row["evaluator_reached"] for row in v8) == 0
    assert sum(row["evaluator_reached"] for row in v15) == 1
