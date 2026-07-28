from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml
from pydantic import ValidationError
from typer.testing import CliRunner

from patchloop.cli import app
from patchloop.contracts import DatasetRole, ExperimentPurpose
from patchloop.dataset import load_dataset_manifest
from patchloop.errors import ContractError
from patchloop.evals import runner as eval_runner
from patchloop.evals.runner import ExperimentSuite
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json, sha256_text


def _core_suite_payload(dataset_manifest_hash: str) -> dict:
    return {
        "schema_version": "experiment-v1",
        "experiment_id": "core-role-test",
        "core": True,
        "tasks": [f"task-{index}" for index in range(12)],
        "conditions": [
            "no_memory",
            "raw_trace",
            "structured",
            "selective_structured",
        ],
        "repetitions": 2,
        "model": "mock",
        "embedding_revision": "test-revision",
        "dataset_manifest_hash": dataset_manifest_hash,
    }


def _ready_live_environment(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-secret-never-rendered")
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_API_BASE", raising=False)
    monkeypatch.setattr(
        eval_runner,
        "_git_state",
        lambda: {"available": True, "commit": "a" * 40, "clean": True},
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
        lambda: {"installed": True, "version": "2.47.0"},
    )
    monkeypatch.setattr(
        eval_runner,
        "utc_now",
        lambda: datetime(2026, 7, 28, 12, tzinfo=UTC),
    )
    monkeypatch.setattr(eval_runner, "runtime_root", lambda: tmp_path / "runtime")


def test_live_campaign_approval_is_an_invocation_preflight_gate(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _ready_live_environment(monkeypatch, tmp_path)
    suite = eval_runner.load_suite("experiments/dev-validation-pilot.template.yaml")
    assert suite.purpose == ExperimentPurpose.DEVELOPMENT_VALIDATION_LIVE_PILOT

    unapproved = eval_runner.preflight_suite(
        "experiments/dev-validation-pilot.template.yaml"
    )
    blocker_codes = {row["code"] for row in unapproved["blockers"]}
    assert blocker_codes == {"LIVE_COST_NOT_APPROVED", "APPROVAL_HASH_MISMATCH"}
    assert "test-secret-never-rendered" not in json.dumps(unapproved)

    approved = eval_runner.preflight_suite(
        "experiments/dev-validation-pilot.template.yaml",
        approve_live_cost=True,
        approved_execution_hash=unapproved["execution_hash"],
    )
    assert approved["ready"] is True
    assert approved["execution_hash"] == unapproved["execution_hash"]


def test_v2_development_campaign_has_exact_twelve_run_matrix(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _ready_live_environment(monkeypatch, tmp_path)
    preflight = eval_runner.preflight_suite("experiments/dev-no-memory.template.yaml")

    assert preflight["purpose"] == "memory-development-no-memory"
    assert preflight["expected_runs"] == 12
    assert len({row["schedule_row_id"] for row in preflight["schedule"]}) == 12
    assert {row["dataset_role"] for row in preflight["tasks"]} == {
        "memory-development"
    }
    assert {row["condition"] for row in preflight["schedule"]} == {"no_memory"}
    assert {row["repetition"] for row in preflight["schedule"]} == {1, 2}
    assert {
        row["code"] for row in preflight["blockers"]
    } == {
        "LIVE_COST_NOT_APPROVED",
        "APPROVAL_HASH_MISMATCH",
        "QUALIFIED_PILOT_REQUIRED",
    }


def test_v2_development_campaign_rejects_an_incomplete_task_set() -> None:
    payload = yaml.safe_load(
        Path("experiments/dev-no-memory.template.yaml").read_text(encoding="utf-8")
    )
    payload["tasks"] = payload["tasks"][:-1]

    with pytest.raises(ValidationError, match="six frozen development tasks"):
        ExperimentSuite.model_validate(payload)


@pytest.mark.parametrize("mutation", ["path", "private", "environment"])
def test_live_preflight_binds_canonical_private_evaluator_package(
    tmp_path: Path,
    monkeypatch,
    mutation: str,
) -> None:
    _ready_live_environment(monkeypatch, tmp_path)
    original_loader = eval_runner.load_task_package
    package = original_loader(Path(eval_runner.PILOT_TASK).parent)
    if mutation == "path":
        forged = package.model_copy(update={"root": str(tmp_path / "forged-task")})
    elif mutation == "private":
        forged = package.model_copy(
            update={"private_spec_hash": "sha256:" + ("f" * 64)}
        )
    else:
        forged = package.model_copy(update={"environment": None})
    monkeypatch.setattr(eval_runner, "load_task_package", lambda _path: forged)

    preflight = eval_runner.preflight_suite(
        "experiments/dev-validation-pilot.template.yaml"
    )

    blockers = {row["code"] for row in preflight["blockers"]}
    assert "TASK_NOT_ELIGIBLE" in blockers
    assert preflight["tasks"] == []


def test_blocked_preflight_happens_before_agent_construction(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _ready_live_environment(monkeypatch, tmp_path)

    class ForbiddenRunner:
        def __init__(self):
            pytest.fail("AgentRunner must not be constructed before live approval")

    monkeypatch.setattr(eval_runner, "AgentRunner", ForbiddenRunner)
    with pytest.raises(ContractError, match="explicit --approve-live-cost"):
        eval_runner.evaluate_suite("experiments/dev-validation-pilot.template.yaml")


def test_approved_pilot_persists_plan_manifest_and_qualification(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _ready_live_environment(monkeypatch, tmp_path)
    preflight = eval_runner.preflight_suite(
        "experiments/dev-validation-pilot.template.yaml"
    )
    captured = []

    class FakeRunner:
        def start(self, _task, *, manifest, **_):
            captured.append(manifest)
            return {
                "run_id": manifest.run_id,
                "outcome_kind": "task_failure",
                "usage": {
                    "model_cost_usd": 0.5,
                    "model_calls": 2,
                    "tool_calls": 1,
                    "input_tokens": 100,
                    "output_tokens": 20,
                },
            }

    qualification_hash = "sha256:" + ("e" * 64)
    monkeypatch.setattr(eval_runner, "AgentRunner", FakeRunner)
    monkeypatch.setattr(
        eval_runner,
        "_qualify_terminal_run",
        lambda run_id, _task: {
            "run_id": run_id,
            "qualified": True,
            "trace_integrity_passed": True,
            "evaluation_reached": True,
            "qualification_hash": qualification_hash,
        },
    )

    result = eval_runner.evaluate_suite(
        "experiments/dev-validation-pilot.template.yaml",
        approve_live_cost=True,
        approved_execution_hash=preflight["execution_hash"],
    )

    assert len(captured) == 1
    assert captured[0].experiment.purpose == (
        ExperimentPurpose.DEVELOPMENT_VALIDATION_LIVE_PILOT
    )
    assert captured[0].experiment.execution_hash == result["execution_hash"]
    assert result["runs"][0]["qualification"]["qualification_hash"] == qualification_hash
    plan_path = Path(result["execution_plan"]["path"])
    assert plan_path.is_file()
    assert json.loads(plan_path.read_text(encoding="utf-8"))["schema_version"] == (
        "experiment-execution-plan-v1"
    )
    journal_rows = [
        json.loads(line)
        for line in Path(result["campaign_journal"]["path"])
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert [row["event_type"] for row in journal_rows] == [
        "CampaignStarted",
        "RunStarted",
        "RunTerminal",
        "CampaignCompleted",
    ]
    assert journal_rows[1]["payload"]["run_id"] == result["runs"][0]["run_id"]
    previous_hash = None
    for sequence, row in enumerate(journal_rows, start=1):
        recorded_hash = row.pop("event_hash")
        assert row["sequence"] == sequence
        assert row["previous_event_hash"] == previous_hash
        assert sha256_text(canonical_json(row)) == recorded_hash
        previous_hash = recorded_hash
    retry = eval_runner.preflight_suite(
        "experiments/dev-validation-pilot.template.yaml"
    )
    assert {
        "EXPERIMENT_RESULT_EXISTS",
        "EXPERIMENT_JOURNAL_EXISTS",
    }.issubset({row["code"] for row in retry["blockers"]})


def test_hard_crash_journal_blocks_duplicate_paid_schedule(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _ready_live_environment(monkeypatch, tmp_path)
    preflight = eval_runner.preflight_suite(
        "experiments/dev-validation-pilot.template.yaml"
    )

    class CrashingRunner:
        def start(self, *_args, **_kwargs):
            raise SystemExit("synthetic hard crash after durable row start")

    monkeypatch.setattr(eval_runner, "AgentRunner", CrashingRunner)
    with pytest.raises(SystemExit, match="synthetic hard crash"):
        eval_runner.evaluate_suite(
            "experiments/dev-validation-pilot.template.yaml",
            approve_live_cost=True,
            approved_execution_hash=preflight["execution_hash"],
        )

    retry = eval_runner.preflight_suite(
        "experiments/dev-validation-pilot.template.yaml"
    )
    assert "EXPERIMENT_JOURNAL_EXISTS" in {
        row["code"] for row in retry["blockers"]
    }
    journal_rows = [
        json.loads(line)
        for line in Path(retry["journal_path"]).read_text(encoding="utf-8").splitlines()
    ]
    assert [row["event_type"] for row in journal_rows] == [
        "CampaignStarted",
        "RunStarted",
    ]


def test_environment_drift_after_preflight_stops_before_agent(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _ready_live_environment(monkeypatch, tmp_path)
    commits = iter(["a" * 40, "a" * 40, "b" * 40])
    monkeypatch.setattr(
        eval_runner,
        "_git_state",
        lambda: {"available": True, "commit": next(commits), "clean": True},
    )
    preflight = eval_runner.preflight_suite(
        "experiments/dev-validation-pilot.template.yaml"
    )

    class ForbiddenRunner:
        def __init__(self):
            pytest.fail("environment drift must stop before AgentRunner construction")

    monkeypatch.setattr(eval_runner, "AgentRunner", ForbiddenRunner)
    with pytest.raises(ContractError, match="changed after the approved preflight"):
        eval_runner.evaluate_suite(
            "experiments/dev-validation-pilot.template.yaml",
            approve_live_cost=True,
            approved_execution_hash=preflight["execution_hash"],
        )


@pytest.mark.parametrize("model", ["openai", "gpt-5.6-terra", "unknown-provider"])
def test_direct_openai_run_is_blocked_before_adapter_construction(
    monkeypatch,
    model: str,
) -> None:
    def forbidden_run(*_, **__):
        pytest.fail("direct live run must not reach run_from_cli")

    monkeypatch.setattr("patchloop.agent.runner.run_from_cli", forbidden_run)
    result = CliRunner().invoke(
        app,
        [
            "run",
            "--task",
            "tasks/smoke/csv-quoted-newline/public.yaml",
            "--model",
            model,
        ],
    )

    assert result.exit_code == 1
    assert "direct live runs are disabled" in result.stdout


def test_core_campaign_requires_exact_design() -> None:
    with pytest.raises(ValidationError, match="12 unique"):
        ExperimentSuite(
            experiment_id="core-test",
            core=True,
            tasks=["task"],
            conditions=["no_memory"],
            model="mock",
        )


def test_core_campaign_requires_dataset_manifest_hash() -> None:
    with pytest.raises(ValidationError, match="dataset manifest hash"):
        ExperimentSuite(
            experiment_id="core-test",
            core=True,
            tasks=[f"task-{index}" for index in range(12)],
            conditions=[
                "no_memory",
                "raw_trace",
                "structured",
                "selective_structured",
            ],
            repetitions=2,
            model="mock",
            embedding_revision="test-revision",
        )


def test_offline_smoke_remains_a_calibration_suite() -> None:
    suite = eval_runner.load_suite("experiments/smoke.yaml")
    assert suite.core is False
    assert suite.purpose == ExperimentPurpose.OFFLINE_SMOKE
    assert suite.dataset_manifest_hash is None


def test_core_campaign_rejects_calibration_registry_role(tmp_path, monkeypatch) -> None:
    package = load_task_package("tasks/dev-train/duration-minute-boundary")
    dataset = load_dataset_manifest()
    suite_path = tmp_path / "suite.yaml"
    suite_path.write_text(
        yaml.safe_dump(_core_suite_payload(dataset[1]), sort_keys=False),
        encoding="utf-8",
    )
    preflight_calls = 0

    def frozen_preflight():
        nonlocal preflight_calls
        preflight_calls += 1
        return dataset

    monkeypatch.setattr(eval_runner, "require_frozen_dataset", frozen_preflight)
    monkeypatch.setattr(eval_runner, "load_task_package", lambda _: package)

    with pytest.raises(ContractError, match="dataset role calibration is not eligible"):
        eval_runner.evaluate_suite(suite_path)
    assert preflight_calls == 1


def test_core_campaign_rejects_dataset_manifest_hash_drift(tmp_path, monkeypatch) -> None:
    dataset = load_dataset_manifest()
    suite_path = tmp_path / "suite.yaml"
    suite_path.write_text(
        yaml.safe_dump(
            _core_suite_payload("sha256:" + ("f" * 64)),
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(eval_runner, "require_frozen_dataset", lambda: dataset)

    with pytest.raises(ContractError, match="does not match"):
        eval_runner.evaluate_suite(suite_path)


def test_core_campaign_runs_complete_frozen_dataset_preflight_first(
    tmp_path: Path,
    monkeypatch,
) -> None:
    suite_path = tmp_path / "suite.yaml"
    suite_path.write_text(
        yaml.safe_dump(
            _core_suite_payload("sha256:" + ("a" * 64)),
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    def reject_incomplete_dataset():
        raise ContractError("core experiment requires a complete frozen dataset")

    def fail_if_task_loading_starts(_):
        pytest.fail("task loading must not start before the frozen-dataset preflight")

    monkeypatch.setattr(
        eval_runner,
        "require_frozen_dataset",
        reject_incomplete_dataset,
    )
    monkeypatch.setattr(eval_runner, "load_task_package", fail_if_task_loading_starts)

    with pytest.raises(ContractError, match="complete frozen dataset"):
        eval_runner.evaluate_suite(suite_path)


def test_core_campaign_schedule_remains_96_runs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    manifest_hash = "sha256:" + ("a" * 64)
    suite_path = tmp_path / "suite.yaml"
    suite_path.write_text(
        yaml.safe_dump(_core_suite_payload(manifest_hash), sort_keys=False),
        encoding="utf-8",
    )
    dataset = SimpleNamespace(dataset_id="core-role-test")
    preflight_calls = 0

    def frozen_preflight():
        nonlocal preflight_calls
        preflight_calls += 1
        return dataset, manifest_hash, tmp_path / "dataset.yaml"

    def fake_load_task_package(path):
        index = int(Path(path).name.removeprefix("task-"))
        split = "same-repo-heldout" if index < 6 else "cross-repo-heldout"
        public = SimpleNamespace(
            task_id=f"task-{index}",
            task_version=1,
            split=split,
            repository=SimpleNamespace(base_commit=f"{index:040x}"),
        )
        image_digest = "sha256:" + f"{index + 200:064x}"
        return SimpleNamespace(
            public=public,
            root=str((eval_runner.repository_root() / f"task-{index}").resolve()),
            public_spec_hash="sha256:" + f"{index:064x}",
            private_spec_hash="sha256:" + f"{index + 100:064x}",
            environment=SimpleNamespace(
                evaluator_image=f"example.invalid/task-{index}@{image_digest}",
                image_digest=image_digest,
            ),
        )

    def fake_require_dataset_role(*, task_id, **_):
        index = int(task_id.removeprefix("task-"))
        role = (
            DatasetRole.CORE_SAME_REPO
            if index < 6
            else DatasetRole.CORE_CROSS_REPO
        )
        return SimpleNamespace(
            role=role,
            path=f"task-{index}",
            private_spec_hash="sha256:" + f"{index + 100:064x}",
        )

    index_path = tmp_path / "memory-index.json"
    index_path.write_text(
        json.dumps(
            {
                "entries": [{"memory_id": "mem_test"}],
                "embedding": {
                    "implementation": "sentence-transformers",
                    "revision": "test-revision",
                },
                "dataset_manifest_hash": manifest_hash,
            }
        ),
        encoding="utf-8",
    )

    starts: list[tuple[str, object]] = []

    class FakeRunner:
        def start(self, task, *, memory_condition, **_):
            starts.append((task, memory_condition))
            return {"usage": {"model_cost_usd": 0.0}}

    monkeypatch.setattr(eval_runner, "require_frozen_dataset", frozen_preflight)
    monkeypatch.setattr(eval_runner, "load_task_package", fake_load_task_package)
    monkeypatch.setattr(eval_runner, "require_dataset_role", fake_require_dataset_role)
    monkeypatch.setattr(eval_runner, "latest_frozen_index", lambda: index_path)
    monkeypatch.setattr(eval_runner, "AgentRunner", FakeRunner)
    monkeypatch.setattr(eval_runner, "runtime_root", lambda: tmp_path / "runtime")
    monkeypatch.setattr(
        eval_runner,
        "_qualify_terminal_run",
        lambda *_: pytest.fail("core runs must not use the development qualifier"),
    )

    result = eval_runner.evaluate_suite(suite_path)

    assert preflight_calls == 1
    assert result["expected_runs"] == 96
    assert result["completed_runs"] == 96
    assert result["infrastructure_errors"] == 0
    assert len(result["runs"]) == 96
    assert len(starts) == 96
    assert result["qualification_errors"] == 0
    assert Path(result["execution_plan"]["path"]).is_file()
    assert {row["task_id"] for row in result["runs"]} == {
        f"task-{index}" for index in range(12)
    }
    assert {
        row["condition"] for row in result["runs"]
    } == {
        "no_memory",
        "raw_trace",
        "structured",
        "selective_structured",
    }
    assert {row["repetition"] for row in result["runs"]} == {1, 2}


def test_core_campaign_rejects_memory_index_from_another_dataset() -> None:
    suite = ExperimentSuite.model_validate(_core_suite_payload("sha256:" + ("a" * 64)))
    index_payload = {
        "entries": [{"memory_id": "mem_test"}],
        "embedding": {
            "implementation": "sentence-transformers",
            "revision": "test-revision",
        },
        "dataset_manifest_hash": "sha256:" + ("b" * 64),
    }

    with pytest.raises(ContractError, match="memory index dataset manifest hash"):
        eval_runner._validate_memory_index(index_payload, suite)


def test_infrastructure_outcome_halts_and_preserves_not_started_ledger(
    tmp_path: Path,
    monkeypatch,
) -> None:
    suite_path = tmp_path / "offline-two-task.yaml"
    suite_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "experiment-v2",
                "experiment_id": "offline-infrastructure-halt",
                "purpose": "offline-smoke",
                "tasks": [
                    "tasks/smoke/csv-quoted-newline/public.yaml",
                    "tasks/smoke/config-falsy-override/public.yaml",
                ],
                "conditions": ["no_memory"],
                "repetitions": 1,
                "model": "mock",
                "model_id": "mock-v1",
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    captured_manifests = []

    class FakeRunner:
        def start(self, _task, *, manifest, **_):
            captured_manifests.append(manifest)
            return {
                "run_id": manifest.run_id,
                "outcome_kind": "infrastructure_error",
                "terminal_error": {
                    "type": "ProviderUnavailable",
                    "message": "synthetic provider failure",
                },
                "usage": {
                    "model_cost_usd": 0.125,
                    "model_calls": 1,
                    "tool_calls": 0,
                    "input_tokens": 50,
                    "output_tokens": 0,
                },
            }

    monkeypatch.setattr(eval_runner, "AgentRunner", FakeRunner)
    monkeypatch.setattr(eval_runner, "runtime_root", lambda: tmp_path / "runtime")
    monkeypatch.setattr(
        eval_runner,
        "_qualify_terminal_run",
        lambda *_: pytest.fail("offline smoke must not use the development qualifier"),
    )

    result = eval_runner.evaluate_suite(suite_path)

    assert len(captured_manifests) == 1
    assert captured_manifests[0].experiment is not None
    assert captured_manifests[0].experiment.execution_hash == result["execution_hash"]
    assert result["actual_model_cost_usd"] == 0.125
    assert result["infrastructure_errors"] == 1
    assert result["not_started_runs"] == 1
    assert len(result["runs"]) == 2
    assert result["runs"][0]["run_id"] == captured_manifests[0].run_id
    assert result["runs"][0]["usage"]["model_calls"] == 1
    assert result["runs"][1]["attempt_status"] == "not_started"
    assert result["runs"][1]["run_id"] is None
    assert result["runs"][1]["not_started_reason"]["type"] == "InfrastructureFailureHalt"
