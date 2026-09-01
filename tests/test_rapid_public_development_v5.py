from __future__ import annotations

import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import pytest

from patchloop.agent.runner import AgentRunner, issue_row_execution_authorization
from patchloop.errors import ContractError, HarnessAdmissionError, RecoveryError
from patchloop.evals import rapid_public_development_v5 as rapid
from patchloop.evals.live_verifier_registry import live_verifier_registry
from patchloop.util import sha256_bytes, sha256_json
from scripts import run_rapid_public_development_v7 as rapid_script

REPOSITORY = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def candidate() -> dict[str, Any]:
    return rapid.load_rapid_public_development_v5_candidate(repository=REPOSITORY)


def test_candidate_uses_only_retained_anyio_public_qualification(
    candidate: dict[str, Any],
) -> None:
    assert candidate["candidate_revision"] == 7
    assert candidate["official"] is False
    assert candidate["source_qualified"] is True
    assert candidate["execution_authorized"] is False
    assert candidate["provider_calls_made"] == candidate["docker_calls_made"] == 0
    assert candidate["added_model_cost_usd"] == 0.0

    selection = candidate["selection_evidence"]
    assert selection["heldout_outcomes_used"] is False
    assert selection["private_evidence_used"] is False
    assert selection["pdm_task_included"] is False
    assert selection["reference_result_role"] == (
        "check-admission-only-not-task-semantic-authority"
    )
    retained = selection["retained_anyio"]
    assert retained["status"] == "QUALIFIED_FROM_CONSUMED_V5_ROWS"
    assert retained["task_id"] == rapid.TASK_ID
    assert retained["task_version"] == rapid.TASK_VERSION
    assert selection["qualification_v5"]["execution_hash"] == (
        rapid.QUALIFICATION_V5_EXECUTION_HASH
    )
    assert selection["retention_v7"]["execution_hash"] == (
        rapid.QUALIFICATION_V7_EXECUTION_HASH
    )
    assert candidate["selection_evidence_hash"] == sha256_json(selection)


def test_candidate_is_six_balanced_rows_with_lower_reserve(
    candidate: dict[str, Any],
) -> None:
    schedule = candidate["schedule"]
    assert len(schedule) == 6
    assert tuple(
        (row["order"], row["variant"], row["repetition"]) for row in schedule
    ) == rapid.EXPECTED_SCHEDULE
    assert {row["task"] for row in schedule} == {rapid.TASK_PATH}
    assert {row["task_version"] for row in schedule} == {4}
    assert {row["memory_condition"] for row in schedule} == {"no_memory"}
    assert candidate["cost_control"] == {
        "per_run_reserve_nanos": 1_200_000_000,
        "full_schedule_reserve_nanos": 7_200_000_000,
        "hard_cap_nanos": 7_500_000_000,
        "pricing_nanos_per_token": rapid.PRICES_NANOS,
        "scheduled_run_count": 6,
        "cost_censoring_allowed": False,
        "official": False,
    }

    binding = candidate["task_bindings"]
    assert len(binding) == 1
    assert binding[0]["task_id"] == rapid.TASK_ID
    assert binding[0]["task_version"] == rapid.TASK_VERSION
    assert binding[0]["visible_check_ids"] == list(rapid.EXPECTED_CHECK_IDS)
    assert binding[0]["task_successor_opt_in"] is True
    assert binding[0]["frozen_dataset_member"] is False


def test_each_pair_changes_only_the_harness_contract(
    candidate: dict[str, Any],
) -> None:
    manifests = [
        rapid.build_rapid_v5_run_manifest(candidate, order, repository=REPOSITORY)
        for order in range(1, 7)
    ]
    assert all(rapid._manifest_matches_candidate(candidate, item) for item in manifests)

    for repetition in (1, 2, 3):
        selected = [
            manifests[row["order"] - 1]
            for row in candidate["schedule"]
            if row["repetition"] == repetition
        ]
        assert len(selected) == 2
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
        } == {("v2", "phase-evidence-v5"), ("v8", "phase-evidence-v13")}
        assert left.created_at == right.created_at == rapid.MANIFEST_CREATED_AT


def test_registry_prevalidates_all_six_rows_and_issues_one_use_capability(
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
    temporary = TemporaryDirectory(prefix="rapid-v5-rehearse-", dir=REPOSITORY / ".p")
    receipt_path = Path(temporary.name) / "rehearsal.json"
    monkeypatch.setattr(rapid, "REHEARSAL_PATH", receipt_path.relative_to(REPOSITORY))
    monkeypatch.setattr(
        rapid,
        "load_rapid_public_development_v5_candidate",
        lambda *_args, **_kwargs: candidate,
    )
    monkeypatch.setattr(
        rapid.DockerSandbox,
        "available",
        staticmethod(
            lambda: (_ for _ in ()).throw(AssertionError("Docker must not be called"))
        ),
    )
    monkeypatch.setattr(
        rapid.OpenAIResponsesAdapter,
        "execute_request",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("provider must not be called")
        ),
    )

    first = rapid.rehearse_rapid_public_development_v5(repository=REPOSITORY)
    second = rapid.rehearse_rapid_public_development_v5(repository=REPOSITORY)
    assert first == second
    assert first["verified_manifest_count"] == 6
    assert first["first_provider_boundary"]["provider_dispatch_blocked"] is True
    assert first["second_provider_boundary"]["provider_dispatch_blocked"] is True
    assert first["inter_row_transition"]["next_schedule_order"] == 2
    assert first["provider_calls_made"] == first["docker_calls_made"] == 0
    assert first["task_calls_made"] == first["evaluator_calls_made"] == 0
    assert receipt_path.read_bytes() == rapid.rehearsal_bytes(first)
    temporary.cleanup()


