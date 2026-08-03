from __future__ import annotations

import hashlib
import json
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from patchloop.evals.qualification import (
    _private_leak_tokens,
    calculate_source_evidence_hash,
)
from patchloop.state import StateStore
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json, sha256_text

SEAL_PATH = Path(
    "reports/live-pilot/generic-baseline-readiness-v2v5-20260803-r3.json"
)
EXPERIMENT_ID = "generic-baseline-readiness-v2v5-20260803-r3"
RUN_IDS = (
    "run_aa9c911512a547d2",
    "run_3995a029dc1f4b19",
    "run_f29df61ba1bc455a",
    "run_741ad42bf680486a",
)
PROJECTION_KEYS = {"schema_version", "check_id", "check_count", "passed"}


def _load_seal() -> dict[str, Any]:
    return json.loads(SEAL_PATH.read_text(encoding="utf-8"))


def _artifact_for_role(
    payload: dict[str, Any], role: str
) -> dict[str, Any]:
    matches = [
        artifact
        for artifact in payload["raw_local_artifacts"]
        if artifact["role"] == role
    ]
    assert len(matches) == 1
    return matches[0]


def _assert_artifact_identity(artifact: dict[str, Any]) -> None:
    content = Path(artifact["path"]).read_bytes()
    assert len(content) == artifact["bytes"]
    assert "sha256:" + hashlib.sha256(content).hexdigest() == artifact["sha256"]


def _assert_projection(projection: object) -> None:
    assert isinstance(projection, dict)
    assert set(projection) == PROJECTION_KEYS
    assert projection["schema_version"] == (
        "qualification-gate-check-projection-v1"
    )
    assert projection["check_id"] == "disabled_call_guard_contract"
    assert type(projection["check_count"]) is int
    assert projection["check_count"] == 1
    assert projection["passed"] is True


def _event_snapshot(state: StateStore, run_id: str) -> dict[str, Any]:
    events = state.list_events(run_id)
    model_payloads = [
        event.payload for event in events if event.type.value == "ModelCalled"
    ]
    tool_names = Counter(
        event.payload["tool"]
        for event in events
        if event.type.value == "ToolCalled"
    )
    loops = [
        event.payload for event in events if event.type.value == "LoopDetected"
    ]
    loop_reasons = Counter(loop["reason_code"] for loop in loops)
    event_counts = Counter(event.type.value for event in events)
    return {
        "events": len(events),
        "checkpoints": len(state.list_checkpoints(run_id)),
        "model_telemetry": {
            "completed_responses": sum(
                item["response_status"] == "completed" for item in model_payloads
            ),
            "incomplete_responses": sum(
                item["response_status"] != "completed" for item in model_payloads
            ),
            "exact_input_count_matches": sum(
                item["input_token_count_match"] is True for item in model_payloads
            ),
            "exact_total_count_matches": sum(
                item["total_token_count_match"] is True for item in model_payloads
            ),
            "truncation_disabled": sum(
                item["response_truncation"] == "disabled"
                for item in model_payloads
            ),
            "store_false": sum(item["store"] is False for item in model_payloads),
            "previous_response_dependency": sum(
                item["previous_response_id_used"] is True
                for item in model_payloads
            ),
            "maximum_input_tokens": max(
                item["requested_input_tokens"] for item in model_payloads
            ),
            "maximum_output_tokens": max(
                item["output_tokens"] for item in model_payloads
            ),
            "input_token_count_calls": sum(
                item["input_token_count_calls"] for item in model_payloads
            ),
        },
        "trace_diagnostics": {
            "tool_calls": dict(tool_names),
            "loop_detected": len(loops),
            "tool_replayed": event_counts["ToolReplayed"],
            "duplicate_search": loop_reasons["duplicate_search"],
            "fully_covered_read": loop_reasons["fully_covered_read"],
            "maximum_no_progress_streak": max(
                (item["no_progress_streak"] for item in loops), default=0
            ),
            "patches_prepared": event_counts["PatchPrepared"],
            "patches_applied": event_counts["PatchApplied"],
            "submission_accepted": event_counts["SubmissionAccepted"],
        },
    }


