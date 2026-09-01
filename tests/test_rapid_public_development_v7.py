from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import pytest
from pydantic import ValidationError

from patchloop.agent.runner import AgentRunner, issue_row_execution_authorization
from patchloop.errors import ContractError, HarnessAdmissionError
from patchloop.evals import rapid_public_development_v7 as rapid
from patchloop.evals.live_verifier_registry import live_verifier_registry
from patchloop.util import sha256_bytes, sha256_json
from scripts import run_rapid_public_development_v9 as rapid_script

REPOSITORY = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def candidate() -> dict[str, Any]:
    return rapid.load_rapid_public_development_v7_candidate(repository=REPOSITORY)


def test_materialized_candidate_and_rehearsal_are_exact(candidate: dict[str, Any]) -> None:
    candidate_raw = (REPOSITORY / rapid.CANDIDATE_PATH).read_bytes()
    assert len(candidate_raw) == 14_740
    assert sha256_bytes(candidate_raw) == (
        "sha256:0c73f969cd3c6181225d91111e735a670fc9e443c43e3cd48011cb01be3b5440"
    )
    assert candidate["execution_hash"] == (
        "sha256:d977b523f672e6b2d2d01674ad7909197ad797b109f39b69cdc39ab9b02c3c66"
    )
    rehearsal = rapid.load_rapid_public_development_v7_rehearsal(
        candidate,
        repository=REPOSITORY,
    )
    rehearsal_raw = (REPOSITORY / rapid.REHEARSAL_PATH).read_bytes()
    assert len(rehearsal_raw) == 3_067
    assert sha256_bytes(rehearsal_raw) == (
        "sha256:6ebeb169d7b13ff93d898ae27c2ca7e5ef460ccc53d7ba846bd6727477c5f4bd"
    )
    assert rehearsal["content_hash"] == (
        "sha256:2a2afd46e482572c6fc76a2d35dbe997f60133438b577d650fe0c52e490afcdf"
    )


def test_candidate_binds_mechanical_qualification_and_narrow_activation(
    candidate: dict[str, Any],
) -> None:
    assert candidate["candidate_revision"] == 9
    assert candidate["official"] is False
    assert candidate["source_qualified"] is True
    assert candidate["execution_authorized"] is False
    assert candidate["provider_calls_made"] == candidate["docker_calls_made"] == 0
    assert candidate["added_model_cost_usd"] == 0.0

    selection = candidate["selection_evidence"]
    assert selection["heldout_outcomes_used"] is False
    assert selection["private_evidence_used"] is False
    assert selection["pdm_task_included"] is False
    mechanical = selection["mechanical_successor"]
    assert mechanical["file_sha256"] == rapid.MECHANICAL_QUALIFICATION_FILE_SHA256
    assert mechanical["content_hash"] == rapid.MECHANICAL_QUALIFICATION_CONTENT_HASH
    assert mechanical["runtime_policy_version"] == "lean-harness-v5"
    assert mechanical["tool_schema_version"] == "v10"
    assert mechanical["context_policy_version"] == "phase-evidence-v15"
    assert mechanical["runtime_activation_authorized"] is False

    transition = selection["source_transition"]
    assert transition["qualified_snapshot_preserved"] is True
    assert transition["unchanged_mechanical_source_count"] == 6
    assert transition["permitted_changed_paths"] == ["patchloop/contracts.py"]
    assert [row["path"] for row in transition["source_rows"]] == list(rapid.MECHANICAL_SOURCE_FILES)
    assert all(
        row["unchanged"] is (row["path"] != "patchloop/contracts.py")
        for row in transition["source_rows"]
    )
    assert candidate["predecessor_candidate"]["path"].endswith(
        "rapid-public-dev-anyio-finalization-20260822-r5-candidate-v8.json"
    )
    assert candidate["predecessor_result"]["path"].endswith(
        "rapid-public-dev-anyio-finalization-20260822-r5-8676d960ad92.jsonl"
    )
    assert candidate["selection_evidence_hash"] == sha256_json(selection)


def test_candidate_preserves_r5_task_model_budget_and_schedule(
    candidate: dict[str, Any],
) -> None:
    assert candidate["model_contract"]["model_id"] == "gpt-5.4-mini-2026-03-17"
    assert len(candidate["schedule"]) == 6
    assert (
        tuple((row["order"], row["variant"], row["repetition"]) for row in candidate["schedule"])
        == rapid.EXPECTED_SCHEDULE
    )
    assert {row["task"] for row in candidate["schedule"]} == {rapid.TASK_PATH}
    assert {row["task_version"] for row in candidate["schedule"]} == {4}
    assert {row["memory_condition"] for row in candidate["schedule"]} == {"no_memory"}
    assert candidate["cost_control"] == {
        "per_run_reserve_nanos": 1_200_000_000,
        "full_schedule_reserve_nanos": 7_200_000_000,
        "hard_cap_nanos": 7_500_000_000,
        "pricing_nanos_per_token": rapid.PRICES_NANOS,
        "scheduled_run_count": 6,
        "cost_censoring_allowed": False,
        "official": False,
    }


