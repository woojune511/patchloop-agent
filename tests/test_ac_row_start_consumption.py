from __future__ import annotations

import copy
import json
import socket
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from patchloop import runtime as runtime_module
from patchloop.agent import runner as agent_runner
from patchloop.agent.runner import (
    AgentRunner,
    _ac_row_start_consumption_path,
    issue_live_execution_authorization,
)
from patchloop.contracts import (
    CONDITION_NEUTRAL_COMPARISON_ACCRUED_CAP_EXPERIMENT_ID,
    CONDITION_NEUTRAL_NO_MEMORY_V2_EXPERIMENT_ID,
    DatasetRole,
    ExperimentRunContext,
    MemoryCondition,
)
from patchloop.errors import ContractError, RecoveryError
from patchloop.evals import runner as eval_runner
from patchloop.runtime import build_manifest
from patchloop.state import StateStore
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json, sha256_bytes, sha256_text

R2_SUITE = Path("experiments/dev-validation-ac-fixed-bundle-readiness-20260813-fast-r1.yaml")
SOURCE_COMMIT = "a" * 40


def _forbidden(label: str):
    def fail(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError(f"{label} is forbidden in offline row-claim tests")

    return fail


def _row_identity(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: row[key]
        for key in (
            "order",
            "schedule_row_id",
            "task_id",
            "split",
            "dataset_role",
            "condition",
            "repetition",
        )
    }


@pytest.fixture
def ac_case(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, Any]:
    root = tmp_path / "runtime"
    monkeypatch.setenv("OPENAI_API_KEY", "offline-placeholder-not-used")
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_API_BASE", raising=False)
    monkeypatch.setattr(eval_runner, "runtime_root", lambda: root)
    monkeypatch.setattr(
        eval_runner,
        "utc_now",
        lambda: datetime(2026, 8, 13, 12, 5, 27, tzinfo=UTC),
    )
    monkeypatch.setattr(
        eval_runner,
        "_git_state",
        lambda: {"available": True, "commit": SOURCE_COMMIT, "clean": True},
    )
    monkeypatch.setattr(
        eval_runner,
        "_docker_image_state",
        lambda images: {
            "available": True,
            "images": [
                {
                    "image": image,
                    "identity": image.rsplit("@", 1)[-1],
                    "ready": True,
                }
                for image in sorted(set(images))
            ],
        },
    )
    monkeypatch.setattr(
        eval_runner,
        "_openai_sdk_state",
        lambda: {"installed": True, "version": "offline-test-sdk"},
    )
    monkeypatch.setattr(runtime_module, "git_commit", lambda: SOURCE_COMMIT)
    monkeypatch.setattr(
        runtime_module,
        "version",
        lambda _package: "offline-test-sdk",
    )
    monkeypatch.setattr(
        eval_runner,
        "_validated_ac_evaluator_v2_source_qualification",
        lambda _suite: {
            "source_qualification_hash": "sha256:" + "1" * 64,
            "evaluator_source_hash": "sha256:" + "2" * 64,
            "successor_suite_hash": "sha256:" + "3" * 64,
            "base_suite_hash": "sha256:" + "4" * 64,
            "base_suite_matches": True,
        },
    )
    monkeypatch.setattr(socket, "socket", _forbidden("network socket"))
    monkeypatch.setattr(
        socket,
        "create_connection",
        _forbidden("network connection"),
    )

    preflight = eval_runner.preflight_suite(R2_SUITE)
    plan = copy.deepcopy(preflight)
    plan["schema_version"] = "experiment-execution-plan-v1"
    plan["blockers"] = []
    plan["ready"] = True
    plan["approval"] = {
        **plan["approval"],
        "invocation_approve_live_cost": True,
        "invocation_approved_execution_hash": plan["execution_hash"],
        "matches_execution_hash": True,
    }
    plan_path = (
        root / "experiments" / "plans" / f"{plan['execution_hash'].removeprefix('sha256:')}.json"
    )
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(
        json.dumps(plan, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    authorization = issue_live_execution_authorization(
        plan["execution_hash"],
        root=root,
    )
    manifest, item = _manifest_for(plan, run_id="run_ac_row_claim_1")
    row_started_event_hash = _write_current_row_journal(plan, manifest)
    return {
        "root": root,
        "plan": plan,
        "authorization": authorization,
        "manifest": manifest,
        "item": item,
        "journal": Path(plan["journal_path"]),
        "row_started_event_hash": row_started_event_hash,
    }


def _manifest_for(
    plan: dict[str, Any],
    *,
    run_id: str,
) -> tuple[Any, dict[str, Any]]:
    suite = eval_runner.load_suite(R2_SUITE)
    schedule_row = plan["schedule"][0]
    task_row = next(row for row in plan["tasks"] if row["task_id"] == schedule_row["task_id"])
    item = {**task_row, **schedule_row}
    task_path = Path(item["task"])
    package = load_task_package(task_path.parent if task_path.is_file() else task_path)
    experiment = ExperimentRunContext(
        experiment_id=suite.experiment_id,
        purpose=suite.purpose,
        suite_hash=plan["suite_hash"],
        execution_hash=plan["execution_hash"],
        dataset_manifest_hash=plan["dataset"]["manifest_hash"],
        dataset_role=DatasetRole(item["dataset_role"]),
        schedule_seed=suite.seed,
        schedule_order=item["order"],
        schedule_row_id=item["schedule_row_id"],
        repetition=item["repetition"],
        campaign_cost_control_hash=plan["campaign_cost_control"]["content_hash"],
    )
    manifest = build_manifest(
        package,
        run_id=run_id,
        provider=suite.model,
        model_id=suite.model_id,
        memory_condition=MemoryCondition(item["condition"]),
        memory_policy_version=suite.memory_policy_version or "v1",
        sandbox_backend="docker",
        budget=suite.budget,
        agent_image_digest=item["evaluator_image_digest"],
        evaluator_image_digest=item["evaluator_image_digest"],
        input_price_per_million_usd=suite.input_price_per_million_usd,
        cached_input_price_per_million_usd=(suite.cached_input_price_per_million_usd),
        cache_write_input_price_per_million_usd=(suite.cache_write_input_price_per_million_usd),
        output_price_per_million_usd=suite.output_price_per_million_usd,
        reasoning_effort=suite.reasoning_effort,
        reasoning_mode=suite.reasoning_mode,
        service_tier=suite.service_tier,
        transport_max_retries=suite.transport_max_retries,
        max_output_tokens=suite.max_output_tokens,
        experiment_context=experiment,
    )
    return manifest, item


def _write_current_row_journal(
    plan: dict[str, Any],
    manifest: Any,
) -> str:
    assert manifest.experiment is not None
    journal = Path(plan["journal_path"])
    control = plan["campaign_cost_control"]
    descriptor = control["descriptor"]
    plan_content_hash = sha256_text(canonical_json(plan))
    row = plan["schedule"][0]
    previous = eval_runner._append_campaign_event(
        journal,
        sequence=1,
        previous_event_hash=None,
        event_type="CampaignStarted",
        payload={
            "experiment_id": plan["experiment_id"],
            "purpose": plan["purpose"],
            "execution_hash": plan["execution_hash"],
            "schedule_hash": plan["schedule_hash"],
            "execution_plan_hash": plan_content_hash,
            "campaign_cost_control_hash": control["content_hash"],
        },
    )
    previous = eval_runner._append_campaign_event(
        journal,
        sequence=2,
        previous_event_hash=previous,
        event_type="FullScheduleCostReserved",
        payload={
            "experiment_id": plan["experiment_id"],
            "execution_hash": plan["execution_hash"],
            "execution_plan_hash": plan_content_hash,
            "campaign_cost_control_hash": control["content_hash"],
            "schedule_hash": plan["schedule_hash"],
            "schedule_row_ids": descriptor["schedule_row_ids"],
            "per_run_reserve_nanos": descriptor["per_run_reserve_nanos"],
            "full_schedule_reserve_nanos": descriptor["full_schedule_reserve_nanos"],
            "hard_cap_nanos": descriptor["hard_cap_nanos"],
            "row_reserve_count": len(plan["schedule"]),
            "cost_censoring_allowed": False,
        },
    )
    return eval_runner._append_campaign_event(
        journal,
        sequence=3,
        previous_event_hash=previous,
        event_type="RunStarted",
        payload={
            **_row_identity(row),
            "run_id": manifest.run_id,
            "execution_hash": plan["execution_hash"],
            "execution_plan_hash": plan_content_hash,
            "campaign_cost_control_hash": control["content_hash"],
        },
    )


def _claim_values(case: dict[str, Any]) -> dict[str, str]:
    manifest = case["manifest"]
    assert manifest.experiment is not None
    return {
        "execution_hash": manifest.experiment.execution_hash,
        "schedule_row_id": manifest.experiment.schedule_row_id,
        "run_id": manifest.run_id,
        "row_started_event_hash": case["row_started_event_hash"],
        "journal_prefix_file_sha256": sha256_bytes(case["journal"].read_bytes()),
        "control_hash": manifest.experiment.campaign_cost_control_hash,
    }


def _configure_offline_runner(
    runner: AgentRunner,
    manifest: Any,
    workspace: Path,
    monkeypatch: pytest.MonkeyPatch,
    execute: Any,
) -> None:
    workspace.mkdir(parents=True, exist_ok=True)

    class FakeDockerSandbox:
        def image_identity(self) -> str | None:
            return manifest.evaluator_image_digest

        def probe_image_identity(self) -> None:
            return None

    monkeypatch.setattr(agent_runner.DockerSandbox, "available", lambda: True)
    # The checked-in R2 suite deliberately leaves live pricing freshness
    # unapproved.  These tests isolate the repository-local row-start boundary;
    # the full-schedule journal and authorization are still validated by the
    # production path below.
    monkeypatch.setattr(
        AgentRunner,
        "_live_plan_matches_manifest",
        staticmethod(lambda *_args, **_kwargs: True),
    )
    monkeypatch.setattr(
        agent_runner.OpenAIResponsesAdapter,
        "__init__",
        _forbidden("OpenAI adapter construction"),
    )
    monkeypatch.setattr(runner, "_docker_sandbox", lambda _package: FakeDockerSandbox())
    monkeypatch.setattr(
        runner.workspaces,
        "create",
        lambda *_args, **_kwargs: workspace,
    )
    monkeypatch.setattr(
        runner.workspaces,
        "validate_managed_workspace",
        lambda _workspace: workspace,
    )
    monkeypatch.setattr(
        runner.workspaces,
        "validate_pristine",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        runner,
        "_prepare_public_review_base_provenance",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(runner, "_execute", execute)


def test_ac_row_start_state_consumption_is_atomic(ac_case: dict[str, Any]) -> None:
    path = ac_case["root"] / "state.sqlite3"
    first = StateStore(path)
    second = StateStore(path)
    first.create_run(ac_case["manifest"])
    values = _claim_values(ac_case)

    def consume(store: StateStore) -> str:
        try:
            store.record_ac_row_start_consumption(**values)
        except ContractError:
            return "rejected"
        return "consumed"

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(consume, (first, second)))

    assert sorted(outcomes) == ["consumed", "rejected"]
    rows = first.list_ac_row_start_consumptions(values["execution_hash"])
    assert len(rows) == 1
    assert rows[0]["schedule_row_id"] == values["schedule_row_id"]
    assert rows[0]["run_id"] == values["run_id"]


@pytest.mark.parametrize("duplicate", ["row", "run", "event"])
def test_ac_row_start_state_rejects_replacement_identities(
    ac_case: dict[str, Any],
    duplicate: str,
) -> None:
    state = StateStore(ac_case["root"] / "state.sqlite3")
    original = ac_case["manifest"]
    replacement = original.model_copy(update={"run_id": "run_ac_row_claim_2"})
    state.create_run(original)
    state.create_run(replacement)
    values = _claim_values(ac_case)
    state.record_ac_row_start_consumption(**values)
    changed = {
        **values,
        "schedule_row_id": "sha256:" + "1" * 64,
        "run_id": replacement.run_id,
        "row_started_event_hash": "sha256:" + "2" * 64,
    }
    if duplicate == "row":
        changed["schedule_row_id"] = values["schedule_row_id"]
    elif duplicate == "run":
        changed["run_id"] = values["run_id"]
    else:
        changed["row_started_event_hash"] = values["row_started_event_hash"]

    with pytest.raises(ContractError, match="already consumed"):
        state.record_ac_row_start_consumption(**changed)


def test_ac_row_start_state_rejects_hash_tamper(ac_case: dict[str, Any]) -> None:
    state = StateStore(ac_case["root"] / "state.sqlite3")
    state.create_run(ac_case["manifest"])
    values = _claim_values(ac_case)
    state.record_ac_row_start_consumption(**values)
    with state._connect() as connection:
        connection.execute(
            "UPDATE ac_row_start_consumptions SET content_hash = ?",
            ("sha256:" + "f" * 64,),
        )

    with pytest.raises(RecoveryError, match="consumption state is invalid"):
        state.list_ac_row_start_consumptions(values["execution_hash"])


def test_ac_paid_boundary_consumes_claim_before_execute_without_calls(
    ac_case: dict[str, Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = AgentRunner(ac_case["root"])
    manifest = ac_case["manifest"]
    execute_calls: list[str] = []

    def execute(*_args: Any, **_kwargs: Any) -> dict[str, str]:
        claims = runner.state.list_ac_row_start_consumptions(manifest.experiment.execution_hash)
        marker_path = _ac_row_start_consumption_path(
            journal_path=ac_case["journal"],
            execution_hash=manifest.experiment.execution_hash,
            schedule_row_id=manifest.experiment.schedule_row_id,
        )
        assert len(claims) == 1
        assert claims[0]["run_id"] == manifest.run_id
        assert marker_path.is_file()
        execute_calls.append(manifest.run_id)
        return {"run_id": manifest.run_id}

    _configure_offline_runner(
        runner,
        manifest,
        tmp_path / "workspace",
        monkeypatch,
        execute,
    )
    result = runner.start(
        ac_case["item"]["task"],
        model="openai",
        manifest=manifest,
        live_authorization=ac_case["authorization"],
    )

    assert result == {"run_id": manifest.run_id}
    assert execute_calls == [manifest.run_id]


def test_ac_marker_write_failure_keeps_db_claim_and_blocks_execute(
    ac_case: dict[str, Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = AgentRunner(ac_case["root"])
    manifest = ac_case["manifest"]
    execute_calls: list[str] = []
    _configure_offline_runner(
        runner,
        manifest,
        tmp_path / "workspace",
        monkeypatch,
        lambda *_args, **_kwargs: execute_calls.append(manifest.run_id),
    )
    monkeypatch.setattr(
        agent_runner,
        "_write_ac_row_start_consumption_marker",
        _forbidden("row-start marker write"),
    )

    with pytest.raises(AssertionError, match="marker write"):
        runner.start(
            ac_case["item"]["task"],
            model="openai",
            manifest=manifest,
            live_authorization=ac_case["authorization"],
        )

    values = _claim_values(ac_case)
    claims = runner.state.list_ac_row_start_consumptions(values["execution_hash"])
    assert len(claims) == 1
    assert execute_calls == []
    with pytest.raises(ContractError, match="already consumed"):
        runner.state.record_ac_row_start_consumption(**values)


def test_ac_consumed_row_rejects_journal_reset_and_replacement_run(
    ac_case: dict[str, Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = AgentRunner(ac_case["root"])
    first_manifest = ac_case["manifest"]
    first_calls: list[str] = []
    _configure_offline_runner(
        first,
        first_manifest,
        tmp_path / "workspace-first",
        monkeypatch,
        lambda *_args, **_kwargs: (
            first_calls.append(first_manifest.run_id) or {"run_id": first_manifest.run_id}
        ),
    )
    first.start(
        ac_case["item"]["task"],
        model="openai",
        manifest=first_manifest,
        live_authorization=ac_case["authorization"],
    )
    marker_path = _ac_row_start_consumption_path(
        journal_path=ac_case["journal"],
        execution_hash=first_manifest.experiment.execution_hash,
        schedule_row_id=first_manifest.experiment.schedule_row_id,
    )
    marker_path.unlink()
    ac_case["journal"].unlink()

    replacement, item = _manifest_for(
        ac_case["plan"],
        run_id="run_ac_row_claim_replacement",
    )
    _write_current_row_journal(ac_case["plan"], replacement)
    second = AgentRunner(ac_case["root"])
    second_calls: list[str] = []
    _configure_offline_runner(
        second,
        replacement,
        tmp_path / "workspace-second",
        monkeypatch,
        lambda *_args, **_kwargs: second_calls.append(replacement.run_id),
    )

    with pytest.raises(ContractError, match="already consumed"):
        second.start(
            item["task"],
            model="openai",
            manifest=replacement,
            live_authorization=ac_case["authorization"],
        )

    assert first_calls == [first_manifest.run_id]
    assert second_calls == []


def test_ac_journal_change_after_initial_validation_stops_before_claim(
    ac_case: dict[str, Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = AgentRunner(ac_case["root"])
    manifest = ac_case["manifest"]
    execute_calls: list[str] = []
    _configure_offline_runner(
        runner,
        manifest,
        tmp_path / "workspace",
        monkeypatch,
        lambda *_args, **_kwargs: execute_calls.append(manifest.run_id),
    )
    original_claim = runner.state.claim_run_for_worker

    def claim_and_mutate(*args: Any, **kwargs: Any) -> dict[str, Any]:
        claim = original_claim(*args, **kwargs)
        raw_events = [
            json.loads(line) for line in ac_case["journal"].read_text(encoding="utf-8").splitlines()
        ]
        eval_runner._append_campaign_event(
            ac_case["journal"],
            sequence=len(raw_events) + 1,
            previous_event_hash=raw_events[-1]["event_hash"],
            event_type="UnexpectedEvent",
            payload={},
        )
        return claim

    monkeypatch.setattr(runner.state, "claim_run_for_worker", claim_and_mutate)

    with pytest.raises(ContractError, match="payload fields differ"):
        runner.start(
            ac_case["item"]["task"],
            model="openai",
            manifest=manifest,
            live_authorization=ac_case["authorization"],
        )

    assert runner.state.list_ac_row_start_consumptions(manifest.experiment.execution_hash) == []
    assert execute_calls == []


def test_ac_resume_is_blocked_before_task_lookup_or_start(
    ac_case: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = AgentRunner(ac_case["root"])
    runner.state.create_run(ac_case["manifest"])
    calls: list[str] = []

    def unexpected(*_args: Any, **_kwargs: Any) -> None:
        calls.append("called")
        raise AssertionError("resume crossed the A/C no-resume boundary")

    monkeypatch.setattr(runner, "_find_task", unexpected)
    monkeypatch.setattr(runner, "start", unexpected)
    with pytest.raises(ContractError, match="full-schedule live resume is disabled"):
        runner.resume(ac_case["manifest"].run_id)
    assert calls == []


@pytest.mark.parametrize(
    "historical_experiment_id",
    [
        CONDITION_NEUTRAL_COMPARISON_ACCRUED_CAP_EXPERIMENT_ID,
        CONDITION_NEUTRAL_NO_MEMORY_V2_EXPERIMENT_ID,
    ],
)
def test_ac_row_claim_does_not_apply_to_d087_or_d097(
    ac_case: dict[str, Any],
    historical_experiment_id: str,
) -> None:
    manifest = ac_case["manifest"]
    assert manifest.experiment is not None
    historical = manifest.model_copy(
        update={
            "experiment": manifest.experiment.model_copy(
                update={"experiment_id": historical_experiment_id}
            )
        }
    )
    runner = AgentRunner(ac_case["root"])

    assert runner._consume_ac_row_start_once(historical, None) is None
    assert runner.state.list_ac_row_start_consumptions(manifest.experiment.execution_hash) == []