def test_d082_portable_seal_has_strict_internal_contract() -> None:
    payload = _load_seal()

    assert set(payload) == {
        "schema_version",
        "experiment_id",
        "purpose",
        "recorded_at",
        "source_harness_commit",
        "execution_hash",
        "suite_hash",
        "schedule_hash",
        "execution_plan_hash",
        "dataset",
        "runtime_contract",
        "model_tuple",
        "budget",
        "original_completion_gate",
        "runs",
        "qualifications",
        "aggregate_trace_telemetry",
        "analysis",
        "claims_boundary",
        "next_gate",
        "journal_seal",
        "portable_artifacts",
        "raw_local_artifacts",
        "evidence_policy",
        "evidence_validation",
    }
    assert payload["schema_version"] == (
        "generic-baseline-readiness-d082-evidence-v1"
    )
    assert payload["experiment_id"] == EXPERIMENT_ID
    assert payload["source_harness_commit"] == (
        "b4c79242bb0a94eed50530116205323e78c7d21a"
    )
    assert payload["runtime_contract"] == {
        "schema_version": "generic-baseline-runtime-contract-v2",
        "call_guard_policy": "model-tool-observability-only-v1",
        "tool_schema_version": "v2",
        "context_policy_version": "phase-evidence-v5",
        "system_prompt_hash": (
            "sha256:441c71fdea2defed14f06b32c3fba7a7aaa19f7a3ca749bc994e72708d8a733b"
        ),
        "tool_schema_hash": (
            "sha256:2ee296c2cf515bf2e0937ec1727dc02046a8560581d39b71246c5b91eccf0827"
        ),
        "transport_max_retries": 0,
        "harness_git_commit": "b4c79242bb0a94eed50530116205323e78c7d21a",
    }
    assert payload["budget"]["per_run"] == {
        "max_model_calls": None,
        "max_tool_calls": None,
        "max_total_tokens": 2_400_000,
        "wall_clock_timeout_seconds": 1_800,
        "max_output_tokens": 25_000,
    }

    gate = payload["original_completion_gate"]
    assert gate["schema_version"] == "generic-baseline-readiness-gate-v2"
    assert gate["passed"] is True
    assert gate["terminal_runs"] == gate["qualified_runs"] == 4
    assert gate["evaluator_reached_runs"] == gate["official_evaluator_runs"] == 4
    assert gate["call_guard_contract_passed"] is True
    assert gate["budget_terminal_runs"] == gate["terminal_loop_failure_runs"] == 0
    assert gate["task_successes"] == 1
    assert gate["task_success_required"] is False
    assert gate["comparison_denominator_eligible"] is False
    assert gate["memory_admission_unlocked"] is False

    runs = payload["runs"]
    assert tuple(run["run_id"] for run in runs) == RUN_IDS
    assert [run["outcome_kind"] for run in runs] == [
        "task_failure",
        "resolved",
        "task_failure",
        "task_failure",
    ]
    assert all(run["evaluation_status"] == "completed" for run in runs)
    assert all(run["official"] is True for run in runs)
    assert all(
        run["verdicts"][policy] == "pass"
        for run in runs
        for policy in ("regression_tests", "scope_policy", "safety_policy")
    )

    aggregate_usage = payload["budget"]["actual_campaign_usage"]
    additive_usage = (
        "input_tokens",
        "cached_input_tokens",
        "cache_write_input_tokens",
        "output_tokens",
        "reasoning_output_tokens",
        "total_tokens",
        "model_calls",
        "input_token_count_calls",
        "tool_calls",
        "wall_clock_ms",
    )
    for key in additive_usage:
        assert aggregate_usage[key] == sum(run["usage"][key] for run in runs)
    assert aggregate_usage["model_cost_usd"] == pytest.approx(
        sum(run["usage"]["model_cost_usd"] for run in runs)
    )
    for run in runs:
        usage = run["usage"]
        assert usage["total_tokens"] == (
            usage["input_tokens"] + usage["output_tokens"]
        )
        expected_cost = (
            (usage["input_tokens"] - usage["cached_input_tokens"]) * 0.75
            + usage["cached_input_tokens"] * 0.075
            + usage["output_tokens"] * 4.5
        ) / 1_000_000
        assert usage["model_cost_usd"] == pytest.approx(expected_cost)
        telemetry = run["model_telemetry"]
        assert telemetry["completed_responses"] == usage["model_calls"]
        assert telemetry["exact_input_count_matches"] == usage["model_calls"]
        assert telemetry["exact_total_count_matches"] == usage["model_calls"]
        assert telemetry["truncation_disabled"] == usage["model_calls"]
        assert telemetry["store_false"] == usage["model_calls"]
        assert telemetry["incomplete_responses"] == 0
        assert telemetry["previous_response_dependency"] == 0

    qualifications = payload["qualifications"]
    assert tuple(item["run_id"] for item in qualifications) == RUN_IDS
    for qualification in qualifications:
        _assert_projection(qualification["gate_projection"])
        assert qualification["qualified"] is True
        assert qualification["trace_integrity_passed"] is True
        assert qualification["leakage_scan_passed"] is True
        assert qualification["evaluation_reached"] is True
        assert qualification["passed_checks"] == qualification["total_checks"] == 28
        assert qualification["memory_candidate_eligible"] is False

    aggregate_trace = payload["aggregate_trace_telemetry"]
    assert aggregate_trace["events"] == sum(
        run["trace_diagnostics"]["events"] for run in runs
    )
    assert aggregate_trace["checkpoints"] == sum(
        run["trace_diagnostics"]["checkpoints"] for run in runs
    )
    for tool, count in aggregate_trace["tool_calls"].items():
        assert count == sum(
            run["trace_diagnostics"]["tool_calls"][tool] for run in runs
        )
    assert aggregate_trace["model_telemetry"] == {
        "completed_responses": 111,
        "incomplete_responses": 0,
        "exact_input_count_matches": 111,
        "exact_total_count_matches": 111,
        "truncation_disabled": 111,
        "store_false": 111,
        "previous_response_dependency": 0,
    }

    assert payload["analysis"]["analysis_ready"] is False
    assert payload["analysis"]["ordinary_metrics_empty"] is True
    assert payload["analysis"]["headline_metrics"] is None
    claims = payload["claims_boundary"]
    assert claims["live_provider_path_exercised"] is True
    assert claims["actual_invoice_or_free_tier_treatment_claimed"] is False
    assert claims["readiness_gate_passed"] is True
    assert claims["calibration_only"] is True
    assert claims["no_memory_performance_baseline_established"] is False
    assert claims["comparison_denominator_eligible"] is False
    assert claims["memory_admission_unlocked"] is False
    assert claims["core_campaign_unlocked"] is False
    assert payload["evidence_policy"]["original_completion_gate_immutable"] is True
    assert (
        payload["evidence_policy"][
            "original_completion_gate_retroactively_recomputed"
        ]
        is False
    )
    assert payload["portable_artifacts"] == []

    artifacts = payload["raw_local_artifacts"]
    assert len(artifacts) == 22
    assert len({item["role"] for item in artifacts}) == len(artifacts)
    assert len({item["path"] for item in artifacts}) == len(artifacts)


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("check_count", True),
        ("check_count", 1.0),
        ("check_count", 2),
        ("check_id", "different-check"),
        ("passed", False),
    ],
)
def test_d082_projection_contract_rejects_malformed_values(
    field: str, replacement: object
) -> None:
    projection = deepcopy(_load_seal()["qualifications"][0]["gate_projection"])
    projection[field] = replacement
    with pytest.raises(AssertionError):
        _assert_projection(projection)

    projection = deepcopy(_load_seal()["qualifications"][0]["gate_projection"])
    projection["extra"] = None
    with pytest.raises(AssertionError):
        _assert_projection(projection)