def test_each_pair_changes_only_the_harness_contract(candidate: dict[str, Any]) -> None:
    manifests = [
        rapid.build_rapid_v7_run_manifest(candidate, order, repository=REPOSITORY)
        for order in range(1, 7)
    ]
    assert all(rapid._manifest_matches_candidate(candidate, item) for item in manifests)
    for repetition in (1, 2, 3):
        selected = [
            manifests[row["order"] - 1]
            for row in candidate["schedule"]
            if row["repetition"] == repetition
        ]
        left, right = selected
        assert left.task_id == right.task_id == rapid.TASK_ID
        assert left.task_version == right.task_version == rapid.TASK_VERSION
        assert left.public_spec_hash == right.public_spec_hash
        assert left.private_spec_hash == right.private_spec_hash
        assert left.base_commit == right.base_commit
        assert left.evaluator_image_digest == right.evaluator_image_digest
        assert left.model == right.model
        assert left.budget == right.budget == rapid.RUNTIME_BUDGET
        assert left.memory.condition == right.memory.condition
        assert {
            (left.tool_schema_version, left.context_policy_version),
            (right.tool_schema_version, right.context_policy_version),
        } == {("v2", "phase-evidence-v5"), ("v10", "phase-evidence-v15")}
        assert left.created_at == right.created_at == rapid.MANIFEST_CREATED_AT


def test_v10_v15_live_manifest_is_scoped_to_r6_identity(
    candidate: dict[str, Any],
) -> None:
    manifest = rapid.build_rapid_v7_run_manifest(candidate, 2, repository=REPOSITORY)
    payload = manifest.model_dump(mode="python")
    assert payload["experiment"] is not None
    payload["experiment"]["experiment_id"] = "rapid-public-dev-anyio-finalization-20260822-r5"
    with pytest.raises(ValidationError, match="Lean Harness requires"):
        type(manifest).model_validate(payload)


def test_registry_prevalidates_six_rows_and_capability_is_one_use(
    candidate: dict[str, Any],
) -> None:
    plan = rapid._plan(candidate, approved=True)
    decision = live_verifier_registry().validate_authorization_plan(plan)
    assert decision.handled is True
    assert decision.accepted is True
    assert decision.verifier_id == rapid.VERIFIER_ID
    assert decision.requires_row_capability is True

    prepared = rapid._prepare_batch(
        candidate,
        authority_kind="rehearsal",
        repository=REPOSITORY,
    )
    assert len(prepared.manifests) == 6
    row = issue_row_execution_authorization(
        prepared.authorization,
        prepared.manifests[0],
        active_schedule_order=1,
    )
    boundary = AgentRunner.rehearse_provider_dispatch(prepared.manifests[0], row)
    assert boundary["provider_dispatch_blocked"] is True
    with pytest.raises(HarnessAdmissionError, match="already consumed"):
        AgentRunner.rehearse_provider_dispatch(prepared.manifests[0], row)


def test_rehearsal_reaches_two_dispatch_boundaries_without_external_calls(
    candidate: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    temporary = TemporaryDirectory(prefix="rapid-v7-rehearse-", dir=REPOSITORY / ".p")
    receipt_path = Path(temporary.name) / "rehearsal.json"
    monkeypatch.setattr(rapid, "REHEARSAL_PATH", receipt_path.relative_to(REPOSITORY))
    monkeypatch.setattr(
        rapid,
        "load_rapid_public_development_v7_candidate",
        lambda *_args, **_kwargs: candidate,
    )
    monkeypatch.setattr(
        rapid.DockerSandbox,
        "available",
        staticmethod(lambda: (_ for _ in ()).throw(AssertionError("Docker called"))),
    )
    monkeypatch.setattr(
        rapid.OpenAIResponsesAdapter,
        "execute_request",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("provider called")),
    )
    monkeypatch.setattr(
        rapid.AgentRunner,
        "start",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("agent called")),
    )

    first = rapid.rehearse_rapid_public_development_v7(repository=REPOSITORY)
    first_bytes = receipt_path.read_bytes()
    second = rapid.rehearse_rapid_public_development_v7(repository=REPOSITORY)
    assert first == second
    assert first_bytes == receipt_path.read_bytes() == rapid.rehearsal_bytes(first)
    assert first["verified_manifest_count"] == 6
    assert first["first_provider_boundary"]["provider_dispatch_blocked"] is True
    assert first["second_provider_boundary"]["provider_dispatch_blocked"] is True
    assert first["inter_row_transition"]["next_schedule_order"] == 2
    assert first["provider_calls_made"] == first["docker_calls_made"] == 0
    assert first["task_calls_made"] == first["evaluator_calls_made"] == 0
    temporary.cleanup()


