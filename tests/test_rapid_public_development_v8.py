from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import pytest
from pydantic import ValidationError

from patchloop.agent.runner import AgentRunner, issue_row_execution_authorization
from patchloop.errors import ContractError, HarnessAdmissionError
from patchloop.evals import rapid_public_development_v8 as rapid
from patchloop.evals.live_verifier_registry import live_verifier_registry
from patchloop.util import sha256_bytes, sha256_json
from scripts import run_rapid_public_development_v10 as rapid_script

REPOSITORY = Path(__file__).resolve().parents[1]
TRACE_DIAGNOSIS = (
    REPOSITORY
    / "reports"
    / "rapid-development"
    / "artifacts"
    / "rapid-public-dev-anyio-event-role-20260823-r7-public-trace-diagnosis-v1.json"
)


@pytest.fixture(scope="module")
def candidate() -> dict[str, Any]:
    return rapid.load_rapid_public_development_v8_candidate(
        repository=REPOSITORY,
        require_current_binding=False,
    )


def test_materialized_candidate_and_rehearsal_are_exact() -> None:
    candidate = rapid.load_rapid_public_development_v8_candidate(
        repository=REPOSITORY,
        require_current_binding=False,
    )
    candidate_raw = (REPOSITORY / rapid.CANDIDATE_PATH).read_bytes()
    assert len(candidate_raw) == 15_002
    assert sha256_bytes(candidate_raw) == (
        "sha256:9a0e783919cb30bb660c4bff87e7e62920be7e4f1838ecb25fba6cca14f924e2"
    )
    assert candidate["execution_hash"] == (
        "sha256:a088c64c369836f06308c3105341f220e3cfb1d3a6d492f33886b8f7f90dbdcf"
    )
    rehearsal = rapid.load_rapid_public_development_v8_rehearsal(
        candidate,
        repository=REPOSITORY,
    )
    rehearsal_raw = (REPOSITORY / rapid.REHEARSAL_PATH).read_bytes()
    assert len(rehearsal_raw) == 3_072
    assert sha256_bytes(rehearsal_raw) == (
        "sha256:7bb6b6611130b888df9d208cd574bbf3536580ce0c7a95ae444153282d2b87ba"
    )
    assert rehearsal["content_hash"] == (
        "sha256:a770e3c5ea67870157f0b347991157cb9d7f013a4cf7eee5429348ff6d1014fa"
    )


def test_candidate_binds_event_role_qualification_and_r6_predecessor(
    candidate: dict[str, Any],
) -> None:
    assert candidate["candidate_revision"] == 10
    assert candidate["official"] is False
    assert candidate["source_qualified"] is True
    assert candidate["execution_authorized"] is False
    assert candidate["provider_calls_made"] == candidate["docker_calls_made"] == 0
    assert candidate["added_model_cost_usd"] == 0.0

    selection = candidate["selection_evidence"]
    assert selection["heldout_outcomes_used"] is False
    assert selection["private_evidence_used"] is False
    event_role = selection["event_role_successor"]
    assert event_role["file_sha256"] == rapid.EVENT_ROLE_QUALIFICATION_FILE_SHA256
    assert event_role["content_hash"] == rapid.EVENT_ROLE_QUALIFICATION_CONTENT_HASH
    assert event_role["runtime_policy_version"] == "lean-harness-v6"
    assert event_role["tool_schema_version"] == "v10"
    assert event_role["context_policy_version"] == "phase-evidence-v16"
    assert event_role["r6_retry_authorized"] is False
    assert event_role["quality_improvement_established"] is False

    transition = selection["source_transition"]
    assert transition["qualified_snapshot_preserved"] is True
    assert transition["unchanged_mechanical_source_count"] == 4
    assert transition["permitted_changed_paths"] == ["patchloop/contracts.py"]
    assert [row["path"] for row in transition["source_rows"]] == list(
        rapid.EVENT_ROLE_SOURCE_FILES
    )
    assert all(
        row["unchanged"] is (row["path"] != "patchloop/contracts.py")
        for row in transition["source_rows"]
    )
    assert candidate["predecessor_candidate"]["path"].endswith(
        "rapid-public-dev-anyio-mechanical-20260823-r6-candidate-v9.json"
    )
    assert candidate["predecessor_result"]["path"].endswith(
        "rapid-public-dev-anyio-mechanical-20260823-r6-d977b523f672.jsonl"
    )
    assert candidate["selection_evidence_hash"] == sha256_json(selection)


def test_candidate_preserves_r6_task_model_budget_and_schedule(
    candidate: dict[str, Any],
) -> None:
    assert candidate["model_contract"]["model_id"] == "gpt-5.4-mini-2026-03-17"
    assert len(candidate["schedule"]) == 6
    assert tuple(
        (row["order"], row["variant"], row["repetition"])
        for row in candidate["schedule"]
    ) == rapid.EXPECTED_SCHEDULE
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
        rapid.build_rapid_v8_run_manifest(candidate, order, repository=REPOSITORY)
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
        } == {("v2", "phase-evidence-v5"), ("v10", "phase-evidence-v16")}
        assert left.created_at == right.created_at == rapid.MANIFEST_CREATED_AT


