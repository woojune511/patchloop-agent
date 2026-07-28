from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest

from patchloop.agent.model import ModelTurn, ModelTurnError
from patchloop.agent.runner import AgentRunner, issue_live_execution_authorization
from patchloop.contracts import (
    EventType,
    ExperimentPurpose,
    ExperimentRunContext,
    FaultSpec,
    Phase,
    RunOutcomeKind,
)
from patchloop.errors import ContractError, RecoveryError
from patchloop.evals.faults import clone_with_fault
from patchloop.runtime import build_manifest
from patchloop.sandbox import LocalSandbox
from patchloop.task_loader import load_task_package
from patchloop.util import sha256_bytes, utc_now

TASK = "tasks/smoke/csv-quoted-newline/public.yaml"
SMOKE_TASKS = {
    "csv-quoted-newline": TASK,
    "config-falsy-override": "tasks/smoke/config-falsy-override/public.yaml",
    "path-prefix-boundary": "tasks/smoke/path-prefix-boundary/public.yaml",
}
SMOKE_REPLAYS = {
    task_id: f"replays/smoke/{task_id}.jsonl" for task_id in SMOKE_TASKS
}


def _write_approved_execution_plan(root: Path, execution_hash: str) -> None:
    path = (
        root
        / "experiments"
        / "plans"
        / f"{execution_hash.removeprefix('sha256:')}.json"
    )
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": "experiment-execution-plan-v1",
                "ready": True,
                "blockers": [],
                "execution_hash": execution_hash,
                "approval": {
                    "invocation_approve_live_cost": True,
                    "invocation_approved_execution_hash": execution_hash,
                    "matches_execution_hash": True,
                },
            }
        ),
        encoding="utf-8",
    )


def _assert_public_trace_boundary(runner: AgentRunner, run_id: str, task_path: str) -> None:
    package = load_task_package(Path(task_path).parent)
    hidden_check_ids = {check.id for check in package.private.hidden_checks}
    contexts: list[str] = []
    for event in runner.state.list_events(run_id):
        if event.type != EventType.CONTEXT_BUILT:
            continue
        context = Path(event.payload["artifact_path"]).read_text(encoding="utf-8")
        contexts.append(context)
        assert "reference.patch" not in context
        assert all(check_id not in context for check_id in hidden_check_ids)
    assert contexts
    assert package.private.reference_patch.sha256 not in contexts[0]


@pytest.mark.parametrize(("task_id", "task_path"), SMOKE_TASKS.items())
def test_offline_mock_agent_creates_complete_trace(
    tmp_path, monkeypatch, task_id: str, task_path: str
) -> None:
    monkeypatch.setattr("patchloop.agent.runner.DockerSandbox.available", lambda: False)
    runner = AgentRunner(tmp_path / "runtime")
    result = runner.start(task_path, model="mock")
    events = runner.state.list_events(result["run_id"])
    assert result["scope_compliant_success"] is True
    assert result["official"] is False
    assert runner.state.get_manifest(result["run_id"]).task_id == task_id
    assert [event.sequence for event in events] == list(range(1, len(events) + 1))
    assert sum(event.type == EventType.MODEL_CALLED for event in events) == 5
    assert sum(event.type == EventType.TOOL_CALLED for event in events) == 4
    assert any(event.type == EventType.PATCH_APPLIED for event in events)
    assert any(event.type == EventType.RUN_COMPLETED for event in events)
    workspace = tmp_path / "runtime" / "workspaces" / result["run_id"] / "repo"
    assert not (workspace / ".patchloop-hidden").exists()
    result_path = (
        tmp_path
        / "runtime"
        / "artifacts"
        / "runs"
        / result["run_id"]
        / "result.json"
    )
    persisted = json.loads(result_path.read_text(encoding="utf-8"))
    assert persisted["usage"] == result["usage"]
    _assert_public_trace_boundary(runner, result["run_id"], task_path)


