from __future__ import annotations

import csv
import json

from patchloop.evals import report as report_module


def _result(run_id: str, success: bool) -> dict:
    state = "pass" if success else "fail"
    return {
        "run_id": run_id,
        "scope_compliant_success": success,
        "verdicts": {
            "hidden_tests": state,
            "regression_tests": "pass",
            "scope_policy": "pass",
        },
        "usage": {
            "input_tokens": 10,
            "output_tokens": 5,
            "model_cost_usd": 0.1,
        },
    }


def test_report_reaggregates_at_task_level(tmp_path, monkeypatch) -> None:
    root = tmp_path / "runtime"
    experiment_dir = root / "experiments"
    experiment_dir.mkdir(parents=True)
    raw = {
        "schedule_seed": 20260723,
        "infrastructure_errors": 0,
        "runs": [
            {
                "task_id": "a",
                "split": "same-repo-heldout",
                "condition": "no_memory",
                "repetition": 1,
                "result": _result("run_a1", True),
                "infrastructure_error": None,
            },
            {
                "task_id": "a",
                "split": "same-repo-heldout",
                "condition": "no_memory",
                "repetition": 2,
                "result": _result("run_a2", False),
                "infrastructure_error": None,
            },
            {
                "task_id": "b",
                "split": "cross-repo-heldout",
                "condition": "no_memory",
                "repetition": 1,
                "result": _result("run_b1", True),
                "infrastructure_error": None,
            },
        ],
    }
    (experiment_dir / "sample.json").write_text(json.dumps(raw), encoding="utf-8")
    monkeypatch.setattr(report_module, "runtime_root", lambda: root)
    report_module.build_report("sample", tmp_path / "report")
    report = json.loads((tmp_path / "report" / "report.json").read_text(encoding="utf-8"))
    assert report["metrics"]["no_memory"]["scrr"]["estimate"] == 0.75
    assert report["metrics"]["no_memory"]["scrr"]["tasks"] == 2
    with (tmp_path / "report" / "runs.csv").open(
        newline="",
        encoding="utf-8",
    ) as handle:
        row = next(csv.DictReader(handle))
    assert row["cached_input_tokens"] == "0"
    assert row["cache_write_input_tokens"] == "0"
    assert row["reasoning_output_tokens"] == "0"
    assert row["input_token_count_calls"] == "0"


def test_report_separates_infrastructure_and_not_started_rows(
    tmp_path,
    monkeypatch,
) -> None:
    root = tmp_path / "runtime"
    experiment_dir = root / "experiments"
    experiment_dir.mkdir(parents=True)
    agent_failure = _result("run_agent_failure", False)
    agent_failure["outcome_kind"] = "agent_failure"
    agent_failure["verdicts"]["scope_policy"] = "not_run"
    infrastructure = _result("run_infrastructure", False)
    infrastructure["outcome_kind"] = "infrastructure_error"
    infrastructure["verdicts"]["scope_policy"] = "not_run"
    raw = {
        "schedule_seed": 20260723,
        "infrastructure_errors": 1,
        "runs": [
            {
                "task_id": "a",
                "split": "same-repo-heldout",
                "condition": "no_memory",
                "repetition": 1,
                "attempt_status": "terminal",
                "run_id": "run_agent_failure",
                "usage": agent_failure["usage"],
                "result": agent_failure,
                "infrastructure_error": None,
            },
            {
                "task_id": "b",
                "split": "same-repo-heldout",
                "condition": "no_memory",
                "repetition": 1,
                "attempt_status": "terminal",
                "run_id": "run_infrastructure",
                "usage": infrastructure["usage"],
                "result": infrastructure,
                "infrastructure_error": {"type": "ProviderUnavailable"},
            },
            {
                "task_id": "c",
                "split": "same-repo-heldout",
                "condition": "no_memory",
                "repetition": 1,
                "attempt_status": "not_started",
                "run_id": None,
                "usage": None,
                "result": None,
                "infrastructure_error": None,
            },
        ],
    }
    (experiment_dir / "separated.json").write_text(
        json.dumps(raw),
        encoding="utf-8",
    )
    monkeypatch.setattr(report_module, "runtime_root", lambda: root)

    report_module.build_report("separated", tmp_path / "report-separated")

    report = json.loads(
        (tmp_path / "report-separated" / "report.json").read_text(encoding="utf-8")
    )
    metrics = report["metrics"]["no_memory"]
    assert metrics["runs"] == 1
    assert metrics["scheduled_runs"] == 3
    assert metrics["infrastructure_runs"] == 1
    assert metrics["not_started_runs"] == 1
    assert metrics["scope_violation"]["estimate"] == 0.0
    assert metrics["total_cost_usd"] == 0.2
    assert report["analysis_ready"] is False
    assert report["headline_metrics"] is None
    assert report["paired_scrr_difference_vs_no_memory"] is None


