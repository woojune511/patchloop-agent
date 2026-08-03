from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

import pytest

from patchloop.contracts import EventType, Usage
from patchloop.evals import runner as eval_runner
from patchloop.evals.qualification import (
    _private_leak_tokens,
    calculate_source_evidence_hash,
    load_trace_qualification,
    qualify_run,
)
from patchloop.state import StateStore
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json, sha256_bytes, sha256_text

ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = (
    ROOT
    / "reports/live-pilot/"
    "dev-no-memory-condition-neutral-accrued-cap-20260804-r1.json"
)
RUNTIME_ROOT = ROOT / ".patchloop"
EXPERIMENT_ID = "dev-no-memory-condition-neutral-accrued-cap-20260804-r1"
EXECUTION_HASH = (
    "sha256:0dd8ca1d0632398fed25ca28fbce89b97b0bf2137be163ed19a09fbf2d7f470d"
)
REPORT_FILE_SHA256 = (
    "sha256:2e24bfb0d98c2a7b2b0d8b5bf80c238ae048d782ce43c1cf08a2c10a6c6b5269"
)
RUN_IDS = (
    "run_eece333f601040b1",
    "run_28c86262518b4bba",
    "run_b6038236132749e1",
    "run_697fc8ab4ab04890",
    "run_277e06953fc14232",
    "run_c6683ae9a038435c",
    "run_4613c65b2a254349",
    "run_725807ab880a4719",
    "run_c04aa62b587d415e",
    "run_d17e180d1e344650",
    "run_d5c54d65ab6b4a60",
    "run_c0e186e798024698",
)
TASK_DIRS = {
    "pyfakefs-makedirs-parent-traversal": ROOT
    / "tasks/dev-train/pyfakefs-makedirs-parent-traversal",
    "anyio-interrupt-runner-cleanup": ROOT
    / "tasks/dev-train/anyio-interrupt-runner-cleanup",
    "hf-hub-xet-endpoint-propagation": ROOT
    / "tasks/dev-train/hf-hub-xet-endpoint-propagation",
    "pdm-ignore-active-venv-resolution": ROOT
    / "tasks/dev-train/pdm-ignore-active-venv-resolution",
    "loguru-invalid-format-feedback": ROOT
    / "tasks/dev-train/loguru-invalid-format-feedback",
    "tox-cross-section-empty-substitution": ROOT
    / "tasks/dev-train/tox-cross-section-empty-substitution",
}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _body() -> dict[str, Any]:
    return _load(REPORT_PATH)["semantic_body"]


def _skip_without_raw() -> None:
    result_path = RUNTIME_ROOT / "experiments" / f"{EXPERIMENT_ID}.json"
    if not result_path.is_file():
        pytest.skip("local immutable D-087 runtime evidence is unavailable")