def test_live_entry_requires_exact_approval_before_rehearsal_or_docker(
    candidate: dict[str, Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        rapid,
        "load_rapid_public_development_v5_candidate",
        lambda *_args, **_kwargs: candidate,
    )
    monkeypatch.setattr(rapid, "_result_bundle_path", lambda *_args: tmp_path / "missing")
    monkeypatch.setattr(
        rapid,
        "load_rapid_public_development_v5_rehearsal",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("rehearsal must not be read")
        ),
    )
    monkeypatch.setattr(
        rapid.DockerSandbox,
        "available",
        staticmethod(
            lambda: (_ for _ in ()).throw(AssertionError("Docker must not be called"))
        ),
    )
    with pytest.raises(ContractError, match="exact hash and cost-cap approval"):
        rapid.run_rapid_public_development_v5(
            approve_live_cost=False,
            approved_execution_hash=None,
            repository=REPOSITORY,
        )


def test_live_entry_requires_rehearsal_before_credentials_or_docker(
    candidate: dict[str, Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        rapid,
        "load_rapid_public_development_v5_candidate",
        lambda *_args, **_kwargs: candidate,
    )
    monkeypatch.setattr(rapid, "_result_bundle_path", lambda *_args: tmp_path / "missing")
    monkeypatch.setattr(
        rapid,
        "load_rapid_public_development_v5_rehearsal",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            HarnessAdmissionError("synthetic missing rehearsal")
        ),
    )
    monkeypatch.setattr(
        rapid.DockerSandbox,
        "available",
        staticmethod(
            lambda: (_ for _ in ()).throw(AssertionError("Docker must not be called"))
        ),
    )
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(HarnessAdmissionError, match="synthetic missing rehearsal"):
        rapid.run_rapid_public_development_v5(
            approve_live_cost=True,
            approved_execution_hash=candidate["execution_hash"],
            repository=REPOSITORY,
        )


