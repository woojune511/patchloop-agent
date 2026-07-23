from __future__ import annotations

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