def test_d088_portable_report_has_content_addressed_strict_boundary() -> None:
    payload = _load(REPORT_PATH)

    assert sha256_bytes(REPORT_PATH.read_bytes()) == REPORT_FILE_SHA256
    assert set(payload) == {
        "schema_version",
        "report_id",
        "semantic_body_hash",
        "semantic_body",
    }
    assert payload["schema_version"] == (
        "condition-neutral-no-memory-campaign-d088-evidence-v1"
    )
    body_hash = sha256_text(canonical_json(payload["semantic_body"]))
    assert payload["semantic_body_hash"] == body_hash
    assert payload["report_id"] == f"d088_{body_hash.removeprefix('sha256:')}"

    body = payload["semantic_body"]
    experiment = body["experiment"]
    assert experiment["experiment_id"] == EXPERIMENT_ID
    assert experiment["execution_hash"] == EXECUTION_HASH
    assert experiment["expected_runs"] == 12
    assert experiment["conditions"] == ["no_memory"]
    assert experiment["repetitions"] == 2

    gate = body["original_campaign_result"]["completion_gate"]
    assert gate["passed"] is False
    assert gate["terminal_runs"] == gate["qualified_runs"] == 12
    assert gate["evaluator_reached_runs"] == gate["official_evaluator_runs"] == 11
    assert gate["budget_terminal_run_ids"] == ["run_4613c65b2a254349"]
    assert gate["task_successes"] == 1
    assert gate["task_success_required"] is False
    assert gate["comparison_denominator_eligible"] is False
    assert gate["memory_admission_unlocked"] is False

    cost = body["campaign_cost"]
    assert cost["passed"] is True
    assert cost["fully_settled"] is True
    assert cost["actual_list_price_cost_usd"] == pytest.approx(5.36842875)
    assert cost["cap_usd"] == 25
    assert cost["maximum_committed_usd"] == pytest.approx(12.31149825)
    assert cost["cap_headroom_usd"] == pytest.approx(19.63157125)
    assert cost["reserved_runs"] == cost["settled_runs"] == 12
    assert cost["reserve_unavailable_events"] == 0
    assert cost["held_reserve_usd"] == 0
    assert cost["campaign_cap_binding"] is False

    runs = body["runs"]
    assert tuple(row["run_id"] for row in runs) == RUN_IDS
    assert [row["order"] for row in runs] == list(range(1, 13))
    assert Counter(row["result"]["outcome_kind"] for row in runs) == {
        "task_failure": 10,
        "agent_failure": 1,
        "resolved": 1,
    }
    assert sum(row["result"]["official"] for row in runs) == 11
    assert sum(row["qualification"]["evaluation_reached"] for row in runs) == 11
    assert all(row["qualification"]["qualified"] is True for row in runs)
    assert sum(row["result"]["hidden_tests"] == "pass" for row in runs) == 1
    assert all(
        row["result"][policy] == "pass"
        for row in runs
        if row["result"]["official"]
        for policy in ("regression_tests", "scope_policy", "safety_policy")
    )

    additive = (
        "input_tokens",
        "output_tokens",
        "reasoning_output_tokens",
        "total_tokens",
        "model_calls",
        "input_token_count_calls",
        "tool_calls",
        "wall_clock_ms",
    )
    aggregate = body["aggregate_usage"]
    for key in additive:
        assert aggregate[key] == sum(row["usage"][key] for row in runs)
    assert aggregate == {
        "input_tokens": 4_844_335,
        "cached_input_tokens": 0,
        "cache_write_input_tokens": 0,
        "output_tokens": 385_595,
        "reasoning_output_tokens": 342_811,
        "total_tokens": 5_229_930,
        "model_calls": 340,
        "input_token_count_calls": 341,
        "tool_calls": 547,
        "wall_clock_ms": 3_356_560,
        "model_cost_usd": 5.36842875,
    }
    assert aggregate["model_cost_usd"] == pytest.approx(
        sum(row["usage"]["model_cost_usd"] for row in runs)
    )
    for row in runs:
        usage = row["usage"]
        assert usage["total_tokens"] == (
            usage["input_tokens"] + usage["output_tokens"]
        )
        expected_cost = (
            usage["input_tokens"] * 0.75 + usage["output_tokens"] * 4.5
        ) / 1_000_000
        assert usage["model_cost_usd"] == pytest.approx(expected_cost)

    blocked = runs[6]
    assert blocked["run_id"] == "run_4613c65b2a254349"
    assert blocked["budget_pressure"] == {
        "binding_dimension": "total_tokens",
        "binding_reason": "exact_request_budget_exceeded",
        "total_token_headroom": 21_792,
        "exact_request_blocked": True,
        "requested_input_tokens": 14_080,
        "max_output_tokens": 25_000,
        "required_tokens": 39_080,
        "remaining_tokens": 21_792,
        "deficit_tokens": 17_288,
        "generation_started": False,
    }
    assert blocked["result"]["evaluation_status"] == "not_run"
    assert blocked["qualification"]["total_checks"] == 28
    assert all(row["qualification"]["total_checks"] == 29 for row in runs[:6])
    assert all(row["qualification"]["total_checks"] == 29 for row in runs[7:])

    trace = body["aggregate_trace"]
    for key in (
        "events",
        "checkpoints",
        "patches_prepared",
        "patches_applied",
        "rejected_candidates",
        "verified_retries",
        "tool_failures",
        "loop_observations",
        "tool_replays",
        "memory_retrieval_events",
        "model_generation_blocks",
        "submissions_accepted",
    ):
        row_key = {
            "loop_observations": "loops",
            "memory_retrieval_events": "memory_retrievals",
            "submissions_accepted": "submission_accepted",
        }.get(key, key)
        assert trace[key] == sum(row["trace"][row_key] for row in runs)
    assert trace["failed_retry_source_sequences"] == 0
    assert trace["completed_model_responses"] == 340
    assert trace["exact_input_count_matches"] == 340
    assert trace["exact_total_count_matches"] == 340
    assert trace["previous_response_dependency"] == 0

    analysis = body["analysis"]
    assert analysis["analysis_ready"] is False
    assert analysis["headline_metrics"] is None
    assert analysis["ordinary_metrics_empty"] is True
    assert analysis["diagnostic_scrr_numerator"] == 1
    assert analysis["diagnostic_scrr_denominator"] == 12
    assert analysis["campaign_spend_cap_was_a_confound"] is False
    assert analysis["per_run_total_token_ceiling_was_a_confound"] is True

    claims = body["claims_boundary"]
    assert claims["workflow_readiness_gate_passed"] is False
    assert claims["campaign_cost_control_passed"] is True
    assert claims["no_memory_performance_baseline_established"] is False
    assert claims["success_rate_estimated"] is False
    assert claims["comparison_denominator_eligible"] is False
    assert claims["memory_admission_unlocked"] is False
    assert claims["core_campaign_unlocked"] is False
    assert claims["automatic_rerun_authorized"] is False
    assert claims["hidden_driven_tuning_authorized"] is False
    assert claims["seal_provider_calls"] == 0
    assert claims["seal_added_model_cost_usd"] == 0
    assert body["next_gate"]["automatic_successor_authorized"] is False