def test_live_entry_requires_exact_approval_before_rehearsal_or_docker(
    candidate: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    temporary = TemporaryDirectory(prefix="rapid-v7-approval-", dir=REPOSITORY / ".p")
    missing = Path(temporary.name) / "missing"
    monkeypatch.setattr(
        rapid,
        "load_rapid_public_development_v7_candidate",
        lambda *_args, **_kwargs: candidate,
    )
    monkeypatch.setattr(rapid, "_result_bundle_path", lambda *_args: missing)
    monkeypatch.setattr(
        rapid,
        "load_rapid_public_development_v7_rehearsal",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("rehearsal read before approval")
        ),
    )
    monkeypatch.setattr(
        rapid.DockerSandbox,
        "available",
        staticmethod(lambda: (_ for _ in ()).throw(AssertionError("Docker called"))),
    )
    with pytest.raises(ContractError, match="exact hash and cost-cap approval"):
        rapid.run_rapid_public_development_v7(
            approve_live_cost=False,
            approved_execution_hash=None,
            repository=REPOSITORY,
        )
    temporary.cleanup()


def test_live_entry_requires_rehearsal_before_credentials_or_docker(
    candidate: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    temporary = TemporaryDirectory(prefix="rapid-v7-gate-", dir=REPOSITORY / ".p")
    missing = Path(temporary.name) / "missing"
    monkeypatch.setattr(
        rapid,
        "load_rapid_public_development_v7_candidate",
        lambda *_args, **_kwargs: candidate,
    )
    monkeypatch.setattr(rapid, "_result_bundle_path", lambda *_args: missing)
    monkeypatch.setattr(
        rapid,
        "load_rapid_public_development_v7_rehearsal",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            HarnessAdmissionError("synthetic missing rehearsal")
        ),
    )
    monkeypatch.setattr(
        rapid.DockerSandbox,
        "available",
        staticmethod(lambda: (_ for _ in ()).throw(AssertionError("Docker called"))),
    )
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(HarnessAdmissionError, match="synthetic missing rehearsal"):
        rapid.run_rapid_public_development_v7(
            approve_live_cost=True,
            approved_execution_hash=candidate["execution_hash"],
            repository=REPOSITORY,
        )
    temporary.cleanup()


def test_consumed_result_is_exact_and_live_retry_stops_before_docker(
    candidate: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result_path = rapid._result_bundle_path(candidate, REPOSITORY)
    raw = result_path.read_bytes()
    assert len(raw) == rapid.CONSUMED_RESULT_FILE_BYTES == 7_854
    assert sha256_bytes(raw) == rapid.CONSUMED_RESULT_FILE_SHA256
    events = [json.loads(line) for line in raw.decode("utf-8").splitlines()]
    assert len(events) == 8
    terminals = [event for event in events if event["event"] == "row-terminal"]
    assert [event["outcome_kind"] for event in terminals] == [
        "agent_failure",
        "agent_failure",
        "infrastructure_error",
    ]
    assert [event["token_terminal"] for event in terminals] == [True, False, False]
    assert events[-1]["content_hash"] == (
        "sha256:c1028978a3a3f2bfa20bb2549bc27b4df81394300089ebc6f8f43b41724e68e8"
    )
    assert events[-1]["model_cost_nanos"] == 1_916_603_250
    monkeypatch.setattr(
        rapid.DockerSandbox,
        "available",
        staticmethod(lambda: (_ for _ in ()).throw(AssertionError("Docker called"))),
    )
    with pytest.raises(ContractError, match="consumed and cannot be retried"):
        rapid.run_rapid_public_development_v7(
            approve_live_cost=True,
            approved_execution_hash=candidate["execution_hash"],
            repository=REPOSITORY,
        )


def test_rehearsal_cli_rejects_live_approval_arguments() -> None:
    with pytest.raises(SystemExit, match="2"):
        rapid_script.main(
            [
                "--repository",
                str(REPOSITORY),
                "--mode",
                "rehearse",
                "--approve-live-cost",
            ]
        )
