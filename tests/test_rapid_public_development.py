from __future__ import annotations

import json
from pathlib import Path

import pytest

from patchloop.agent.runner import AgentRunner
from patchloop.contracts import MemoryCondition, RunManifest, RunOutcomeKind, Usage
from patchloop.errors import ContractError
from patchloop.evals import rapid_public_development as rapid


def test_candidate_is_small_unofficial_and_no_call(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        rapid.DockerSandbox,
        "available",
        lambda: (_ for _ in ()).throw(AssertionError("Docker must not be called")),
    )
    monkeypatch.setattr(
        rapid.AgentRunner,
        "start",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("agent must not run")),
    )

    candidate = rapid.build_rapid_public_development_candidate()

    assert candidate["official"] is False
    assert candidate["execution_authorized"] is False
    assert candidate["provider_calls_made"] == 0
    assert candidate["docker_calls_made"] == 0
    assert candidate["runtime_dependencies"]["uv_lock_sha256"].startswith("sha256:")
    assert candidate["runtime_dependencies"]["openai_sdk_version"]
    assert len(candidate["schedule"]) == 8
    assert {row["memory_condition"] for row in candidate["schedule"]} == {"no_memory"}
    assert {row["variant"] for row in candidate["schedule"]} == set(rapid.VARIANTS)
    assert candidate["cost_control"]["full_schedule_reserve_nanos"] == 9_600_000_000
    assert candidate["cost_control"]["hard_cap_nanos"] == 10_000_000_000


def test_config_freezes_exact_balanced_schedule() -> None:
    config, _, _ = rapid._read_config(rapid.CONFIG_PATH, Path(".").resolve())
    assert len(config.schedule) == 8
    for task in rapid.TASK_PATHS:
        first = [row.variant for row in config.schedule if row.task == task and row.repetition == 1]
        second = [
            row.variant for row in config.schedule if row.task == task and row.repetition == 2
        ]
        assert second == list(reversed(first))


def test_baseline_and_lean_manifests_only_change_runtime_variant() -> None:
    candidate = rapid.build_rapid_public_development_candidate()
    baseline = rapid.build_rapid_run_manifest(candidate, 1)
    lean = rapid.build_rapid_run_manifest(candidate, 2)

    assert (baseline.tool_schema_version, baseline.context_policy_version) == (
        "v2",
        "phase-evidence-v5",
    )
    assert (lean.tool_schema_version, lean.context_policy_version) == (
        "v7",
        "phase-evidence-v12",
    )
    assert baseline.memory.condition == lean.memory.condition == MemoryCondition.NO_MEMORY
    assert baseline.memory.index_hash is None and lean.memory.index_hash is None
    assert baseline.budget == lean.budget == rapid.RUNTIME_BUDGET
    assert baseline.model == lean.model
    assert AgentRunner._runtime_contract(baseline)[0] == AgentRunner._runtime_contract(lean)[0]


def test_paid_boundary_recomputes_plan_config_source_and_manifest() -> None:
    candidate = rapid.build_rapid_public_development_candidate()
    manifest = rapid.build_rapid_run_manifest(candidate, 2)
    plan = rapid._plan(candidate, approved=True)

    assert rapid.rapid_live_plan_matches_manifest(plan=plan, manifest=manifest)

    tampered_plan = json.loads(json.dumps(plan))
    tampered_plan["schedule"][1]["variant"] = "baseline-v2v5"
    assert not rapid.rapid_live_plan_matches_manifest(plan=tampered_plan, manifest=manifest)

    tampered_plan = json.loads(json.dumps(plan))
    tampered_plan["runtime_dependencies"]["openai_sdk_version"] = "0.0.0"
    assert not rapid.rapid_live_plan_matches_manifest(plan=tampered_plan, manifest=manifest)

    payload = manifest.model_dump(mode="python")
    payload["model"]["temperature"] = 0.0
    payload["experiment"]["schedule_row_id"] = candidate["schedule"][0]["schedule_row_id"]
    tampered_manifest = RunManifest.model_validate(payload)
    assert not rapid.rapid_live_plan_matches_manifest(plan=plan, manifest=tampered_manifest)


def test_live_entry_fails_before_credentials_docker_or_writes_without_approval(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        rapid.DockerSandbox,
        "available",
        lambda: (_ for _ in ()).throw(AssertionError("Docker must not be called")),
    )
    with pytest.raises(ContractError, match="exact hash and cost-cap approval"):
        rapid.run_rapid_public_development(
            approve_live_cost=False,
            approved_execution_hash=None,
        )


def test_exact_cost_projection() -> None:
    usage = Usage(
        input_tokens=1_000,
        cached_input_tokens=100,
        cache_write_input_tokens=200,
        output_tokens=300,
    )
    assert rapid._usage_cost_nanos(usage) == 700 * 750 + 100 * 75 + 200 * 750 + 300 * 4_500


def test_unpersisted_runner_error_is_an_infrastructure_terminal() -> None:
    projected = rapid._row_projection(
        schedule_row={"order": 1},
        result=None,
        runner=object(),  # type: ignore[arg-type]
        error=RuntimeError("provider failed before durable result"),
    )

    assert projected["outcome_kind"] == RunOutcomeKind.INFRASTRUCTURE_ERROR.value
    assert projected["success_at_budget"] is False
    assert projected["error_type"] == "RuntimeError"
    assert projected["error_message"] is None

    contract = rapid._row_projection(
        schedule_row={"order": 1},
        result=None,
        runner=object(),  # type: ignore[arg-type]
        error=ContractError("live capability rejected"),
    )
    assert contract["error_message"] == "live capability rejected"


def test_single_result_bundle_is_hash_chained_and_append_only(tmp_path: Path) -> None:
    path = tmp_path / "rapid.jsonl"
    first = rapid._append_bundle_event(path, {"event": "batch-started"}, create=True)
    second = rapid._append_bundle_event(path, {"event": "row-terminal"})

    assert second["previous_event_hash"] == first["content_hash"]
    assert rapid._bundle_tail_hash(path) == second["content_hash"]

    lines = path.read_text(encoding="utf-8").splitlines()
    lines[0] = lines[0].replace("batch-started", "batch-tampered")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with pytest.raises(ContractError, match="event hash differs"):
        rapid._append_bundle_event(path, {"event": "batch-completed"})


def test_config_model_rejects_memory_or_metric_drift() -> None:
    config, _, _ = rapid._read_config(rapid.CONFIG_PATH, Path(".").resolve())
    body = config.model_dump(mode="json")
    body["memory_condition"] = "structured"
    with pytest.raises(ValueError):
        rapid.RapidPublicDevelopmentConfig.model_validate(body)

    body = config.model_dump(mode="json")
    body["metrics"] = ["success_at_budget"]
    with pytest.raises(ValueError):
        rapid.RapidPublicDevelopmentConfig.model_validate(body)
