from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

import pytest

from patchloop.contracts import Usage
from patchloop.errors import ContractError
from patchloop.evals import runner as eval_runner
from patchloop.evals.qualification import (
    _private_leak_tokens,
    calculate_source_evidence_hash,
    load_trace_qualification,
    qualify_run,
)
from patchloop.runtime import calculate_model_cost
from patchloop.state import StateStore
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json, sha256_bytes, sha256_text
from tests.test_d089_anyio_budget_only_probe import (
    SUITE_PATH,
    _ready_environment,
)

ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = (
    ROOT
    / "reports/live-pilot/"
    "anyio-workflow-completion-budget-only-v2v5-20260804-r1.json"
)
RUNTIME_ROOT = ROOT / ".patchloop"
EXPERIMENT_ID = "anyio-workflow-completion-budget-only-v2v5-20260804-r1"
RUN_ID = "run_e444de1bb20a4325"
EXECUTION_HASH = (
    "sha256:dafb1182bc77a80a19384406a528997d608dc935201df63e7fdc1ef5aad471c3"
)
REPORT_FILE_SHA256 = (
    "sha256:06006c95454618b7adcea305465fa63611d2043c70aaa3e1df2de9a3f5a192f1"
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _body() -> dict[str, Any]:
    return _load(REPORT_PATH)["semantic_body"]


def _skip_without_raw() -> None:
    path = RUNTIME_ROOT / "experiments" / f"{EXPERIMENT_ID}.json"
    if not path.is_file():
        pytest.skip("local immutable D-089 runtime evidence is unavailable")


def test_d090_portable_seal_has_content_addressed_strict_boundary() -> None:
    payload = _load(REPORT_PATH)

    assert sha256_bytes(REPORT_PATH.read_bytes()) == REPORT_FILE_SHA256
    assert set(payload) == {
        "schema_version",
        "report_id",
        "semantic_body_hash",
        "semantic_body",
    }
    assert payload["schema_version"] == (
        "anyio-budget-only-readiness-d090-evidence-v1"
    )
    body_hash = sha256_text(canonical_json(payload["semantic_body"]))
    assert payload["semantic_body_hash"] == body_hash
    assert payload["report_id"] == f"d090_{body_hash.removeprefix('sha256:')}"

    body = payload["semantic_body"]
    assert set(body) == {
        "milestone",
        "evidence_kind",
        "recorded_at",
        "sealed_at",
        "source_contract",
        "experiment",
        "environment",
        "original_probe_result",
        "run",
        "budget_pressure",
        "qualification",
        "public_trace_diagnostics",
        "journal_seal",
        "raw_local_artifacts",
        "evidence_validation",
        "analysis",
        "claims_boundary",
        "next_gate",
    }
    experiment = body["experiment"]
    assert experiment["experiment_id"] == EXPERIMENT_ID
    assert experiment["execution_hash"] == EXECUTION_HASH
    assert experiment["expected_runs"] == experiment["completed_runs"] == 1
    assert experiment["memory_condition"] == "no_memory"
    assert experiment["approved_maximum_cost_usd"] == 10

    gate = body["original_probe_result"]["completion_gate"]
    assert gate["schema_version"] == "workflow-completion-probe-gate-v1"
    assert gate["gate_id"] == "d089-anyio-budget-only-readiness"
    assert gate["budget_only_probe"] is True
    assert gate["calibration_only"] is True
    assert gate["passed"] is False
    assert gate["terminal_runs"] == gate["qualified_runs"] == 1
    assert gate["evaluator_reached_runs"] == gate["official_evaluator_runs"] == 0
    assert gate["budget_terminal_run_ids"] == [RUN_ID]
    assert gate["infrastructure_errors"] == 0
    assert gate["qualification_errors"] == 0
    assert gate["diagnostic_errors"] == 0
    assert gate["terminal_loop_failure_runs"] == 0
    assert gate["call_guard_contract_passed"] is True
    assert gate["comparison_denominator_eligible"] is False
    assert gate["memory_admission_unlocked"] is False

    run = body["run"]
    assert run["run_id"] == RUN_ID
    assert run["attempt_status"] == "terminal"
    assert run["outcome_kind"] == "agent_failure"
    assert run["evaluation_status"] == "not_run"
    assert run["official"] is False
    assert run["terminal_phase"] == "IMPLEMENT"
    assert run["usage"] == {
        "input_tokens": 1_737_041,
        "cached_input_tokens": 0,
        "cache_write_input_tokens": 0,
        "output_tokens": 219_068,
        "reasoning_output_tokens": 206_655,
        "total_tokens": 1_956_109,
        "model_calls": 79,
        "input_token_count_calls": 80,
        "tool_calls": 121,
        "wall_clock_ms": 1_628_695,
        "model_cost_usd": 2.28858675,
    }
    terminal = run["terminal_error"]
    assert terminal["reason_code"] == "exact_request_budget_exceeded"
    assert terminal["generation_started"] is False
    assert terminal["required_tokens"] == 58_804
    assert terminal["remaining_tokens"] == 43_891
    assert terminal["deficit_tokens"] == 14_913
    assert terminal["minimum_total_budget_same_prefix"] == 2_014_913

    pressure = body["budget_pressure"]
    assert pressure["binding_dimension"] == "total_tokens"
    assert pressure["headroom"] == {
        "total_tokens": 43_891,
        "wall_clock_ms": 171_305,
    }
    assert pressure["token_tail"]["triggered"] is True
    assert pressure["exact_request"]["blocked"] is True
    assert pressure["counterfactual_same_prefix_only"] is True

    qualification = body["qualification"]
    assert qualification["qualified"] is True
    assert qualification["evaluation_reached"] is False
    assert qualification["passed_checks"] == qualification["total_checks"] == 27
    assert qualification["disabled_call_guard_contract"] == {
        "schema_version": "qualification-gate-check-projection-v1",
        "check_id": "disabled_call_guard_contract",
        "check_count": 1,
        "passed": True,
    }

    claims = body["claims_boundary"]
    assert claims["provider_calls_made_by_probe"] == 79
    assert claims["actual_list_price_model_cost_usd"] == 2.28858675
    assert claims["provider_calls_made_by_seal"] == 0
    assert claims["added_model_cost_usd_by_seal"] == 0
    assert claims["no_memory_baseline_established"] is False
    assert claims["comparison_denominator_eligible"] is False
    assert claims["memory_review_admission_or_index_unlocked"] is False
    assert claims["core_campaign_unlocked"] is False
    assert claims["automatic_rerun_authorized"] is False
    assert body["next_gate"]["hard_consumption_enforced"] is True


def test_d090_portable_seal_binds_sources_and_is_leak_safe() -> None:
    payload = _load(REPORT_PATH)
    body = payload["semantic_body"]
    source = body["source_contract"]

    for role in ("suite", "source_gate"):
        descriptor = source[role]
        assert sha256_bytes((ROOT / descriptor["path"]).read_bytes()) == (
            descriptor["sha256"]
        )

    report_text = REPORT_PATH.read_text(encoding="utf-8")
    forbidden_keys = {
        "api_key",
        "authorization",
        "checks",
        "details",
        "verifier_results",
        "evidence_artifacts",
        "request_body",
        "response_id",
        "private_spec_hash",
        "hidden_artifacts",
        "patch_body",
        "reference_patch",
    }

    def walk_keys(value: object) -> set[str]:
        if isinstance(value, dict):
            return set(value) | {
                nested for child in value.values() for nested in walk_keys(child)
            }
        if isinstance(value, list):
            return {
                nested for child in value for nested in walk_keys(child)
            }
        return set()

    assert forbidden_keys.isdisjoint(walk_keys(payload))
    for marker in (
        "OPENAI_API_KEY",
        "Bearer ",
        "sk-",
        "diff --git",
        "@@ -",
        '"request_body"',
        '"response_id"',
    ):
        assert marker not in report_text

    package = load_task_package(
        ROOT / "tasks/dev-train/anyio-interrupt-runner-cleanup"
    )
    leaked = [
        token
        for token in _private_leak_tokens(package, api_key=None)
        if token in report_text
    ]
    assert leaked == []


def test_d090_raw_result_qualification_and_journal_reconcile_when_present() -> None:
    _skip_without_raw()
    body = _body()
    raw_descriptor = body["original_probe_result"]["raw_result"]
    raw_path = ROOT / raw_descriptor["path"]
    raw_bytes = raw_path.read_bytes()
    raw = json.loads(raw_bytes)
    row = raw["runs"][0]

    assert len(raw_bytes) == raw_descriptor["bytes"]
    assert sha256_bytes(raw_bytes) == raw_descriptor["sha256"]
    assert raw["experiment_id"] == EXPERIMENT_ID
    assert raw["execution_hash"] == EXECUTION_HASH
    assert raw["completion_gate"] == body["original_probe_result"][
        "completion_gate"
    ]
    assert row["run_id"] == RUN_ID
    assert row["usage"] == {
        key: value
        for key, value in body["run"]["usage"].items()
        if key != "total_tokens"
    }
    assert row["result"]["terminal_error"]["details"]["reason_code"] == (
        body["run"]["terminal_error"]["reason_code"]
    )
    assert row["budget_pressure"]["exact_request"]["deficit_tokens"] == (
        body["run"]["terminal_error"]["deficit_tokens"]
    )

    state = StateStore(RUNTIME_ROOT / "state.sqlite3")
    manifest = state.get_manifest(RUN_ID)
    events = state.list_events(RUN_ID)
    event_counts = Counter(event.type.value for event in events)
    assert len(events) == body["public_trace_diagnostics"]["events"] == 556
    assert len(state.list_checkpoints(RUN_ID)) == 123
    assert event_counts == {
        "RunStarted": 1,
        "PhaseChanged": 3,
        "ContextBuilt": 80,
        "ModelCalled": 79,
        "ToolCalled": 121,
        "ToolSucceeded": 86,
        "ToolFailed": 15,
        "CheckpointSaved": 123,
        "LoopDetected": 22,
        "ToolReplayed": 20,
        "PatchPrepared": 1,
        "PatchApplied": 1,
        "ToolAdmissionBlocked": 1,
        "ModelGenerationBlocked": 1,
        "FailureTagged": 1,
        "RunFailed": 1,
    }

    model_payloads = [
        event.payload for event in events if event.type.value == "ModelCalled"
    ]
    tool_payloads = [
        event.payload for event in events if event.type.value == "ToolCalled"
    ]
    usage = Usage.model_validate(row["usage"])
    assert len(model_payloads) == usage.model_calls == 79
    assert len(tool_payloads) == usage.tool_calls == 121
    assert sum(item["input_tokens"] for item in model_payloads) == (
        usage.input_tokens
    )
    assert sum(item["output_tokens"] for item in model_payloads) == (
        usage.output_tokens
    )
    assert all(
        item["requested_input_tokens"] == item["input_tokens"]
        and item["input_token_count_match"] is True
        and item["total_tokens"]
        == item["input_tokens"] + item["output_tokens"]
        and item["total_token_count_match"] is True
        and item["response_status"] == "completed"
        and item["response_incomplete_reason"] is None
        and item["response_truncation"] == "disabled"
        and item["store"] is False
        and item["previous_response_id_used"] is False
        for item in model_payloads
    )
    recalculated_cost = calculate_model_cost(usage, manifest.model)
    assert recalculated_cost == pytest.approx(2.28858675, abs=1e-12)
    assert recalculated_cost == pytest.approx(raw["actual_model_cost_usd"])

    persisted = load_trace_qualification(RUN_ID, root=RUNTIME_ROOT)
    recomputed = qualify_run(
        RUN_ID,
        task_dir=ROOT / "tasks/dev-train/anyio-interrupt-runner-cleanup",
        root=RUNTIME_ROOT,
        persist=False,
    )
    assert canonical_json(persisted) == canonical_json(recomputed)
    assert persisted["qualified"] is True
    assert len(persisted["checks"]) == 27
    assert all(check["passed"] for check in persisted["checks"])
    assert calculate_source_evidence_hash(RUN_ID, root=RUNTIME_ROOT) == (
        persisted["source_evidence_hash"]
    )

    raw_artifacts: dict[str, dict[str, Any]] = {}
    for descriptor in body["raw_local_artifacts"]:
        path = ROOT / descriptor["path"]
        assert path.is_file()
        content = path.read_bytes()
        assert len(content) == descriptor["bytes"]
        assert sha256_bytes(content) == descriptor["sha256"]
        if descriptor["role"] in {"execution-plan", "manifest"}:
            raw_artifacts[descriptor["role"]] = json.loads(content)

    plan = raw_artifacts["execution-plan"]
    durable_manifest = raw_artifacts["manifest"]
    source_commit = body["source_contract"]["harness_git_commit"]
    experiment = body["experiment"]
    runtime_contract = body["environment"]["runtime_contract"]

    assert plan["environment"]["git"]["commit"] == source_commit
    assert plan["runtime_contract"]["harness_git_commit"] == source_commit
    assert durable_manifest["harness_git_commit"] == source_commit
    assert plan["execution_hash"] == experiment["execution_hash"]
    assert plan["suite_hash"] == experiment["suite_hash"]
    assert plan["schedule_hash"] == experiment["schedule_hash"]
    assert plan["schedule"][0]["schedule_row_id"] == (
        experiment["schedule_row_id"]
    )
    assert all(
        plan["runtime_contract"][key] == value
        for key, value in runtime_contract.items()
    )
    assert plan["runtime_contract"]["transport_max_retries"] == (
        body["environment"]["model"]["transport_max_retries"]
    )

    assert durable_manifest["run_id"] == body["run"]["run_id"]
    assert durable_manifest["task_id"] == body["run"]["task_id"]
    assert durable_manifest["experiment"]["experiment_id"] == EXPERIMENT_ID
    assert durable_manifest["experiment"]["execution_hash"] == (
        experiment["execution_hash"]
    )
    assert durable_manifest["experiment"]["suite_hash"] == (
        experiment["suite_hash"]
    )
    assert durable_manifest["experiment"]["schedule_row_id"] == (
        experiment["schedule_row_id"]
    )
    assert durable_manifest["tool_schema_version"] == (
        runtime_contract["tool_schema_version"]
    )
    assert durable_manifest["context_policy_version"] == (
        runtime_contract["context_policy_version"]
    )
    assert durable_manifest["budget"] == body["budget_pressure"][
        "configured_limits"
    ]
    for key in (
        "provider",
        "model_id",
        "reasoning_effort",
        "reasoning_mode",
        "service_tier",
        "transport_max_retries",
        "max_output_tokens",
    ):
        assert durable_manifest["model"][key] == body["environment"]["model"][
            key
        ]

    journal_descriptor = body["journal_seal"]
    journal_path = ROOT / journal_descriptor["path"]
    journal = [
        json.loads(line)
        for line in journal_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    previous_hash = None
    for event in journal:
        body_without_hash = {
            key: value for key, value in event.items() if key != "event_hash"
        }
        assert event["previous_event_hash"] == previous_hash
        assert event["event_hash"] == sha256_text(
            canonical_json(body_without_hash)
        )
        previous_hash = event["event_hash"]
    assert [event["event_type"] for event in journal] == (
        journal_descriptor["event_types"]
    )
    assert [event["sequence"] for event in journal] == (
        journal_descriptor["sequences"]
    )
    assert journal[-1]["payload"]["result_hash"] == sha256_bytes(raw_bytes)
    assert journal[-1]["event_hash"] == journal_descriptor["final_event_hash"]
    assert raw["campaign_journal"]["last_event_hash_before_completion"] == (
        journal[-1]["previous_event_hash"]
    )


def test_d090_consumed_d089_is_hard_immutable_without_local_evidence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _ready_environment(monkeypatch, tmp_path)

    assert EXPERIMENT_ID in (
        eval_runner.CONSUMED_WORKFLOW_COMPLETION_PROBE_EXPERIMENT_IDS
    )
    assert EXPERIMENT_ID in eval_runner.HISTORICAL_IMMUTABLE_LIVE_EXPERIMENT_IDS
    assert EXPERIMENT_ID not in eval_runner.CONSUMED_CURRENT_LIVE_EXPERIMENT_IDS

    preflight = eval_runner.preflight_suite(SUITE_PATH)
    blocker_codes = {row["code"] for row in preflight["blockers"]}
    assert "HISTORICAL_SUITE_IMMUTABLE" in blocker_codes
    assert "LIVE_COST_NOT_APPROVED" in blocker_codes
    assert "APPROVAL_HASH_MISMATCH" in blocker_codes
    assert "EXPERIMENT_RESULT_EXISTS" not in blocker_codes
    assert "EXPERIMENT_JOURNAL_EXISTS" not in blocker_codes

    class ForbiddenRunner:
        def __init__(self) -> None:
            pytest.fail("hard-consumed D-089 must stop before runner construction")

    monkeypatch.setattr(eval_runner, "AgentRunner", ForbiddenRunner)
    with pytest.raises(ContractError, match="preflight failed"):
        eval_runner.evaluate_suite(
            SUITE_PATH,
            approve_live_cost=True,
            approved_execution_hash=preflight["execution_hash"],
        )

    runtime = tmp_path / "runtime"
    result_path = runtime / "experiments" / f"{EXPERIMENT_ID}.json"
    journal_path = (
        runtime / "experiments" / "journals" / f"{EXPERIMENT_ID}.jsonl"
    )
    result_path.parent.mkdir(parents=True, exist_ok=True)
    journal_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text("{}", encoding="utf-8")
    journal_path.write_text("{}\n", encoding="utf-8")

    with_artifacts = eval_runner.preflight_suite(SUITE_PATH)
    artifact_codes = {row["code"] for row in with_artifacts["blockers"]}
    assert "HISTORICAL_SUITE_IMMUTABLE" in artifact_codes
    assert "EXPERIMENT_RESULT_EXISTS" in artifact_codes
    assert "EXPERIMENT_JOURNAL_EXISTS" in artifact_codes
