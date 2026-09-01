from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import pytest
from pydantic import ValidationError

from patchloop.agent.runner import AgentRunner, issue_row_execution_authorization
from patchloop.errors import ContractError, HarnessAdmissionError, RecoveryError
from patchloop.evals import rapid_public_development_v9 as rapid
from patchloop.evals.live_verifier_registry import (
    LiveVerifierEntry,
    LiveVerifierRegistry,
    live_verifier_registry,
)
from patchloop.util import sha256_bytes, sha256_json
from scripts import run_rapid_public_development_v11 as rapid_script

REPOSITORY = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def candidate() -> dict[str, Any]:
    return rapid.load_consumed_rapid_public_development_v9_candidate(
        repository=REPOSITORY
    )


@pytest.fixture(scope="module")
def frozen_candidate() -> dict[str, Any]:
    return rapid.load_consumed_rapid_public_development_v9_candidate(
        repository=REPOSITORY
    )


def test_materialized_candidate_and_rehearsal_are_exact(
    frozen_candidate: dict[str, Any],
) -> None:
    candidate = frozen_candidate
    with pytest.raises(RecoveryError):
        rapid.load_rapid_public_development_v9_candidate(repository=REPOSITORY)
    candidate_raw = (REPOSITORY / rapid.CANDIDATE_PATH).read_bytes()
    assert candidate_raw == rapid.candidate_bytes(candidate)
    assert len(candidate_raw) == 16_596
    assert sha256_bytes(candidate_raw) == (
        "sha256:ac1466bbb5c1ad449676d4c97246e5078328ea48a8fd4c6ca6eb575e9461a200"
    )
    assert candidate["execution_hash"] == (
        "sha256:553f7cfca404df2985fe5a79b267738c4e63afadd2997c9451e1fc35328faa74"
    )
    assert candidate["content_hash"] == (
        "sha256:79539c739d9343bd43c65bb843598bae6bc491c2f4323740e138602bda17615d"
    )
    assert candidate["runtime_build_hash"] == (
        "sha256:7c1f3b3e4a3873e34325ecf2c4646743ce487a97a3645139e6bfc180ecd560aa"
    )
    rehearsal = rapid.load_rapid_public_development_v9_rehearsal(
        candidate,
        repository=REPOSITORY,
    )
    rehearsal_raw = (REPOSITORY / rapid.REHEARSAL_PATH).read_bytes()
    assert rehearsal_raw == rapid.rehearsal_bytes(rehearsal)
    assert len(rehearsal_raw) == 3_076
    assert sha256_bytes(rehearsal_raw) == (
        "sha256:a71b7f74ce0ae9b9c6f861d0d9efaf6fe810fd61d409f3c641a1b39b1905ef4a"
    )
    assert rehearsal["content_hash"] == (
        "sha256:55c44f5407b018f483694978e49b051cc28e35c98498746d3d3c6310f7b31b8d"
    )
    assert rehearsal["verifier_entry_hash"] == (
        "sha256:e885adac2d9924605d8d72d76776ef549cb9a05805e3a0a8b0f3b7c4caab5989"
    )
    assert rehearsal["execution_hash"] == candidate["execution_hash"]


def test_consumed_result_bundle_is_exact_and_hash_chained(
    frozen_candidate: dict[str, Any],
) -> None:
    candidate = frozen_candidate
    path = rapid._result_bundle_path(candidate, REPOSITORY)
    raw = path.read_bytes()
    assert len(raw) == 9_567
    assert sha256_bytes(raw) == (
        "sha256:5d05e062a32ed4d912fdde93f7ee4048f118f461f888d1516fbb82b7d6e9ce9c"
    )
    events = [json.loads(line) for line in raw.decode("utf-8").splitlines()]
    assert len(events) == 8

    previous = None
    for event in events:
        body = {key: value for key, value in event.items() if key != "content_hash"}
        assert body["previous_event_hash"] == previous
        assert event["content_hash"] == sha256_json(body)
        previous = event["content_hash"]

    rows = events[1:7]
    assert [event["event"] for event in events] == [
        "batch-started",
        *("row-terminal" for _ in range(6)),
        "batch-completed",
    ]
    assert [row["order"] for row in rows] == list(range(1, 7))
    assert [row["outcome_kind"] for row in rows] == ["agent_failure"] * 6
    assert [row["token_terminal"] for row in rows] == [True, False, False, True, True, False]
    assert [row["evaluator_reached"] for row in rows] == [False] * 6
    assert [row["submission_completed"] for row in rows] == [False] * 6
    assert [row["success_at_budget"] for row in rows] == [False] * 6
    assert [row["model_cost_nanos"] for row in rows] == [
        1_011_367_500,
        828_184_500,
        736_663_500,
        947_202_750,
        917_305_500,
        861_782_250,
    ]
    assert [row["usage"]["model_calls"] for row in rows] == [56, 42, 29, 52, 57, 41]
    assert [row["usage"]["tool_calls"] for row in rows] == [97, 54, 41, 94, 103, 55]

    summary = events[-1]
    assert summary["content_hash"] == (
        "sha256:a9ce3a74b3c1c22bde88910c0b43f4f66443eb9e58d12034e1763377aa5765dc"
    )
    assert summary["model_cost_nanos"] == 5_302_506_000
    assert summary["started_rows"] == summary["agent_failures"] == 6
    assert summary["harness_admission_failures"] == 0
    assert summary["evaluator_reached"] == summary["submissions_completed"] == 0
    assert summary["successes_at_budget"] == 0
    assert summary["model_calls"] == 277
    assert summary["tool_calls"] == 444