def test_v10_v16_live_manifest_is_scoped_to_r7_identity(
    candidate: dict[str, Any],
) -> None:
    manifest = rapid.build_rapid_v8_run_manifest(candidate, 2, repository=REPOSITORY)
    payload = manifest.model_dump(mode="python")
    assert payload["experiment"] is not None
    payload["experiment"]["experiment_id"] = (
        "rapid-public-dev-anyio-mechanical-20260823-r6"
    )
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


def test_rehearsal_is_byte_identical_and_makes_no_external_calls(
    candidate: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    temporary = TemporaryDirectory(prefix="rapid-v8-rehearse-", dir=REPOSITORY / ".p")
    receipt_path = Path(temporary.name) / "rehearsal.json"
    monkeypatch.setattr(rapid, "REHEARSAL_PATH", receipt_path.relative_to(REPOSITORY))
    monkeypatch.setattr(
        rapid,
        "load_rapid_public_development_v8_candidate",
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

    first = rapid.rehearse_rapid_public_development_v8(repository=REPOSITORY)
    first_bytes = receipt_path.read_bytes()
    second = rapid.rehearse_rapid_public_development_v8(repository=REPOSITORY)
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
    temporary = TemporaryDirectory(prefix="rapid-v8-approval-", dir=REPOSITORY / ".p")
    missing = Path(temporary.name) / "missing"
    monkeypatch.setattr(
        rapid,
        "load_rapid_public_development_v8_candidate",
        lambda *_args, **_kwargs: candidate,
    )
    monkeypatch.setattr(rapid, "_result_bundle_path", lambda *_args: missing)
    monkeypatch.setattr(
        rapid,
        "load_rapid_public_development_v8_rehearsal",
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
        rapid.run_rapid_public_development_v8(
            approve_live_cost=False,
            approved_execution_hash=None,
            repository=REPOSITORY,
        )
    temporary.cleanup()


def test_exact_approval_reaches_batch_start_after_live_admission(
    candidate: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class BatchStartReached(Exception):
        pass

    temporary = TemporaryDirectory(prefix="rapid-v8-live-gate-", dir=REPOSITORY / ".tmp")
    temporary_root = Path(temporary.name)
    result_path = temporary_root / "result.jsonl"
    original_write_plan = rapid._write_or_validate_plan
    original_issue_live = rapid.issue_live_execution_authorization

    monkeypatch.setattr(
        rapid,
        "load_rapid_public_development_v8_candidate",
        lambda *_args, **_kwargs: candidate,
    )
    monkeypatch.setattr(rapid, "_result_bundle_path", lambda *_args: result_path)
    monkeypatch.setattr(
        rapid,
        "_write_or_validate_plan",
        lambda selected, _root: original_write_plan(selected, temporary_root),
    )
    monkeypatch.setattr(
        rapid,
        "issue_live_execution_authorization",
        lambda execution_hash, *, root: original_issue_live(
            execution_hash,
            root=temporary_root / ".patchloop",
        ),
    )
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-never-dispatched")
    monkeypatch.setattr(rapid.DockerSandbox, "available", staticmethod(lambda: True))
    monkeypatch.setattr(
        rapid.DockerSandbox,
        "image_identity",
        lambda _self: candidate["task_bindings"][0]["evaluator_image_digest"],
    )
    monkeypatch.setattr(
        rapid,
        "_append_bundle_event",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(BatchStartReached),
    )
    monkeypatch.setattr(
        rapid.AgentRunner,
        "start",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("provider path reached before batch start")
        ),
    )

    with pytest.raises(BatchStartReached):
        rapid.run_rapid_public_development_v8(
            approve_live_cost=True,
            approved_execution_hash=candidate["execution_hash"],
            repository=REPOSITORY,
        )
    assert not result_path.exists()
    temporary.cleanup()


def test_consumed_result_is_exact_and_live_retry_stops_before_docker(
    candidate: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result_path = rapid._result_bundle_path(candidate, REPOSITORY)
    raw = result_path.read_bytes()
    assert len(raw) == 9_548
    assert sha256_bytes(raw) == (
        "sha256:4a37bcbee2090ed83937432e717f8291ad6bc2784f06e1b53162fbfef495858b"
    )
    events = [json.loads(line) for line in raw.decode("utf-8").splitlines()]
    assert [event["event"] for event in events] == [
        "batch-started",
        *("row-terminal" for _ in range(6)),
        "batch-completed",
    ]
    terminals = events[1:7]
    assert [
        (
            event["variant"],
            event["repetition"],
            event["outcome_kind"],
            event["evaluator_reached"],
            event["submission_completed"],
            event["success_at_budget"],
            event["token_terminal"],
            event["model_cost_nanos"],
        )
        for event in terminals
    ] == [
        ("baseline-v2v5", 1, "task_failure", True, True, False, False, 205_801_500),
        (
            "lean-harness-v6",
            1,
            "agent_failure",
            False,
            False,
            False,
            False,
            915_991_500,
        ),
        (
            "lean-harness-v6",
            2,
            "agent_failure",
            False,
            False,
            False,
            False,
            249_758_250,
        ),
        (
            "baseline-v2v5",
            2,
            "agent_failure",
            False,
            False,
            False,
            True,
            993_952_500,
        ),
        ("baseline-v2v5", 3, "resolved", True, True, True, False, 386_762_250),
        (
            "lean-harness-v6",
            3,
            "agent_failure",
            False,
            False,
            False,
            False,
            826_347_750,
        ),
    ]
    summary = events[-1]
    assert summary["content_hash"] == (
        "sha256:c5c89455d3f0c2500982804252ae21760a6fbc2b0a5b038d70ce0e875ed77e67"
    )
    assert {
        key: summary[key]
        for key in (
            "attempted_rows",
            "agent_rows_started",
            "harness_admission_failures",
            "agent_failures",
            "evaluator_reached",
            "submissions_completed",
            "successes_at_budget",
            "token_terminals",
            "model_cost_nanos",
        )
    } == {
        "attempted_rows": 6,
        "agent_rows_started": 6,
        "harness_admission_failures": 0,
        "agent_failures": 4,
        "evaluator_reached": 2,
        "submissions_completed": 2,
        "successes_at_budget": 1,
        "token_terminals": 1,
        "model_cost_nanos": 3_578_613_750,
    }

    monkeypatch.setattr(
        rapid,
        "load_rapid_public_development_v8_rehearsal",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("consumed execution must stop before rehearsal")
        ),
    )
    monkeypatch.setattr(
        rapid.DockerSandbox,
        "available",
        staticmethod(lambda: (_ for _ in ()).throw(AssertionError("Docker called"))),
    )
    with pytest.raises(ContractError, match="consumed and cannot be retried"):
        rapid.run_rapid_public_development_v8(
            approve_live_cost=True,
            approved_execution_hash=candidate["execution_hash"],
            repository=REPOSITORY,
        )


def test_public_trace_diagnosis_binds_r7_and_preserves_evidence_limits() -> None:
    raw = TRACE_DIAGNOSIS.read_bytes()
    diagnosis = json.loads(raw)
    assert len(raw) == 11_566
    assert sha256_bytes(raw) == (
        "sha256:1d55ec573c5caf554b530af264d49fa6da30230293320e8c459db020d83faab5"
    )
    assert diagnosis["content_hash"] == sha256_json(
        {key: value for key, value in diagnosis.items() if key != "content_hash"}
    )
    assert diagnosis["source_bundle"] == {
        "path": (
            "reports/rapid-development/"
            "rapid-public-dev-anyio-event-role-20260823-r7-a088c64c3698.jsonl"
        ),
        "bytes": 9_548,
        "file_sha256": (
            "sha256:4a37bcbee2090ed83937432e717f8291ad6bc2784f06e1b53162fbfef495858b"
        ),
        "execution_hash": (
            "sha256:a088c64c369836f06308c3105341f220e3cfb1d3a6d492f33886b8f7f90dbdcf"
        ),
        "terminal_content_hash": (
            "sha256:c5c89455d3f0c2500982804252ae21760a6fbc2b0a5b038d70ce0e875ed77e67"
        ),
    }
    assert [row["terminal_classification"] for row in diagnosis["rows"]] == [
        "PUBLIC_VISIBLE_CHECKS_PASS_HIDDEN_VERDICT_FAIL",
        "ACTIONLESS_MODEL_RESPONSE",
        "ACTIONLESS_MODEL_RESPONSE",
        "LOCAL_EXACT_REQUEST_OUTPUT_BUDGET_BLOCK",
        "RESOLVED",
        "PROVIDER_INCOMPLETE_RESPONSE_AT_OUTPUT_CAP",
    ]
    assert [row["patch_applied_count"] for row in diagnosis["rows"]] == [1, 3, 1, 2, 2, 3]
    assert sum(
        failure["count"]
        for row in diagnosis["rows"]
        for failure in row["failed_tools"]
    ) == 32
    boundary = diagnosis["evidence_boundary"]
    assert boundary["hidden_assertions_read"] is False
    assert boundary["private_evaluator_artifacts_read"] is False
    assert boundary["reference_patches_read"] is False
    assert boundary["reasoning_text_read"] is False
    assert boundary["llm_content_read"] is False
    assert boundary["provider_calls"] == boundary["docker_calls"] == 0
    assert boundary["evaluator_calls"] == 0
    assert diagnosis["disposition"] == {
        "r7_consumed": True,
        "r7_retry_authorized": False,
        "quality_improvement_established": False,
        "successor_implemented": False,
        "successor_execution_authorized": False,
        "next_work": "offline completion-policy successor design using only this public diagnosis",
    }


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
