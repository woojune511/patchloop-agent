from __future__ import annotations

import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import pytest
from pydantic import ValidationError

from patchloop.agent.runner import AgentRunner, issue_row_execution_authorization
from patchloop.errors import ContractError, HarnessAdmissionError, RecoveryError
from patchloop.evals import rapid_public_development_v6 as rapid
from patchloop.evals.live_verifier_registry import live_verifier_registry
from patchloop.util import sha256_bytes, sha256_json
from scripts import run_rapid_public_development_v8 as rapid_script

REPOSITORY = Path(__file__).resolve().parents[1]
TRACE_DIAGNOSIS = (
    REPOSITORY
    / "reports"
    / "rapid-development"
    / "artifacts"
    / "rapid-public-dev-anyio-finalization-20260822-r5-public-trace-diagnosis-v1.json"
)


@pytest.fixture(scope="module")
def candidate() -> dict[str, Any]:
    return rapid.load_rapid_public_development_v6_candidate(repository=REPOSITORY)


def test_candidate_binds_retained_anyio_and_offline_finalization_qualification(
    candidate: dict[str, Any],
) -> None:
    assert candidate["candidate_revision"] == 8
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
    assert selection["retention_v7"]["execution_hash"] == (rapid.QUALIFICATION_V7_EXECUTION_HASH)
    finalization = selection["finalization_successor"]
    assert finalization["file_sha256"] == (rapid.FINALIZATION_QUALIFICATION_FILE_SHA256)
    assert finalization["content_hash"] == (rapid.FINALIZATION_QUALIFICATION_CONTENT_HASH)
    assert finalization["runtime_policy_version"] == "lean-harness-v4"
    assert finalization["tool_schema_version"] == "v9"
    assert finalization["context_policy_version"] == "phase-evidence-v14"
    assert finalization["runtime_activation_authorized"] is False
    assert candidate["predecessor_candidate"]["file_sha256"] == (
        "sha256:da7c021cf3b3ed5e5510e384b3d36d2a3a2fa9be5df22af8b0d615729169f730"
    )
    assert candidate["predecessor_result"]["file_sha256"] == (
        "sha256:dc3fdc8d35f236cd810d47b7be4dff55599d0a242f5c4be9cd98071d7d8ccf8c"
    )
    assert candidate["selection_evidence_hash"] == sha256_json(selection)


def test_candidate_is_six_balanced_rows_with_lower_reserve(
    candidate: dict[str, Any],
) -> None:
    schedule = candidate["schedule"]
    assert len(schedule) == 6
    assert (
        tuple((row["order"], row["variant"], row["repetition"]) for row in schedule)
        == rapid.EXPECTED_SCHEDULE
    )
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
        rapid.build_rapid_v6_run_manifest(candidate, order, repository=REPOSITORY)
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
        } == {("v2", "phase-evidence-v5"), ("v9", "phase-evidence-v14")}
        assert left.created_at == right.created_at == rapid.MANIFEST_CREATED_AT