def test_report_excludes_trace_qualification_failures_from_research_metrics(
    tmp_path,
    monkeypatch,
) -> None:
    result = _result("run_unqualified", True)
    result["outcome_kind"] = "resolved"
    raw = {
        "schedule_seed": 20260723,
        "infrastructure_errors": 0,
        "runs": [
            {
                "task_id": "a",
                "split": "dev-train",
                "condition": "no_memory",
                "repetition": 1,
                "attempt_status": "terminal",
                "run_id": "run_unqualified",
                "usage": result["usage"],
                "result": result,
                "infrastructure_error": None,
                "qualification": {"qualified": False},
                "qualification_error": {
                    "type": "TraceQualificationFailed",
                    "message": (
                        "terminal trace did not satisfy deterministic qualification"
                    ),
                },
            }
        ],
    }

    runtime = tmp_path / ".patchloop"
    experiment_dir = runtime / "experiments"
    experiment_dir.mkdir(parents=True)
    (experiment_dir / "report-qualification.json").write_text(
        json.dumps(raw),
        encoding="utf-8",
    )
    monkeypatch.setattr(report_module, "runtime_root", lambda: runtime)

    report_module.build_report("report-qualification", tmp_path / "report")
    report = json.loads(
        (tmp_path / "report" / "report.json").read_text(encoding="utf-8")
    )
    metrics = report["metrics"]["no_memory"]

    assert metrics["runs"] == 0
    assert metrics["scrr"]["tasks"] == 0
    assert metrics["infrastructure_runs"] == 0
    assert metrics["qualification_excluded_runs"] == 1
    assert metrics["total_cost_usd"] == 0.1
    assert report["analysis_ready"] is False


def test_report_marks_only_complete_predeclared_matrix_headline_ready(
    tmp_path,
    monkeypatch,
) -> None:
    root = tmp_path / "runtime"
    experiment_dir = root / "experiments"
    experiment_dir.mkdir(parents=True)
    runs = []
    for task_id in ("a", "b"):
        for repetition in (1, 2):
            result = _result(f"run_{task_id}{repetition}", True)
            result["outcome_kind"] = "resolved"
            runs.append(
                {
                    "task_id": task_id,
                    "split": "same-repo-heldout",
                    "condition": "no_memory",
                    "repetition": repetition,
                    "attempt_status": "terminal",
                    "run_id": result["run_id"],
                    "usage": result["usage"],
                    "result": result,
                    "infrastructure_error": None,
                    "qualification": None,
                    "qualification_error": None,
                }
            )
    raw = {
        "schedule_seed": 20260723,
        "expected_runs": 4,
        "infrastructure_errors": 0,
        "suite": {
            "tasks": ["task-a", "task-b"],
            "conditions": ["no_memory"],
            "repetitions": 2,
        },
        "runs": runs,
    }
    (experiment_dir / "complete.json").write_text(
        json.dumps(raw),
        encoding="utf-8",
    )
    monkeypatch.setattr(report_module, "runtime_root", lambda: root)

    report_module.build_report("complete", tmp_path / "report-complete")
    report = json.loads(
        (tmp_path / "report-complete" / "report.json").read_text(encoding="utf-8")
    )

    assert report["analysis_ready"] is True
    assert report["analysis_basis"] == "complete-predeclared-matrix"
    assert report["headline_metrics"] == report["metrics"]
    assert report["paired_scrr_difference_vs_no_memory"] == {}