@pytest.mark.parametrize(
    ("task_id", "task_path", "replay_path"),
    [
        (task_id, task_path, SMOKE_REPLAYS[task_id])
        for task_id, task_path in SMOKE_TASKS.items()
    ],
)
def test_offline_replay_agent_creates_hashed_complete_trace(
    tmp_path,
    monkeypatch,
    task_id: str,
    task_path: str,
    replay_path: str,
) -> None:
    monkeypatch.setattr("patchloop.agent.runner.DockerSandbox.available", lambda: False)
    runner = AgentRunner(tmp_path / "runtime")
    result = runner.start(task_path, model=f"replay:{replay_path}")
    manifest = runner.state.get_manifest(result["run_id"])
    events = runner.state.list_events(result["run_id"])

    assert result["scope_compliant_success"] is True
    assert result["official"] is False
    assert manifest.task_id == task_id
    assert manifest.model.provider == "replay"
    assert manifest.model.model_id == f"replay:{replay_path}"
    assert manifest.model.replay_hash == sha256_bytes(Path(replay_path).read_bytes())
    assert sum(event.type == EventType.MODEL_CALLED for event in events) == 5
    assert sum(event.type == EventType.TOOL_CALLED for event in events) == 4
    _assert_public_trace_boundary(runner, result["run_id"], task_path)