def test_v9_v14_live_manifest_is_scoped_to_the_new_r5_identity(
    candidate: dict[str, Any],
) -> None:
    manifest = rapid.build_rapid_v6_run_manifest(
        candidate,
        2,
        repository=REPOSITORY,
    )
    payload = manifest.model_dump(mode="python")
    assert payload["experiment"] is not None
    payload["experiment"]["experiment_id"] = "rapid-public-dev-anyio-targeted-20260822-r4"

    with pytest.raises(ValidationError, match="Lean Harness requires"):
        type(manifest).model_validate(payload)


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
    temporary = TemporaryDirectory(prefix="rapid-v6-rehearse-", dir=REPOSITORY / ".p")
    receipt_path = Path(temporary.name) / "rehearsal.json"
    monkeypatch.setattr(rapid, "REHEARSAL_PATH", receipt_path.relative_to(REPOSITORY))
    monkeypatch.setattr(
        rapid,
        "load_rapid_public_development_v6_candidate",
        lambda *_args, **_kwargs: candidate,
    )
    monkeypatch.setattr(
        rapid.DockerSandbox,
        "available",
        staticmethod(lambda: (_ for _ in ()).throw(AssertionError("Docker must not be called"))),
    )
    monkeypatch.setattr(
        rapid.OpenAIResponsesAdapter,
        "execute_request",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("provider must not be called")
        ),
    )

    first = rapid.rehearse_rapid_public_development_v6(repository=REPOSITORY)
    second = rapid.rehearse_rapid_public_development_v6(repository=REPOSITORY)
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
        "load_rapid_public_development_v6_candidate",
        lambda *_args, **_kwargs: candidate,
    )
    monkeypatch.setattr(rapid, "_result_bundle_path", lambda *_args: tmp_path / "missing")
    monkeypatch.setattr(
        rapid,
        "load_rapid_public_development_v6_rehearsal",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("rehearsal must not be read")
        ),
    )
    monkeypatch.setattr(
        rapid.DockerSandbox,
        "available",
        staticmethod(lambda: (_ for _ in ()).throw(AssertionError("Docker must not be called"))),
    )
    with pytest.raises(ContractError, match="exact hash and cost-cap approval"):
        rapid.run_rapid_public_development_v6(
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
        "load_rapid_public_development_v6_candidate",
        lambda *_args, **_kwargs: candidate,
    )
    monkeypatch.setattr(rapid, "_result_bundle_path", lambda *_args: tmp_path / "missing")
    monkeypatch.setattr(
        rapid,
        "load_rapid_public_development_v6_rehearsal",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            HarnessAdmissionError("synthetic missing rehearsal")
        ),
    )
    monkeypatch.setattr(
        rapid.DockerSandbox,
        "available",
        staticmethod(lambda: (_ for _ in ()).throw(AssertionError("Docker must not be called"))),
    )
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(HarnessAdmissionError, match="synthetic missing rehearsal"):
        rapid.run_rapid_public_development_v6(
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

    temporary = TemporaryDirectory(prefix="rapid-v6-terminal-", dir=REPOSITORY / ".p")
    bundle = Path(temporary.name) / "run.jsonl"
    prepared = rapid._prepare_batch(
        candidate,
        authority_kind="rehearsal",
        repository=REPOSITORY,
    )
    monkeypatch.setattr(
        rapid,
        "load_rapid_public_development_v6_candidate",
        lambda *_args, **_kwargs: candidate,
    )
    monkeypatch.setattr(rapid, "_result_bundle_path", lambda *_args: bundle)
    monkeypatch.setattr(
        rapid,
        "load_rapid_public_development_v6_rehearsal",
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

    summary = rapid.run_rapid_public_development_v6(
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
    assert candidate_path.stat().st_size == 10_347
    assert sha256_bytes(candidate_path.read_bytes()) == (
        "sha256:4229a317a6bb52a1159503cdd453c0f748e656b19c8a8f5b041eaf7db93524eb"
    )
    assert candidate_path.read_bytes() == rapid.candidate_bytes(candidate)
    assert rapid.load_rapid_public_development_v6_candidate(REPOSITORY) == candidate
    receipt = rapid.load_rapid_public_development_v6_rehearsal(candidate, repository=REPOSITORY)
    assert rehearsal_path.stat().st_size == 3_069
    assert sha256_bytes(rehearsal_path.read_bytes()) == (
        "sha256:9fde502220f18f4d6b95b946dc1e22f27582020b27d48f81935d338284a16b60"
    )
    assert rehearsal_path.read_bytes() == rapid.rehearsal_bytes(receipt)
    assert receipt["provider_calls_made"] == receipt["docker_calls_made"] == 0
    assert receipt["task_calls_made"] == receipt["evaluator_calls_made"] == 0
    assert receipt["content_hash"] == (
        "sha256:a452d69827fdeb29df35c810bf6fa159c530d04a38f361cc94e05d0a2ad0f5bc"
    )
    assert candidate["execution_hash"] == (
        "sha256:8676d960ad92a632f8c61f56f9a2056506b12675877b4eb26ca373552cbe5456"
    )
    result_path = rapid._result_bundle_path(candidate, REPOSITORY)
    assert result_path.stat().st_size == 9_546
    assert sha256_bytes(result_path.read_bytes()) == (
        "sha256:09da402f811abfbf5c161ec8e6174854077b4ed23440c65bb015a5ecd3d2cbcb"
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
    assert [row["token_terminal"] for row in rows] == [
        True,
        False,
        False,
        True,
        True,
        False,
    ]
    summary = events[-1]
    assert summary["content_hash"] == (
        "sha256:33f2820f2b33549b4e0938dd2be91c5a8e4be0842bb60a642396441f1b2fbaac"
    )
    assert summary["model_cost_nanos"] == 5_229_653_850
    assert summary["evaluator_reached"] == 0
    assert summary["submissions_completed"] == 0
    assert summary["successes_at_budget"] == 0


def test_consumed_live_entry_rejects_before_rehearsal_or_docker(
    candidate: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        rapid,
        "load_rapid_public_development_v6_rehearsal",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("consumed execution must stop before rehearsal")
        ),
    )
    monkeypatch.setattr(
        rapid.DockerSandbox,
        "available",
        staticmethod(
            lambda: (_ for _ in ()).throw(
                AssertionError("consumed execution must stop before Docker")
            )
        ),
    )
    with pytest.raises(ContractError, match="consumed and cannot be retried"):
        rapid.run_rapid_public_development_v6(
            approve_live_cost=True,
            approved_execution_hash=candidate["execution_hash"],
            repository=REPOSITORY,
        )


def test_public_trace_diagnosis_binds_result_and_evidence_limits() -> None:
    diagnosis = json.loads(TRACE_DIAGNOSIS.read_text(encoding="utf-8"))
    assert TRACE_DIAGNOSIS.stat().st_size == 6_757
    assert sha256_bytes(TRACE_DIAGNOSIS.read_bytes()) == (
        "sha256:7a6f1ae99f1f245e8bf3cfad90f45c908262f3e9b40e14ae89a22641b5388974"
    )
    assert diagnosis["official"] is False
    assert diagnosis["source_bundle"] == {
        "bytes": 9_546,
        "file_sha256": ("sha256:09da402f811abfbf5c161ec8e6174854077b4ed23440c65bb015a5ecd3d2cbcb"),
        "execution_hash": rapid.CONSUMED_EXECUTION_HASH,
        "path": (
            "reports/rapid-development/"
            "rapid-public-dev-anyio-finalization-20260822-r5-8676d960ad92.jsonl"
        ),
        "terminal_content_hash": (
            "sha256:33f2820f2b33549b4e0938dd2be91c5a8e4be0842bb60a642396441f1b2fbaac"
        ),
    }
    assert diagnosis["batch_outcome"]["model_cost_usd"] == "5.22965385"
    assert diagnosis["batch_outcome"]["evaluator_reached"] == 0
    assert diagnosis["batch_outcome"]["submissions_completed"] == 0
    assert diagnosis["validation_evidence"] == {
        "rows_passing_targeted_and_upstream_on_a_submission_ready_state": 0,
        "targeted_check_invocations": 25,
        "targeted_check_passes": 1,
        "upstream_regression_invocations": 14,
        "upstream_regression_passes": 6,
        "tool_succeeded_is_not_check_pass": True,
        "interpretation": (
            "Every run_check invocation completed as a tool call, but its separate "
            "passed field shows that no row satisfied both registered checks before "
            "terminal failure."
        ),
    }
    boundary = diagnosis["evidence_boundary"]
    assert boundary["analysis_provider_calls"] == 0
    assert boundary["analysis_docker_calls"] == 0
    assert boundary["analysis_added_cost_usd"] == "0"
    assert boundary["reasoning_text_read"] is False
    assert boundary["private_evaluator_artifacts_read"] is False
    assert boundary["hidden_assertions_read"] is False
    assert diagnosis["successor_disposition"]["paid_execution_authorized"] is False


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

    monkeypatch.setattr(rapid_script, "run_rapid_public_development_v6", fake_run)
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