def test_candidate_binds_completion_qualification_and_r7_predecessor(
    candidate: dict[str, Any],
) -> None:
    assert candidate["candidate_revision"] == 11
    assert candidate["official"] is False
    assert candidate["source_qualified"] is True
    assert candidate["execution_authorized"] is False
    assert candidate["provider_calls_made"] == candidate["docker_calls_made"] == 0
    assert candidate["added_model_cost_usd"] == 0.0

    selection = candidate["selection_evidence"]
    assert selection["heldout_outcomes_used"] is False
    assert selection["private_evidence_used"] is False
    completion = selection["completion_policy_successor"]
    assert completion["file_sha256"] == rapid.COMPLETION_QUALIFICATION_FILE_SHA256
    assert completion["content_hash"] == rapid.COMPLETION_QUALIFICATION_CONTENT_HASH
    assert completion["scenario_set_hash"] == rapid.COMPLETION_QUALIFICATION_SCENARIO_SET_HASH
    assert completion["runtime_policy_version"] == "lean-harness-v7"
    assert completion["tool_schema_version"] == "v11"
    assert completion["context_policy_version"] == "phase-evidence-v17"
    assert completion["quality_improvement_established"] is False

    transition = selection["source_transition"]
    assert transition["qualified_snapshot_preserved"] is True
    assert transition["unchanged_mechanical_source_count"] == 5
    assert transition["permitted_changed_paths"] == ["patchloop/contracts.py"]
    assert [row["path"] for row in transition["source_rows"]] == list(
        rapid.COMPLETION_SOURCE_FILES
    )
    assert all(
        row["unchanged"] is (row["path"] != "patchloop/contracts.py")
        for row in transition["source_rows"]
    )
    assert candidate["predecessor_candidate"]["path"].endswith(
        "rapid-public-dev-anyio-event-role-20260823-r7-candidate-v10.json"
    )
    assert candidate["predecessor_result"]["path"].endswith(
        "rapid-public-dev-anyio-event-role-20260823-r7-a088c64c3698.jsonl"
    )
    assert candidate["selection_evidence_hash"] == sha256_json(selection)


def test_candidate_preserves_r7_task_model_budget_and_schedule(
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
        rapid.build_rapid_v9_run_manifest(candidate, order, repository=REPOSITORY)
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
        } == {("v2", "phase-evidence-v5"), ("v11", "phase-evidence-v17")}
        assert left.created_at == right.created_at == rapid.MANIFEST_CREATED_AT