def test_d082_seal_reconciles_raw_result_trace_and_journal_when_present() -> None:
    payload = _load_seal()
    result_artifact = _artifact_for_role(payload, "experiment-result")
    if not Path(result_artifact["path"]).is_file():
        pytest.skip("raw local D-081 evidence is not bundled")

    missing = [
        artifact["path"]
        for artifact in payload["raw_local_artifacts"]
        if not Path(artifact["path"]).is_file()
    ]
    assert missing == []
    for artifact in payload["raw_local_artifacts"]:
        _assert_artifact_identity(artifact)

    raw = json.loads(Path(result_artifact["path"]).read_text(encoding="utf-8"))
    assert raw["experiment_id"] == payload["experiment_id"]
    assert raw["execution_hash"] == payload["execution_hash"]
    assert raw["suite_hash"] == payload["suite_hash"]
    assert raw["schedule_hash"] == payload["schedule_hash"]
    assert raw["execution_plan"]["artifact_hash"] == payload["execution_plan_hash"]
    assert payload["original_completion_gate"] == raw["completion_gate"]

    evidence_runs = {run["run_id"]: run for run in payload["runs"]}
    evidence_qualifications = {
        item["run_id"]: item for item in payload["qualifications"]
    }
    state_path = Path(".patchloop/state.sqlite3")
    assert state_path.is_file()
    state = StateStore(state_path)
    for row in raw["runs"]:
        run = evidence_runs[row["run_id"]]
        result = row["result"]
        assert run["task_id"] == row["task_id"]
        assert run["schedule_row_id"] == row["schedule_row_id"]
        for key in (
            "outcome_kind",
            "agent_submission_status",
            "evaluation_status",
            "official",
            "scope_compliant_success",
            "verdicts",
        ):
            assert run[key] == result[key]
        for key, value in result["usage"].items():
            assert run["usage"][key] == value
        assert run["usage"]["total_tokens"] == (
            result["usage"]["input_tokens"] + result["usage"]["output_tokens"]
        )

        raw_pressure = row["budget_pressure"]
        pressure = run["budget_pressure"]
        assert pressure["binding_dimension"] == raw_pressure["binding_dimension"]
        assert pressure["binding_reason"] == raw_pressure["binding_reason"]
        assert pressure["total_token_headroom"] == raw_pressure["headroom"][
            "total_tokens"
        ]
        assert pressure["wall_clock_headroom_ms"] == raw_pressure["headroom"][
            "wall_clock_ms"
        ]
        assert pressure["blocked_tool_count"] == raw_pressure["blocked_tool_count"]
        assert pressure["token_tail_triggered"] == raw_pressure["token_tail"][
            "triggered"
        ]
        assert pressure["exact_request_blocked"] == raw_pressure["exact_request"][
            "blocked"
        ]

        snapshot = _event_snapshot(state, row["run_id"])
        assert run["model_telemetry"] == {
            key: value
            for key, value in snapshot["model_telemetry"].items()
            if key != "input_token_count_calls"
        }
        assert snapshot["model_telemetry"]["input_token_count_calls"] == run[
            "usage"
        ]["input_token_count_calls"]
        trace = snapshot["trace_diagnostics"]
        expected_trace = run["trace_diagnostics"]
        assert snapshot["events"] == expected_trace["events"]
        assert snapshot["checkpoints"] == expected_trace["checkpoints"]
        for key in (
            "tool_calls",
            "loop_detected",
            "tool_replayed",
            "duplicate_search",
            "fully_covered_read",
            "maximum_no_progress_streak",
            "patches_prepared",
            "patches_applied",
            "submission_accepted",
        ):
            assert trace[key] == expected_trace[key]

        patch_path = Path(".patchloop/runs") / row["run_id"] / "submitted.patch"
        patch = patch_path.read_bytes()
        assert len(patch) == run["submitted_diff"]["size_bytes"]
        assert "sha256:" + hashlib.sha256(patch).hexdigest() == run[
            "submitted_diff"
        ]["content_hash"]
        scope_result = next(
            item
            for item in result["verifier_results"]
            if item["check_id"] == "scope"
        )
        assert scope_result["details"]["changed_files"] == run["submitted_diff"][
            "changed_files"
        ]
        assert scope_result["details"]["added_lines"] == run["submitted_diff"][
            "added_lines"
        ]
        assert scope_result["details"]["deleted_lines"] == run["submitted_diff"][
            "deleted_lines"
        ]

        summary = row["qualification"]
        qualification = evidence_qualifications[row["run_id"]]
        assert set(summary["gate_checks"]) == {"disabled_call_guard_contract"}
        _assert_projection(summary["gate_checks"]["disabled_call_guard_contract"])
        assert qualification["gate_projection"] == summary["gate_checks"][
            "disabled_call_guard_contract"
        ]
        raw_qualification = json.loads(
            Path(
                _artifact_for_role(
                    payload,
                    next(
                        item["role"]
                        for item in payload["raw_local_artifacts"]
                        if item["role"].endswith("-trace-qualification")
                        and row["run_id"] in item["path"]
                    ),
                )["path"]
            ).read_text(encoding="utf-8")
        )
        assert raw_qualification["qualification_hash"] == qualification[
            "qualification_hash"
        ]
        assert raw_qualification["source_evidence_hash"] == qualification[
            "source_evidence_hash"
        ]
        assert calculate_source_evidence_hash(row["run_id"]) == qualification[
            "source_evidence_hash"
        ]
        assert len(raw_qualification["checks"]) == qualification["total_checks"]
        assert sum(item["passed"] for item in raw_qualification["checks"]) == (
            qualification["passed_checks"]
        )
        call_guard_checks = [
            item
            for item in raw_qualification["checks"]
            if item["check_id"] == "disabled_call_guard_contract"
        ]
        assert len(call_guard_checks) == 1
        assert call_guard_checks[0]["passed"] is True

    aggregate = payload["budget"]["actual_campaign_usage"]
    assert raw["actual_model_cost_usd"] == pytest.approx(
        aggregate["model_cost_usd"]
    )
    assert sum(row["result"]["usage"]["model_calls"] for row in raw["runs"]) == (
        aggregate["model_calls"]
    )
    assert sum(row["result"]["usage"]["tool_calls"] for row in raw["runs"]) == (
        aggregate["tool_calls"]
    )

    report_artifact = _artifact_for_role(payload, "post-run-analysis-report")
    report = json.loads(Path(report_artifact["path"]).read_text(encoding="utf-8"))
    assert report["source_runtime_hash"] == payload["journal_seal"]["result_hash"]
    assert report["analysis_ready"] is False
    assert report["metrics"] == {}
    assert report["headline_metrics"] is None
    assert report["diagnostic_metrics"]["no_memory"]["scrr"] == payload[
        "analysis"
    ]["diagnostic_scrr"]

    journal_artifact = _artifact_for_role(payload, "campaign-journal")
    journal_rows = [
        json.loads(line)
        for line in Path(journal_artifact["path"])
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    previous_hash = None
    for sequence, row in enumerate(journal_rows, start=1):
        recorded_hash = row.pop("event_hash")
        assert row["sequence"] == sequence
        assert row["previous_event_hash"] == previous_hash
        assert sha256_text(canonical_json(row)) == recorded_hash
        previous_hash = recorded_hash
    seal = payload["journal_seal"]
    assert len(journal_rows) == seal["final_sequence"]
    assert journal_rows[-1]["event_type"] == seal["final_event_type"]
    assert previous_hash == seal["final_event_hash"]
    assert journal_rows[-1]["previous_event_hash"] == seal["previous_event_hash"]
    assert journal_rows[-1]["payload"]["result_hash"] == seal["result_hash"]
    assert result_artifact["sha256"] == seal["result_hash"]


def test_d082_portable_seal_excludes_private_payloads() -> None:
    checked_text = SEAL_PATH.read_text(encoding="utf-8")
    payload = json.loads(checked_text)
    forbidden_keys = {
        "api_key",
        "authorization",
        "checks",
        "details",
        "verifier_results",
        "evidence_artifacts",
        "artifact_path",
        "headers",
        "input",
        "instructions",
        "output",
        "private_spec_hash",
        "hidden_artifacts",
        "request",
        "request_body",
        "response",
        "response_error",
        "response_id",
        "system_fingerprint",
        "text",
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
    assert checked_text.count('"check_id": "disabled_call_guard_contract"') == 4
    for marker in (
        "OPENAI_API_KEY",
        "Bearer ",
        "sk-",
        '"request_body"',
        '"response_id"',
        '"private_spec_hash"',
    ):
        assert marker not in checked_text

    task_paths = (
        "tasks/dev-train/hf-hub-xet-endpoint-propagation",
        "tasks/dev-validation/babel-strict-grouped-decimal-trailing-zeroes",
        "tasks/dev-validation/moto-query-scanned-count",
        "tasks/dev-train/pyfakefs-makedirs-parent-traversal",
    )
    leaked: list[str] = []
    for task_path in task_paths:
        package = load_task_package(task_path)
        private_tokens = _private_leak_tokens(package, api_key=None)
        leaked.extend(token for token in private_tokens if token in checked_text)
    assert sorted(set(leaked)) == []