def test_replay_path_must_be_repository_relative(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("patchloop.agent.runner.DockerSandbox.available", lambda: False)
    runner = AgentRunner(tmp_path / "runtime")
    with pytest.raises(ContractError, match="safe relative path"):
        runner.start(TASK, model="replay:../outside.jsonl")


def test_agent_failure_persists_run_id_usage_cost_and_terminal_artifacts(
    tmp_path,
    monkeypatch,
) -> None:
    class InvalidTurnAdapter:
        def next_turn(self, context, tools):
            del context, tools
            return ModelTurn(
                text="not done and no tool",
                input_tokens=1_000,
                cached_input_tokens=200,
                cache_write_input_tokens=100,
                output_tokens=100,
                response_id="resp_failure",
                response_model="gpt-5.6-terra",
                response_service_tier="default",
            )

    monkeypatch.setattr("patchloop.agent.runner.DockerSandbox.available", lambda: False)
    package = load_task_package(Path(TASK).parent)
    execution_hash = "sha256:" + ("e" * 64)
    manifest = build_manifest(
        package,
        run_id="run_live_agent_failure",
        provider="openai",
        model_id="gpt-5.6-terra",
        input_price_per_million_usd=2.5,
        cached_input_price_per_million_usd=0.25,
        cache_write_input_price_per_million_usd=3.125,
        output_price_per_million_usd=15.0,
        experiment_context=ExperimentRunContext(
            experiment_id="live-attempt-persistence-test",
            purpose=ExperimentPurpose.DEVELOPMENT_VALIDATION_LIVE_PILOT,
            suite_hash="sha256:" + ("a" * 64),
            execution_hash=execution_hash,
            schedule_seed=20260723,
            schedule_order=1,
            schedule_row_id="sha256:" + ("b" * 64),
            repetition=1,
        ),
    )
    runner = AgentRunner(tmp_path / "runtime")
    monkeypatch.setattr(runner, "_model_adapter", lambda *_: InvalidTurnAdapter())
    _write_approved_execution_plan(tmp_path / "runtime", execution_hash)

    result = runner.start(
        TASK,
        model="openai",
        manifest=manifest,
        live_authorization=issue_live_execution_authorization(
            execution_hash,
            root=tmp_path / "runtime",
        ),
    )

    assert result["run_id"] == manifest.run_id
    assert result["outcome_kind"] == RunOutcomeKind.AGENT_FAILURE.value
    assert result["evaluation_status"] == "not_run"
    assert result["usage"]["input_tokens"] == 1_000
    assert result["usage"]["cached_input_tokens"] == 200
    assert result["usage"]["cache_write_input_tokens"] == 100
    assert result["usage"]["model_cost_usd"] == pytest.approx(0.0036125)
    events = runner.state.list_events(manifest.run_id)
    assert events[-1].type == EventType.RUN_FAILED
    assert sum(event.type == EventType.RUN_FAILED for event in events) == 1
    result_path = (
        tmp_path
        / "runtime"
        / "artifacts"
        / "runs"
        / manifest.run_id
        / "result.json"
    )
    assert json.loads(result_path.read_text(encoding="utf-8"))["run_id"] == manifest.run_id


def test_agent_runner_rejects_live_model_without_campaign_capability(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr("patchloop.agent.runner.DockerSandbox.available", lambda: False)
    package = load_task_package(Path(TASK).parent)
    manifest = build_manifest(
        package,
        run_id="run_unapproved_live",
        provider="openai",
        model_id="gpt-5.6-terra",
    )
    runner = AgentRunner(tmp_path / "runtime")

    with pytest.raises(ContractError, match="approved experiment execution capability"):
        runner.start(TASK, model="openai", manifest=manifest)

    assert runner.state.has_run(manifest.run_id) is False


def test_live_capability_requires_persisted_approved_plan(tmp_path) -> None:
    with pytest.raises(ContractError, match="persisted approved execution plan"):
        issue_live_execution_authorization(
            "sha256:" + ("a" * 64),
            root=tmp_path / "runtime",
        )


def test_live_capability_rejects_execution_plan_drift(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr("patchloop.agent.runner.DockerSandbox.available", lambda: False)
    root = tmp_path / "runtime"
    execution_hash = "sha256:" + ("c" * 64)
    _write_approved_execution_plan(root, execution_hash)
    authorization = issue_live_execution_authorization(execution_hash, root=root)
    Path(authorization.plan_path).write_text(
        Path(authorization.plan_path).read_text(encoding="utf-8") + "\n",
        encoding="utf-8",
    )
    package = load_task_package(Path(TASK).parent)
    manifest = build_manifest(
        package,
        run_id="run_live_plan_drift",
        provider="openai",
        model_id="gpt-5.6-terra",
        experiment_context=ExperimentRunContext(
            experiment_id="live-plan-drift-test",
            purpose=ExperimentPurpose.DEVELOPMENT_VALIDATION_LIVE_PILOT,
            suite_hash="sha256:" + ("a" * 64),
            execution_hash=execution_hash,
            schedule_seed=20260723,
            schedule_order=1,
            schedule_row_id="sha256:" + ("b" * 64),
            repetition=1,
        ),
    )
    runner = AgentRunner(root)

    with pytest.raises(ContractError, match="approved experiment execution capability"):
        runner.start(
            TASK,
            model="openai",
            manifest=manifest,
            live_authorization=authorization,
        )

    assert runner.state.has_run(manifest.run_id) is False


def test_agent_runner_rejects_model_selector_manifest_mismatch(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr("patchloop.agent.runner.DockerSandbox.available", lambda: False)
    package = load_task_package(Path(TASK).parent)
    manifest = build_manifest(
        package,
        run_id="run_model_binding_mismatch",
        provider="mock",
        model_id="mock-v1",
    )
    runner = AgentRunner(tmp_path / "runtime")

    with pytest.raises(ContractError, match="does not match"):
        runner.start(TASK, model="openai", manifest=manifest)

    assert runner.state.has_run(manifest.run_id) is False


def test_agent_runner_rejects_task_package_manifest_mismatch(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr("patchloop.agent.runner.DockerSandbox.available", lambda: False)
    package = load_task_package(Path(TASK).parent)
    manifest = build_manifest(
        package,
        run_id="run_task_binding_mismatch",
        provider="mock",
        model_id="mock-v1",
    ).model_copy(update={"public_spec_hash": "sha256:" + ("f" * 64)})
    runner = AgentRunner(tmp_path / "runtime")

    with pytest.raises(ContractError, match="immutable run manifest"):
        runner.start(TASK, model="mock", manifest=manifest)

    assert runner.state.has_run(manifest.run_id) is False


def test_agent_runner_uses_one_validated_task_snapshot_before_model_turn(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr("patchloop.agent.runner.DockerSandbox.available", lambda: False)
    original_package = load_task_package(Path(TASK).parent)
    replacement = original_package.model_copy(
        update={"private_spec_hash": "sha256:" + ("f" * 64)}
    )
    loads = []

    def changing_loader(_task_dir):
        loads.append(len(loads) + 1)
        return original_package if len(loads) == 1 else replacement

    class StopAtModelTurn:
        @staticmethod
        def next_turn(_context, _tools):
            assert loads == [1]
            raise SystemExit("stop at model boundary")

    manifest = build_manifest(
        original_package,
        run_id="run_task_snapshot_probe",
        provider="mock",
        model_id="mock-v1",
    )
    runner = AgentRunner(tmp_path / "runtime")
    monkeypatch.setattr("patchloop.agent.runner.load_task_package", changing_loader)
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: StopAtModelTurn())

    with pytest.raises(SystemExit, match="stop at model boundary"):
        runner.start(TASK, model="mock", manifest=manifest)

    assert loads == [1]


def test_startup_failure_persists_terminal_infrastructure_attempt(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr("patchloop.agent.runner.DockerSandbox.available", lambda: False)
    package = load_task_package(Path(TASK).parent)
    manifest = build_manifest(
        package,
        run_id="run_startup_infrastructure_failure",
        provider="mock",
        model_id="mock-v1",
    )
    runner = AgentRunner(tmp_path / "runtime")

    def fail_workspace(*_args, **_kwargs):
        raise OSError("synthetic workspace failure")

    monkeypatch.setattr(runner.workspaces, "create", fail_workspace)
    with pytest.raises(OSError, match="synthetic workspace failure"):
        runner.start(TASK, model="mock", manifest=manifest)

    row = next(
        row for row in runner.state.list_runs() if row["run_id"] == manifest.run_id
    )
    assert row["status"] == "failed"
    assert row["result"]["outcome_kind"] == "infrastructure_error"
    assert runner.state.list_events(manifest.run_id)[-1].type == EventType.RUN_FAILED
    assert (
        tmp_path
        / "runtime"
        / "artifacts"
        / "runs"
        / manifest.run_id
        / "result.json"
    ).is_file()


def test_billed_model_parse_error_preserves_usage_and_cost(
    tmp_path,
    monkeypatch,
) -> None:
    class BilledMalformedTurnAdapter:
        @staticmethod
        def next_turn(_context, _tools):
            return ModelTurn(
                input_tokens=1_000,
                cached_input_tokens=200,
                cache_write_input_tokens=100,
                output_tokens=100,
                response_id="resp_malformed",
                error=ModelTurnError(
                    code="invalid_tool_arguments_json",
                    message="provider function-call arguments were not valid JSON",
                ),
            )

    monkeypatch.setattr("patchloop.agent.runner.DockerSandbox.available", lambda: False)
    package = load_task_package(Path(TASK).parent)
    manifest = build_manifest(
        package,
        run_id="run_billed_parse_error",
        provider="mock",
        model_id="mock-v1",
        input_price_per_million_usd=2.5,
        cached_input_price_per_million_usd=0.25,
        cache_write_input_price_per_million_usd=3.125,
        output_price_per_million_usd=15.0,
    )
    runner = AgentRunner(tmp_path / "runtime")
    monkeypatch.setattr(
        runner,
        "_model_adapter",
        lambda *_args: BilledMalformedTurnAdapter(),
    )

    result = runner.start(TASK, model="mock", manifest=manifest)

    assert result["outcome_kind"] == "agent_failure"
    assert result["terminal_error"]["message"].endswith(
        "invalid_tool_arguments_json"
    )
    assert result["usage"]["input_tokens"] == 1_000
    assert result["usage"]["model_cost_usd"] == pytest.approx(0.0036125)
    model_event = next(
        event
        for event in runner.state.list_events(manifest.run_id)
        if event.type == EventType.MODEL_CALLED
    )
    assert model_event.payload["response_error_code"] == (
        "invalid_tool_arguments_json"
    )


def test_fault_clone_preserves_replay_adapter_identity(monkeypatch) -> None:
    package = load_task_package(Path(TASK).parent)
    replay_model = f"replay:{SMOKE_REPLAYS['csv-quoted-newline']}"
    baseline = build_manifest(
        package,
        run_id="run_replay_fault_baseline",
        provider="replay",
        model_id=replay_model,
        replay_hash=sha256_bytes(
            Path(SMOKE_REPLAYS["csv-quoted-newline"]).read_bytes()
        ),
    )
    captured = {}

    class FakeRunner:
        state = type(
            "FakeState",
            (),
            {"get_manifest": staticmethod(lambda _run_id: baseline)},
        )()

        @staticmethod
        def _find_task(_manifest):
            return Path(TASK).parent

        @staticmethod
        def start(_task, *, model, manifest, **_kwargs):
            captured["model"] = model
            captured["manifest"] = manifest
            return {"status": "suspended"}

    monkeypatch.setattr("patchloop.evals.faults.AgentRunner", FakeRunner)

    clone_with_fault(baseline.run_id, "worker-restart")

    assert captured["model"] == replay_model
    assert captured["manifest"].model.provider == "replay"


def test_worker_restart_resumes_without_duplicate_patch(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("patchloop.agent.runner.DockerSandbox.available", lambda: False)
    package = load_task_package("tasks/smoke/csv-quoted-newline")
    manifest = build_manifest(
        package,
        run_id="run_recovery_test",
        sandbox_backend="local",
        fault=FaultSpec(type="worker-kill-after-patch"),
    )
    runner = AgentRunner(tmp_path / "runtime")
    suspended = runner.start(TASK, model="mock", manifest=manifest)
    assert suspended["status"] == "suspended"
    resumed = runner.resume(manifest.run_id)
    events = runner.state.list_events(manifest.run_id)
    assert resumed["scope_compliant_success"] is True
    assert sum(event.type == EventType.PATCH_APPLIED for event in events) == 1


def test_replay_worker_restart_preserves_source_identity(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("patchloop.agent.runner.DockerSandbox.available", lambda: False)
    replay_path = SMOKE_REPLAYS["config-falsy-override"]
    replay_hash = sha256_bytes(Path(replay_path).read_bytes())
    package = load_task_package("tasks/smoke/config-falsy-override")
    manifest = build_manifest(
        package,
        run_id="run_replay_recovery",
        provider="replay",
        model_id=f"replay:{replay_path}",
        replay_hash=replay_hash,
        sandbox_backend="local",
        fault=FaultSpec(type="worker-kill-after-patch"),
    )
    runner = AgentRunner(tmp_path / "runtime")
    suspended = runner.start(
        SMOKE_TASKS["config-falsy-override"],
        model=f"replay:{replay_path}",
        manifest=manifest,
    )
    assert suspended["status"] == "suspended"

    resumed = runner.resume(manifest.run_id)
    events = runner.state.list_events(manifest.run_id)
    assert resumed["scope_compliant_success"] is True
    assert runner.state.get_manifest(manifest.run_id).model.replay_hash == replay_hash
    assert sum(event.type == EventType.PATCH_APPLIED for event in events) == 1


def test_resume_rejects_checkpoint_worktree_mismatch(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("patchloop.agent.runner.DockerSandbox.available", lambda: False)
    package = load_task_package("tasks/smoke/csv-quoted-newline")
    manifest = build_manifest(
        package,
        run_id="run_corrupt_checkpoint",
        sandbox_backend="local",
        fault=FaultSpec(type="worker-kill-after-patch"),
    )
    runner = AgentRunner(tmp_path / "runtime")
    runner.start(TASK, model="mock", manifest=manifest)
    checkpoint = runner.state.latest_checkpoint(manifest.run_id)
    assert checkpoint is not None
    corrupt = checkpoint.model_copy(
        update={
            "checkpoint_id": f"ckpt_{uuid.uuid4().hex}",
            "through_sequence": runner.state.last_sequence(manifest.run_id),
            "worktree_diff_hash": "sha256:corrupt",
            "created_at": utc_now(),
        }
    )
    runner.state.save_checkpoint(corrupt)
    with pytest.raises(RecoveryError, match="diff hash"):
        runner.resume(manifest.run_id)


def test_resume_rejects_untracked_workspace_state(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("patchloop.agent.runner.DockerSandbox.available", lambda: False)
    package = load_task_package("tasks/smoke/csv-quoted-newline")
    manifest = build_manifest(
        package,
        run_id="run_untracked_recovery",
        sandbox_backend="local",
        fault=FaultSpec(type="worker-kill-after-patch"),
    )
    runner = AgentRunner(tmp_path / "runtime")
    suspended = runner.start(TASK, model="mock", manifest=manifest)
    assert suspended["status"] == "suspended"
    workspace = runner.root / "workspaces" / manifest.run_id / "repo"
    (workspace / "untracked-agent-state.txt").write_text(
        "must not survive recovery",
        encoding="utf-8",
    )

    with pytest.raises(RecoveryError, match="untracked files during recovery"):
        runner.resume(manifest.run_id)


def test_checkpoint_rejects_untracked_workspace_state(tmp_path) -> None:
    package = load_task_package("tasks/smoke/csv-quoted-newline")
    manifest = build_manifest(
        package,
        run_id="run_untracked_checkpoint",
        sandbox_backend="local",
    )
    runner = AgentRunner(tmp_path / "runtime")
    runner.state.create_run(manifest)
    workspace = runner.workspaces.create(
        manifest.run_id,
        package.public.repository.url,
        package.public.repository.base_commit,
    )
    (workspace / "untracked-agent-state.txt").write_text(
        "must not enter a checkpoint",
        encoding="utf-8",
    )

    with pytest.raises(RecoveryError, match="untracked files at checkpoint"):
        runner._checkpoint(manifest, workspace, Phase.INTAKE)


def test_run_check_untracked_output_fails_as_infrastructure_error(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr("patchloop.agent.runner.DockerSandbox.available", lambda: False)
    real_run_check = LocalSandbox.run_check

    def run_check_and_leave_untracked(self, workspace, check):
        result = real_run_check(self, workspace, check)
        (workspace / "untracked-check-output.txt").write_text(
            "must not enter a checkpoint",
            encoding="utf-8",
        )
        return result

    monkeypatch.setattr(LocalSandbox, "run_check", run_check_and_leave_untracked)
    runner = AgentRunner(tmp_path / "runtime")

    result = runner.start(TASK, model="mock")

    assert result["outcome_kind"] == RunOutcomeKind.INFRASTRUCTURE_ERROR.value
    assert result["terminal_error"]["type"] == "RecoveryError"
    assert "untracked files at checkpoint" in result["terminal_error"]["message"]
    assert result["evaluation_status"] == "not_run"


def test_timeout_fault_is_recorded_without_repeating_command(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("patchloop.agent.runner.DockerSandbox.available", lambda: False)
    package = load_task_package("tasks/smoke/csv-quoted-newline")
    manifest = build_manifest(
        package,
        run_id="run_timeout_fault",
        sandbox_backend="local",
        fault=FaultSpec(type="test-timeout"),
    )
    runner = AgentRunner(tmp_path / "runtime")
    result = runner.start(TASK, model="mock", manifest=manifest)
    assert result["outcome_kind"] == RunOutcomeKind.AGENT_FAILURE.value
    assert "visible check" in result["terminal_error"]["message"]
    events = runner.state.list_events(manifest.run_id)
    timed_out_checks = [
        event
        for event in events
        if event.type == EventType.TOOL_SUCCEEDED
        and event.payload.get("tool") == "run_check"
        and event.payload.get("timed_out") is True
    ]
    assert len(timed_out_checks) == 1
    assert sum(event.type == EventType.TOOL_CALLED for event in events) == 4
    assert events[-1].type == EventType.RUN_FAILED