def test_d088_portable_contract_survives_without_local_runtime(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    payload = _load(REPORT_PATH)
    monkeypatch.chdir(tmp_path)
    assert not Path(".patchloop").exists()
    body_hash = sha256_text(canonical_json(payload["semantic_body"]))
    assert payload["semantic_body_hash"] == body_hash
    assert payload["semantic_body"]["portable_contract"][
        "self_contained_without_local_runtime_artifacts"
    ] is True


def test_d088_raw_result_qualifications_and_trace_reconcile_when_present() -> None:
    _skip_without_raw()
    body = _body()
    raw_path = RUNTIME_ROOT / "experiments" / f"{EXPERIMENT_ID}.json"
    journal_path = (
        RUNTIME_ROOT / "experiments" / "journals" / f"{EXPERIMENT_ID}.jsonl"
    )
    before = {
        "result": sha256_bytes(raw_path.read_bytes()),
        "journal": sha256_bytes(journal_path.read_bytes()),
    }

    for artifact in body["raw_local_artifacts"]:
        path = ROOT / artifact["path"]
        assert path.is_file(), artifact["role"]
        assert path.stat().st_size == artifact["bytes"]
        assert sha256_bytes(path.read_bytes()) == artifact["sha256"]

    raw = _load(raw_path)
    assert raw["experiment_id"] == EXPERIMENT_ID
    assert raw["execution_hash"] == EXECUTION_HASH
    assert raw["suite_hash"] == body["experiment"]["suite_hash"]
    assert raw["schedule_hash"] == body["experiment"]["schedule_hash"]
    assert raw["execution_plan"]["artifact_hash"] == body["source_contract"][
        "execution_plan_semantic_hash"
    ]
    plan_path = ROOT / body["source_contract"]["execution_plan_path"]
    plan = _load(plan_path)
    assert sha256_text(canonical_json(plan)) == body["source_contract"][
        "execution_plan_semantic_hash"
    ]
    assert raw["completion_gate"] == body["original_campaign_result"][
        "completion_gate"
    ]
    assert raw["campaign_cost_qualification"]["passed"] is True

    state = StateStore(RUNTIME_ROOT / "state.sqlite3")
    evidence_by_run = {row["run_id"]: row for row in body["runs"]}
    for raw_row in raw["runs"]:
        evidence = evidence_by_run[raw_row["run_id"]]
        result = raw_row["result"]
        assert evidence["order"] == raw_row["order"]
        assert evidence["schedule_row_id"] == raw_row["schedule_row_id"]
        assert evidence["task_id"] == raw_row["task_id"]
        assert evidence["repetition"] == raw_row["repetition"]
        assert evidence["result"]["outcome_kind"] == result["outcome_kind"]
        assert evidence["result"]["evaluation_status"] == result[
            "evaluation_status"
        ]
        assert evidence["result"]["official"] == result["official"]
        for field, raw_field in (
            ("hidden_tests", "hidden_tests"),
            ("regression_tests", "regression_tests"),
            ("scope_policy", "scope_policy"),
            ("safety_policy", "safety_policy"),
        ):
            assert evidence["result"][field] == result["verdicts"][raw_field]
        for key, value in evidence["usage"].items():
            if key == "total_tokens":
                assert value == (
                    result["usage"]["input_tokens"]
                    + result["usage"]["output_tokens"]
                )
            else:
                assert value == result["usage"][key]

        persisted = load_trace_qualification(raw_row["run_id"], root=RUNTIME_ROOT)
        recomputed = qualify_run(
            raw_row["run_id"],
            task_dir=TASK_DIRS[raw_row["task_id"]],
            root=RUNTIME_ROOT,
            persist=False,
        )
        assert canonical_json(recomputed) == canonical_json(persisted)
        qualification = evidence["qualification"]
        assert persisted["qualified"] is qualification["qualified"] is True
        assert persisted["trace_integrity_passed"] is True
        assert persisted["leakage_scan_passed"] is True
        assert persisted["evaluation_reached"] == qualification[
            "evaluation_reached"
        ]
        assert persisted["qualification_hash"] == qualification[
            "qualification_hash"
        ]
        assert persisted["source_evidence_hash"] == qualification[
            "source_evidence_hash"
        ]
        assert calculate_source_evidence_hash(
            raw_row["run_id"], root=RUNTIME_ROOT, require_valid_plan=False
        ) == qualification["source_evidence_hash"]
        assert len(persisted["checks"]) == qualification["total_checks"]
        assert sum(check["passed"] for check in persisted["checks"]) == (
            qualification["passed_checks"]
        )
        projection = raw_row["qualification"]["gate_checks"][
            "disabled_call_guard_contract"
        ]
        assert projection == {
            "schema_version": "qualification-gate-check-projection-v1",
            "check_id": "disabled_call_guard_contract",
            "check_count": 1,
            "passed": True,
        }

        events = state.list_events(raw_row["run_id"])
        counts = Counter(event.type.value for event in events)
        trace = evidence["trace"]
        assert len(events) == trace["events"]
        assert len(state.list_checkpoints(raw_row["run_id"])) == trace[
            "checkpoints"
        ]
        assert counts[EventType.PATCH_PREPARED.value] == trace[
            "patches_prepared"
        ]
        assert counts[EventType.PATCH_APPLIED.value] == trace["patches_applied"]
        assert counts[EventType.TOOL_FAILED.value] == trace["tool_failures"]
        assert counts[EventType.LOOP_DETECTED.value] == trace["loops"]
        assert counts[EventType.TOOL_REPLAYED.value] == trace["tool_replays"]
        assert counts[EventType.MEMORY_RETRIEVED.value] == 0
        assert counts[EventType.MODEL_GENERATION_BLOCKED.value] == trace[
            "model_generation_blocks"
        ]
        assert counts[EventType.SUBMISSION_ACCEPTED.value] == trace[
            "submission_accepted"
        ]
        retry = raw_row["qualification"]["trace_features"][
            "rejected_patch_retry_context"
        ]
        assert retry["rejected_candidate_count"] == trace[
            "rejected_candidates"
        ]
        assert retry["verified_retry_count"] == trace["verified_retries"]
        assert retry["failed_source_failure_sequences"] == []

        models = [
            event.payload
            for event in events
            if event.type == EventType.MODEL_CALLED
        ]
        assert len(models) == result["usage"]["model_calls"]
        assert all(item["response_status"] == "completed" for item in models)
        assert all(item["input_token_count_match"] is True for item in models)
        assert all(item["total_token_count_match"] is True for item in models)
        assert all(item["response_truncation"] == "disabled" for item in models)
        assert all(item["store"] is False for item in models)
        assert all(item["previous_response_id_used"] is False for item in models)

        receipt = (
            RUNTIME_ROOT
            / "artifacts"
            / "runs"
            / raw_row["run_id"]
            / "evaluation-receipt.json"
        )
        patch = RUNTIME_ROOT / "runs" / raw_row["run_id"] / "submitted.patch"
        if raw_row["run_id"] == "run_4613c65b2a254349":
            assert not receipt.exists()
            assert not patch.exists()
        else:
            assert receipt.is_file()
            assert patch.is_file()

    after = {
        "result": sha256_bytes(raw_path.read_bytes()),
        "journal": sha256_bytes(journal_path.read_bytes()),
    }
    assert after == before


def test_d088_cost_journal_and_sqlite_consumptions_reconcile_when_present() -> None:
    _skip_without_raw()
    body = _body()
    raw = _load(RUNTIME_ROOT / "experiments" / f"{EXPERIMENT_ID}.json")
    journal_path = (
        RUNTIME_ROOT / "experiments" / "journals" / f"{EXPERIMENT_ID}.jsonl"
    )
    journal_rows = [
        json.loads(line)
        for line in journal_path.read_text(encoding="utf-8").splitlines()
    ]
    previous_hash = None
    for sequence, source in enumerate(journal_rows, start=1):
        row = dict(source)
        event_hash = row.pop("event_hash")
        assert row["sequence"] == sequence
        assert row["previous_event_hash"] == previous_hash
        assert sha256_text(canonical_json(row)) == event_hash
        previous_hash = event_hash

    seal = body["journal_seal"]
    assert Counter(row["event_type"] for row in journal_rows) == seal[
        "event_counts"
    ]
    assert len(journal_rows) == seal["final_sequence"] == 50
    assert sha256_bytes(journal_path.read_bytes()) == seal["file_sha256"]
    assert previous_hash == seal["final_event_hash"]
    assert journal_rows[-1]["previous_event_hash"] == seal[
        "previous_event_hash"
    ]
    assert journal_rows[-1]["payload"]["result_hash"] == seal["result_hash"]

    recomputed_cost = eval_runner._campaign_cost_journal_evidence(
        journal_path,
        raw["campaign_cost_control"],
        run_root=RUNTIME_ROOT,
    )
    assert recomputed_cost == raw["campaign_cost_qualification"]
    assert recomputed_cost["accrued_cost_nanos"] == sum(
        eval_runner._d087_fixed_cost_nanos(
            Usage.model_validate(row["result"]["usage"])
        )
        for row in raw["runs"]
    )
    assert recomputed_cost["accrued_cost_nanos"] == 5_368_428_750
    assert recomputed_cost["maximum_committed_nanos"] == 12_311_498_250
    assert recomputed_cost["cap_nanos"] == 25_000_000_000

    state = StateStore(RUNTIME_ROOT / "state.sqlite3")
    consumptions = state.list_d087_reservation_consumptions(
        execution_hash=EXECUTION_HASH
    )
    consumption_seal = body["durable_consumption_seal"]
    assert len(consumptions) == consumption_seal["sqlite_consumption_rows"] == 12
    assert len({row["schedule_row_id"] for row in consumptions}) == 12
    assert len({row["run_id"] for row in consumptions}) == 12
    assert sha256_text(canonical_json(consumptions)) == consumption_seal[
        "canonical_consumption_set_hash"
    ]
    journal_reservations = {
        (row["payload"]["schedule_row_id"], row["payload"]["run_id"]): row[
            "event_hash"
        ]
        for row in journal_rows
        if row["event_type"] == "RunCostReserved"
    }
    sqlite_reservations = {
        (row["schedule_row_id"], row["run_id"]) for row in consumptions
    }
    assert sqlite_reservations == set(journal_reservations)
    for consumption in consumptions:
        identity = (
            consumption["schedule_row_id"],
            consumption["run_id"],
        )
        assert consumption["reservation_event_hash"] == journal_reservations[
            identity
        ]
        assert consumption["control_hash"] == raw["campaign_cost_control"][
            "content_hash"
        ]


def test_d088_portable_report_is_leak_safe() -> None:
    report_text = REPORT_PATH.read_text(encoding="utf-8")
    payload = _load(REPORT_PATH)
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

    leaked: list[str] = []
    for task_dir in TASK_DIRS.values():
        package = load_task_package(task_dir)
        leaked.extend(
            token
            for token in _private_leak_tokens(package, api_key=None)
            if token in report_text
        )
    assert sorted(set(leaked)) == []