def test_pre_agent_contract_terminal_is_excluded_from_agent_failure_rate(
    candidate: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class EmptyState:
        @staticmethod
        def list_events(_run_id: str) -> list[Any]:
            return []

        @staticmethod
        def list_runs() -> list[Any]:
            return []

    class AdmissionFailingRunner:
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            self.state = EmptyState()

        @staticmethod
        def start(*_args: Any, **_kwargs: Any) -> None:
            raise HarnessAdmissionError("synthetic row admission rejection")

    temporary = TemporaryDirectory(prefix="rapid-v5-terminal-", dir=REPOSITORY / ".p")
    bundle = Path(temporary.name) / "run.jsonl"
    prepared = rapid._prepare_batch(
        candidate,
        authority_kind="rehearsal",
        repository=REPOSITORY,
    )
    monkeypatch.setattr(
        rapid,
        "load_rapid_public_development_v5_candidate",
        lambda *_args, **_kwargs: candidate,
    )
    monkeypatch.setattr(rapid, "_result_bundle_path", lambda *_args: bundle)
    monkeypatch.setattr(
        rapid,
        "load_rapid_public_development_v5_rehearsal",
        lambda *_args, **_kwargs: {},
    )
    monkeypatch.setattr(rapid, "_write_or_validate_plan", lambda *_args: Path("plan"))
    monkeypatch.setattr(
        rapid,
        "issue_live_execution_authorization",
        lambda *_args, **_kwargs: object(),
    )
    monkeypatch.setattr(rapid, "_prepare_batch", lambda *_args, **_kwargs: prepared)
    monkeypatch.setattr(rapid.DockerSandbox, "available", staticmethod(lambda: True))
    monkeypatch.setattr(
        rapid.DockerSandbox,
        "image_identity",
        lambda self: self.image.rsplit("@", maxsplit=1)[1],
    )
    monkeypatch.setattr(rapid, "AgentRunner", AdmissionFailingRunner)
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-placeholder")

    summary = rapid.run_rapid_public_development_v5(
        approve_live_cost=True,
        approved_execution_hash=candidate["execution_hash"],
        repository=REPOSITORY,
    )
    events = [json.loads(line) for line in bundle.read_text(encoding="utf-8").splitlines()]
    assert [event["event"] for event in events] == [
        "batch-started",
        "row-terminal",
        *("row-not-started" for _ in range(5)),
        "batch-completed",
    ]
    assert events[1]["outcome_kind"] == rapid.HARNESS_ADMISSION_FAILURE
    assert events[1]["harness_admission_failure"] is True
    assert events[1]["agent_started"] is False
    assert summary["harness_admission_failures"] == 1
    assert summary["agent_rows_started"] == summary["agent_failures"] == 0
    assert summary["agent_failure_rate"] is None
    temporary.cleanup()


def test_active_prefix_is_append_only_and_rejects_schedule_drift(
    candidate: dict[str, Any],
) -> None:
    start = rapid._seal_event(rapid._batch_started_event(candidate), None)
    terminal = rapid._rehearsed_resolved_terminal(candidate, start["content_hash"])
    assert rapid._active_bundle_next_order_from_events(candidate, [start]) == 1
    assert rapid._active_bundle_next_order_from_events(candidate, [start, terminal]) == 2

    body = {
        key: value
        for key, value in terminal.items()
        if key not in {"content_hash", "previous_event_hash"}
    }
    drifted = rapid._seal_event(
        {**body, "task_version": 1},
        start["content_hash"],
    )
    assert rapid._active_bundle_next_order_from_events(candidate, [start, drifted]) is None


def test_candidate_tampering_changes_execution_identity(candidate: dict[str, Any]) -> None:
    tampered = json.loads(json.dumps(candidate))
    tampered["schedule"][0]["task_version"] = 1
    with pytest.raises(RecoveryError, match="identity differs"):
        rapid.candidate_bytes(tampered)


def test_materialized_candidate_rehearsal_and_consumed_result_are_exact(
    candidate: dict[str, Any],
) -> None:
    candidate_path = REPOSITORY / rapid.CANDIDATE_PATH
    rehearsal_path = REPOSITORY / rapid.REHEARSAL_PATH
    assert candidate_path.stat().st_size == 9_380
    assert sha256_bytes(candidate_path.read_bytes()) == (
        "sha256:da7c021cf3b3ed5e5510e384b3d36d2a3a2fa9be5df22af8b0d615729169f730"
    )
    assert rapid.load_rapid_public_development_v5_candidate(REPOSITORY) == candidate
    assert rehearsal_path.stat().st_size == 3_065
    assert sha256_bytes(rehearsal_path.read_bytes()) == (
        "sha256:db0464a1486f85aeb33c33a8658848671bf4a81baa4b608a0448636f4609df7f"
    )
    receipt = rapid.load_rapid_public_development_v5_rehearsal(
        candidate, repository=REPOSITORY
    )
    assert receipt["content_hash"] == (
        "sha256:670db4f7a3a752ec45879a00539f75e6c52380e3f71f0c089b7555f1305facd9"
    )
    result_path = rapid._result_bundle_path(candidate, REPOSITORY)
    assert result_path.stat().st_size == 9_530
    assert sha256_bytes(result_path.read_bytes()) == (
        "sha256:dc3fdc8d35f236cd810d47b7be4dff55599d0a242f5c4be9cd98071d7d8ccf8c"
    )
    events = [json.loads(line) for line in result_path.read_text(encoding="utf-8").splitlines()]
    assert [event["event"] for event in events] == [
        "batch-started",
        *("row-terminal" for _ in range(6)),
        "batch-completed",
    ]
    previous = None
    for event in events:
        body = {key: value for key, value in event.items() if key != "content_hash"}
        assert body["previous_event_hash"] == previous
        assert event["content_hash"] == sha256_json(body)
        previous = event["content_hash"]
    rows = events[1:-1]
    assert [row["order"] for row in rows] == list(range(1, 7))
    assert [row["outcome_kind"] for row in rows] == ["agent_failure"] * 6
    assert [row["token_terminal"] for row in rows] == [True, False, False, True, True, False]
    summary = events[-1]
    assert summary["content_hash"] == (
        "sha256:65222f5a733ee2c757c87b6db76d03dd0a182a90b44e6889429041424e164f74"
    )
    assert summary["model_cost_nanos"] == 4_262_620_650
    assert summary["model_calls"] == 233
    assert summary["tool_calls"] == 401
    assert summary["harness_admission_failures"] == 0
    assert summary["evaluator_reached"] == summary["submissions_completed"] == 0
    assert summary["successes_at_budget"] == 0
    with pytest.raises(ContractError, match="consumed and cannot be retried"):
        rapid.run_rapid_public_development_v5(
            approve_live_cost=True,
            approved_execution_hash=candidate["execution_hash"],
            repository=REPOSITORY,
        )


def test_live_script_loads_and_restores_exact_env_file(
    candidate: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("OPENAI_API_KEY=test-only-placeholder\n", encoding="utf-8")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    def fake_run(**kwargs: Any) -> dict[str, Any]:
        assert os.environ.get("OPENAI_API_KEY") == "test-only-placeholder"
        return {"execution_hash": kwargs["approved_execution_hash"], "ok": True}

    monkeypatch.setattr(rapid_script, "run_rapid_public_development_v5", fake_run)
    assert (
        rapid_script.main(
            [
                "--mode",
                "live",
                "--approve-live-cost",
                "--approved-execution-hash",
                candidate["execution_hash"],
                "--env-file",
                str(env_file),
            ]
        )
        == 0
    )
    assert "OPENAI_API_KEY" not in os.environ
    assert json.loads(capsys.readouterr().out)["ok"] is True