def test_v11_v17_live_manifest_is_scoped_to_r8_identity(
    candidate: dict[str, Any],
) -> None:
    manifest = rapid.build_rapid_v9_run_manifest(candidate, 2, repository=REPOSITORY)
    payload = manifest.model_dump(mode="python")
    assert payload["experiment"] is not None
    payload["experiment"]["experiment_id"] = (
        "rapid-public-dev-anyio-event-role-20260823-r7"
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


def test_verifier_entry_hash_is_stable_when_registry_grows() -> None:
    entry = LiveVerifierEntry(
        verifier_id=rapid.VERIFIER_ID,
        experiment_id=rapid.EXPERIMENT_ID,
        plan_schema=rapid.PLAN_SCHEMA,
        plan_kind=rapid.PLAN_KIND,
        purpose="rapid_public_development",
        official=False,
        module="example.current",
        function="verify",
        call_shape="rapid",
        requires_row_capability=True,
    )
    later = LiveVerifierEntry(
        verifier_id="later-verifier",
        experiment_id="later-experiment",
        plan_schema="later-schema",
        plan_kind=None,
        purpose="rapid_public_development",
        official=False,
        module="example.later",
        function="verify",
        call_shape="rapid",
    )
    before = LiveVerifierRegistry((entry,))
    after = LiveVerifierRegistry((entry, later))

    lookup = {
        "experiment_id": rapid.EXPERIMENT_ID,
        "plan_schema": rapid.PLAN_SCHEMA,
        "plan_kind": rapid.PLAN_KIND,
    }
    assert before.descriptor_hash_for(**lookup) == after.descriptor_hash_for(**lookup)
    assert before.content_hash != after.content_hash
    with pytest.raises(KeyError, match="no matching"):
        before.descriptor_hash_for(
            experiment_id="unknown",
            plan_schema=rapid.PLAN_SCHEMA,
            plan_kind=rapid.PLAN_KIND,
        )


def test_rehearsal_is_byte_identical_and_makes_no_external_calls(
    candidate: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with TemporaryDirectory(prefix="rapid-v9-rehearse-", dir=REPOSITORY / ".p") as temp:
        receipt_path = Path(temp) / "rehearsal.json"
        monkeypatch.setattr(rapid, "REHEARSAL_PATH", receipt_path.relative_to(REPOSITORY))
        monkeypatch.setattr(
            rapid,
            "load_rapid_public_development_v9_candidate",
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

        first = rapid.rehearse_rapid_public_development_v9(repository=REPOSITORY)
        first_bytes = receipt_path.read_bytes()
        second = rapid.rehearse_rapid_public_development_v9(repository=REPOSITORY)
        assert first == second
        assert first_bytes == receipt_path.read_bytes() == rapid.rehearsal_bytes(first)
        assert first["verified_manifest_count"] == 6
        assert first["first_provider_boundary"]["provider_dispatch_blocked"] is True
        assert first["second_provider_boundary"]["provider_dispatch_blocked"] is True
        assert first["inter_row_transition"]["next_schedule_order"] == 2
        assert first["provider_calls_made"] == first["docker_calls_made"] == 0
        assert first["task_calls_made"] == first["evaluator_calls_made"] == 0


def test_live_entry_requires_exact_approval_before_rehearsal_or_docker(
    candidate: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with TemporaryDirectory(prefix="rapid-v9-approval-", dir=REPOSITORY / ".p") as temp:
        missing = Path(temp) / "missing"
        monkeypatch.setattr(
            rapid,
            "load_rapid_public_development_v9_candidate",
            lambda *_args, **_kwargs: candidate,
        )
        monkeypatch.setattr(rapid, "_result_bundle_path", lambda *_args: missing)
        monkeypatch.setattr(
            rapid,
            "load_rapid_public_development_v9_rehearsal",
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
            rapid.run_rapid_public_development_v9(
                approve_live_cost=False,
                approved_execution_hash=None,
                repository=REPOSITORY,
            )


def test_consumed_live_retry_stops_before_rehearsal_docker_or_provider(
    candidate: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        rapid,
        "load_rapid_public_development_v9_rehearsal",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("rehearsal reached for consumed execution")
        ),
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

    with pytest.raises(ContractError, match="consumed and cannot be retried"):
        rapid.run_rapid_public_development_v9(
            approve_live_cost=True,
            approved_execution_hash=candidate["execution_hash"],
            repository=REPOSITORY,
        )


def test_exact_approval_reaches_batch_start_after_live_admission(
    candidate: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class BatchStartReached(Exception):
        pass

    with TemporaryDirectory(prefix="rapid-v9-live-gate-", dir=REPOSITORY / ".tmp") as temp:
        temporary_root = Path(temp)
        result_path = temporary_root / "result.jsonl"
        original_write_plan = rapid._write_or_validate_plan
        original_issue_live = rapid.issue_live_execution_authorization

        monkeypatch.setattr(rapid, "_result_bundle_path", lambda *_args: result_path)
        monkeypatch.setattr(
            rapid,
            "load_rapid_public_development_v9_candidate",
            lambda *_args, **_kwargs: candidate,
        )
        monkeypatch.setattr(
            rapid,
            "load_rapid_public_development_v9_rehearsal",
            lambda *_args, **_kwargs: {"execution_hash": candidate["execution_hash"]},
        )
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
            rapid.run_rapid_public_development_v9(
                approve_live_cost=True,
                approved_execution_hash=candidate["execution_hash"],
                repository=REPOSITORY,
            )
        assert not result_path.exists()


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
