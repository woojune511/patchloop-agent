"""Task-level statistical report derived only from raw experiment results."""

from __future__ import annotations

import csv
import html
import json
import random
import shutil
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path
from statistics import mean

from patchloop.errors import ContractError
from patchloop.runtime import runtime_root
from patchloop.state import StateStore
from patchloop.util import sha256_bytes

_CALIBRATION_ONLY_PURPOSES = {
    "memory-development-no-memory-budget-pilot",
    "memory-development-no-memory-corrective-pilot",
}


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int((len(ordered) - 1) * p)))
    return ordered[index]


def _task_bootstrap(task_values: dict[str, float], *, seed: int, samples: int = 10_000) -> dict:
    tasks = sorted(task_values)
    if not tasks:
        return {"estimate": 0.0, "ci95": [0.0, 0.0], "tasks": 0}
    generator = random.Random(seed)
    estimates = [mean(task_values[generator.choice(tasks)] for _ in tasks) for _ in range(samples)]
    return {
        "estimate": mean(task_values.values()),
        "ci95": [_percentile(estimates, 0.025), _percentile(estimates, 0.975)],
        "tasks": len(tasks),
    }


def _task_means(runs: list[dict], metric: Callable[[dict | None], float]) -> dict[str, float]:
    values: dict[str, list[float]] = defaultdict(list)
    for run in runs:
        if not _is_research_outcome(run):
            continue
        values[run["task_id"]].append(metric(run["result"]))
    return {task_id: mean(repetitions) for task_id, repetitions in values.items()}


def _is_research_outcome(run: dict) -> bool:
    result = run.get("result")
    return bool(
        run.get("attempt_status") != "not_started"
        and run.get("infrastructure_error") is None
        and run.get("qualification_error") is None
        and run.get("diagnostic_error") is None
        and (
            run.get("qualification") is None
            or run["qualification"].get("qualified") is True
        )
        and (
            run.get("diagnostic") is None
            or run["diagnostic"].get("status") == "passed"
        )
        and result is not None
        and result.get("outcome_kind") != "infrastructure_error"
    )


def _exclusion_reason(run: dict) -> str | None:
    if run.get("attempt_status") == "not_started":
        return "not_started"
    result = run.get("result")
    if run.get("infrastructure_error") is not None or (
        result is not None and result.get("outcome_kind") == "infrastructure_error"
    ):
        return "infrastructure_error"
    if run.get("qualification_error") is not None or (
        run.get("qualification") is not None
        and run["qualification"].get("qualified") is not True
    ):
        return "trace_qualification_failure"
    diagnostic_error = run.get("diagnostic_error")
    diagnostic = run.get("diagnostic")
    if diagnostic_error is not None or (
        diagnostic is not None and diagnostic.get("status") != "passed"
    ):
        if (
            diagnostic_error is not None
            and diagnostic_error.get("type")
            == "TraceExerciseInconclusive"
        ) or (
            diagnostic is not None
            and diagnostic.get("status") == "inconclusive"
        ):
            return "trace_exercise_inconclusive"
        return "trace_exercise_failure"
    if result is None:
        return "missing_terminal_result"
    return None


def _analysis_readiness(raw: dict) -> dict:
    reasons: list[str] = []
    runs = raw.get("runs", [])
    suite = raw.get("suite")
    expected_runs = raw.get("expected_runs")
    if raw.get("purpose") in _CALIBRATION_ONLY_PURPOSES:
        reasons.append(
            "experiment purpose is calibration-only and excluded from "
            "the comparison denominator"
        )
    if not isinstance(expected_runs, int) or len(runs) != expected_runs:
        reasons.append("scheduled row count does not match expected_runs")
    if any(_exclusion_reason(run) is not None for run in runs):
        reasons.append("one or more scheduled rows are not analysis-eligible outcomes")
    if not isinstance(suite, dict):
        reasons.append("predeclared suite matrix is unavailable")
    else:
        repetitions = suite.get("repetitions")
        conditions = suite.get("conditions")
        tasks = suite.get("tasks")
        if (
            not isinstance(repetitions, int)
            or not isinstance(conditions, list)
            or not isinstance(tasks, list)
        ):
            reasons.append("predeclared suite matrix is incomplete")
        else:
            observed_task_ids = {run.get("task_id") for run in runs}
            if None in observed_task_ids or len(observed_task_ids) != len(tasks):
                reasons.append("observed task identities do not match the suite task count")
            expected_repetitions = set(range(1, repetitions + 1))
            for condition in conditions:
                condition_rows = [
                    run for run in runs if run.get("condition") == condition
                ]
                condition_tasks = {run.get("task_id") for run in condition_rows}
                if condition_tasks != observed_task_ids:
                    reasons.append(f"condition {condition} has an incomplete task set")
                    continue
                for task_id in condition_tasks:
                    repetitions_seen = {
                        run.get("repetition")
                        for run in condition_rows
                        if run.get("task_id") == task_id
                    }
                    if repetitions_seen != expected_repetitions:
                        reasons.append(
                            f"condition {condition} task {task_id} "
                            "has incomplete repetitions"
                        )
    return {
        "analysis_ready": not reasons,
        "analysis_basis": (
            "complete-predeclared-matrix"
            if not reasons
            else "available-case-diagnostic-not-for-headlines"
        ),
        "analysis_blockers": list(dict.fromkeys(reasons)),
    }


def _result_metric(result: dict | None, name: str) -> float:
    if not result:
        return 0.0
    if name == "scrr":
        return float(bool(result["scope_compliant_success"]))
    if name == "hidden_pass":
        return float(result["verdicts"]["hidden_tests"] == "pass")
    if name == "regression_free":
        return float(result["verdicts"]["regression_tests"] == "pass")
    if name == "scope_violation":
        return float(result["verdicts"]["scope_policy"] == "fail")
    raise ValueError(name)


def _paired_differences(metrics: dict[str, dict[str, float]], seed: int) -> dict:
    baseline = metrics.get("no_memory", {})
    comparisons = {}
    for condition, task_values in metrics.items():
        if condition == "no_memory":
            continue
        shared = sorted(set(baseline) & set(task_values))
        differences = {task: task_values[task] - baseline[task] for task in shared}
        comparisons[condition] = _task_bootstrap(differences, seed=seed)
    return comparisons


def _flip_counts(runs: list[dict]) -> dict:
    indexed = {
        (run["task_id"], run["condition"], run["repetition"]): bool(
            run["result"] and run["result"]["scope_compliant_success"]
        )
        for run in runs
        if _is_research_outcome(run)
    }
    counts: dict[str, dict[str, int]] = defaultdict(
        lambda: {"failure_to_success": 0, "success_to_failure": 0, "unchanged": 0}
    )
    for (task, condition, repetition), success in indexed.items():
        if condition == "no_memory":
            continue
        baseline = indexed.get((task, "no_memory", repetition))
        if baseline is None:
            continue
        if not baseline and success:
            counts[condition]["failure_to_success"] += 1
        elif baseline and not success:
            counts[condition]["success_to_failure"] += 1
        else:
            counts[condition]["unchanged"] += 1
    return dict(counts)


def _copy_bundle_artifact(
    source_path: str | None,
    artifact_id: str | None,
    evidence_type: str,
    *,
    run_id: str,
    output_dir: Path,
    artifact_dir: Path,
    evidence_index: list[dict],
) -> str | None:
    if not source_path or not artifact_id or not Path(source_path).is_file():
        return None
    source_bytes = Path(source_path).read_bytes()
    artifact_dir.mkdir(parents=True, exist_ok=True)
    destination = artifact_dir / f"{artifact_id}.artifact"
    try:
        value = json.loads(source_bytes)

        def scrub_paths(item):
            if isinstance(item, dict):
                return {
                    key: "[normalized runtime artifact path]"
                    if key == "artifact_path" and isinstance(child, str)
                    else scrub_paths(child)
                    for key, child in item.items()
                }
            if isinstance(item, list):
                return [scrub_paths(child) for child in item]
            return item

        portable_bytes = json.dumps(scrub_paths(value), indent=2, ensure_ascii=False).encode(
            "utf-8"
        )
    except (UnicodeDecodeError, json.JSONDecodeError):
        portable_bytes = source_bytes
    destination.write_bytes(portable_bytes)
    relative = destination.relative_to(output_dir).as_posix()
    evidence_index.append(
        {
            "run_id": run_id,
            "evidence_type": evidence_type,
            "artifact_id": artifact_id,
            "path": relative,
            "source_content_hash": sha256_bytes(source_bytes),
            "content_hash": sha256_bytes(destination.read_bytes()),
            "normalized": portable_bytes != source_bytes,
        }
    )
    return relative


def _bundle_run_evidence(raw: dict, output_dir: Path) -> dict:
    state = StateStore(runtime_root() / "state.sqlite3")
    normalized = json.loads(json.dumps(raw))
    evidence_index = []
    runs_root = output_dir / "runs"
    if runs_root.exists():
        shutil.rmtree(runs_root)
    for run in normalized["runs"]:
        result = run["result"]
        if not result:
            continue
        run_id = result["run_id"]
        run_dir = output_dir / "runs" / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        artifact_dir = run_dir / "artifacts"

        if state.has_run(run_id):
            manifest = state.get_manifest(run_id)
            (run_dir / "manifest.json").write_text(
                manifest.model_dump_json(indent=2), encoding="utf-8"
            )
            events = state.list_events(run_id)
            normalized_events = []
            for event in events:
                event_payload = event.model_dump(mode="json")
                payload = event_payload["payload"]
                relative = _copy_bundle_artifact(
                    payload.get("artifact_path"),
                    payload.get("artifact_id"),
                    f"event:{event.type.value}",
                    run_id=run_id,
                    output_dir=output_dir,
                    artifact_dir=artifact_dir,
                    evidence_index=evidence_index,
                )
                if relative:
                    payload["artifact_path"] = relative
                normalized_events.append(json.dumps(event_payload, ensure_ascii=False))
            (run_dir / "events.jsonl").write_text(
                "".join(line + "\n" for line in normalized_events),
                encoding="utf-8",
            )
            checkpoint = state.latest_checkpoint(run_id)
            if checkpoint:
                (run_dir / "checkpoint.json").write_text(
                    checkpoint.model_dump_json(indent=2), encoding="utf-8"
                )
        patch_source = runtime_root() / "runs" / run_id / "submitted.patch"
        if patch_source.exists():
            shutil.copyfile(patch_source, run_dir / "submitted.patch")
        for verifier in result.get("verifier_results", []):
            source_path = verifier["details"].get("artifact_path")
            artifact_id = (
                verifier["evidence_artifact_ids"][0] if verifier["evidence_artifact_ids"] else None
            )
            relative = _copy_bundle_artifact(
                source_path,
                artifact_id,
                f"verifier:{verifier['check_id']}",
                run_id=run_id,
                output_dir=output_dir,
                artifact_dir=artifact_dir,
                evidence_index=evidence_index,
            )
            if relative:
                verifier["details"]["artifact_path"] = relative
        (run_dir / "result.json").write_text(
            json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    (output_dir / "evidence-index.json").write_text(
        json.dumps(evidence_index, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return normalized


def build_report(experiment: str, output: str | Path) -> dict:
    source = runtime_root() / "experiments" / f"{experiment}.json"
    if not source.exists():
        raise ContractError(f"unknown experiment: {experiment}")
    raw = json.loads(source.read_text(encoding="utf-8"))
    output_dir = Path(output)
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_copy = output_dir / "raw-experiment.json"
    normalized_raw = _bundle_run_evidence(raw, output_dir)
    raw_copy.write_text(json.dumps(normalized_raw, indent=2, ensure_ascii=False), encoding="utf-8")
    by_condition: dict[str, list[dict]] = defaultdict(list)
    rows = []
    for run in raw["runs"]:
        result = run["result"]
        by_condition[run["condition"]].append(run)
        usage = run.get("usage") or (result["usage"] if result else {})
        rows.append(
            {
                "task_id": run["task_id"],
                "split": run.get("split", "unknown"),
                "condition": run["condition"],
                "repetition": run["repetition"],
                "scope_compliant_success": int(_result_metric(result, "scrr")),
                "hidden_pass": int(_result_metric(result, "hidden_pass")),
                "regression_free": int(_result_metric(result, "regression_free")),
                "scope_violation": int(_result_metric(result, "scope_violation")),
                "input_tokens": usage.get("input_tokens", 0),
                "cached_input_tokens": usage.get("cached_input_tokens", 0),
                "cache_write_input_tokens": usage.get(
                    "cache_write_input_tokens",
                    0,
                ),
                "output_tokens": usage.get("output_tokens", 0),
                "reasoning_output_tokens": usage.get(
                    "reasoning_output_tokens",
                    0,
                ),
                "input_token_count_calls": usage.get(
                    "input_token_count_calls",
                    0,
                ),
                "model_cost_usd": usage.get("model_cost_usd", 0),
                "run_id": run.get("run_id") or (result["run_id"] if result else ""),
                "attempt_status": run.get(
                    "attempt_status",
                    "terminal" if result else "not_started",
                ),
                "outcome_kind": result.get("outcome_kind", "") if result else "",
                "infrastructure_error": json.dumps(run["infrastructure_error"] or {}),
                "qualification_status": (
                    run.get("qualification", {}).get("qualified")
                    if run.get("qualification") is not None
                    else ""
                ),
                "qualification_error": json.dumps(
                    run.get("qualification_error") or {}
                ),
                "diagnostic_status": (
                    run.get("diagnostic", {}).get("status")
                    if run.get("diagnostic") is not None
                    else ""
                ),
                "diagnostic_error": json.dumps(
                    run.get("diagnostic_error") or {}
                ),
                "analysis_included": int(_is_research_outcome(run)),
                "exclusion_reason": _exclusion_reason(run) or "",
            }
        )

    readiness = _analysis_readiness(raw)
    metrics = {}
    task_scrr_by_condition = {}
    for condition, condition_runs in sorted(by_condition.items()):
        research_runs = [run for run in condition_runs if _is_research_outcome(run)]
        task_scrr = _task_means(condition_runs, lambda result: _result_metric(result, "scrr"))
        task_scrr_by_condition[condition] = task_scrr
        scrr = _task_bootstrap(task_scrr, seed=raw["schedule_seed"])
        successes = sum(_result_metric(run["result"], "scrr") for run in research_runs)
        total_cost = sum(
            float(
                (run.get("usage") or (run["result"]["usage"] if run["result"] else {})).get(
                    "model_cost_usd",
                    0,
                )
            )
            for run in condition_runs
        )
        total_tokens = [
            int(
                (run.get("usage") or (run["result"]["usage"] if run["result"] else {})).get(
                    "input_tokens",
                    0,
                )
            )
            + int(
                (run.get("usage") or (run["result"]["usage"] if run["result"] else {})).get(
                    "output_tokens",
                    0,
                )
            )
            for run in condition_runs
            if run.get("usage") or run["result"]
        ]
        by_split = {}
        for split in sorted({run.get("split", "unknown") for run in condition_runs}):
            split_runs = [run for run in condition_runs if run.get("split", "unknown") == split]
            split_means = _task_means(split_runs, lambda result: _result_metric(result, "scrr"))
            by_split[split] = _task_bootstrap(split_means, seed=raw["schedule_seed"])
        metrics[condition] = {
            "scrr": scrr,
            "hidden_pass": _task_bootstrap(
                _task_means(condition_runs, lambda result: _result_metric(result, "hidden_pass")),
                seed=raw["schedule_seed"],
            ),
            "regression_free": _task_bootstrap(
                _task_means(
                    condition_runs,
                    lambda result: _result_metric(result, "regression_free"),
                ),
                seed=raw["schedule_seed"],
            ),
            "scope_violation": _task_bootstrap(
                _task_means(
                    condition_runs,
                    lambda result: _result_metric(result, "scope_violation"),
                ),
                seed=raw["schedule_seed"],
            ),
            "by_split": by_split,
            "runs": len(research_runs),
            "scheduled_runs": len(condition_runs),
            "infrastructure_runs": sum(
                _exclusion_reason(run) == "infrastructure_error"
                for run in condition_runs
            ),
            "qualification_excluded_runs": sum(
                _exclusion_reason(run) == "trace_qualification_failure"
                for run in condition_runs
            ),
            "diagnostic_inconclusive_runs": sum(
                _exclusion_reason(run) == "trace_exercise_inconclusive"
                for run in condition_runs
            ),
            "diagnostic_failed_runs": sum(
                _exclusion_reason(run) == "trace_exercise_failure"
                for run in condition_runs
            ),
            "not_started_runs": sum(
                run.get("attempt_status") == "not_started"
                for run in condition_runs
            ),
            "total_cost_usd": total_cost,
            "cost_per_success_usd": total_cost / successes if successes else None,
            "mean_total_tokens": mean(total_tokens) if total_tokens else 0,
        }

    report = {
        "schema_version": "analysis-report-v1",
        "experiment_id": experiment,
        "source": raw_copy.name,
        "source_runtime_hash": sha256_bytes(source.read_bytes()),
        "source_note": "runtime raw paths are normalized to the portable evidence bundle",
        "method": {
            "unit": "task",
            "repetition_aggregation": "mean within task",
            "bootstrap_samples": 10_000,
            "seed": raw["schedule_seed"],
            "interval": "95% percentile",
            "analysis_basis": readiness["analysis_basis"],
        },
        **readiness,
        "metrics": metrics,
        "headline_metrics": metrics if readiness["analysis_ready"] else None,
        "paired_scrr_difference_vs_no_memory": (
            _paired_differences(task_scrr_by_condition, raw["schedule_seed"])
            if readiness["analysis_ready"]
            else None
        ),
        "success_failure_flips_vs_no_memory": (
            _flip_counts(raw["runs"]) if readiness["analysis_ready"] else None
        ),
        "infrastructure_errors": raw["infrastructure_errors"],
    }
    (output_dir / "report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    with (output_dir / "runs.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else ["task_id"])
        writer.writeheader()
        writer.writerows(rows)
    table_rows = "".join(
        "<tr>"
        f"<td>{html.escape(condition)}</td>"
        f"<td>{values['scrr']['estimate']:.3f}</td>"
        f"<td>[{values['scrr']['ci95'][0]:.3f}, {values['scrr']['ci95'][1]:.3f}]</td>"
        f"<td>{values['scrr']['tasks']}</td>"
        "</tr>"
        for condition, values in metrics.items()
    )
    readiness_banner = (
        "<p><strong>Headline analysis ready.</strong></p>"
        if readiness["analysis_ready"]
        else (
            "<p><strong>Diagnostic available-case output only; not valid for "
            "headline comparison.</strong></p>"
        )
    )
    (output_dir / "report.html").write_text(
        "<!doctype html><meta charset='utf-8'><title>PatchLoop report</title>"
        f"<h1>Experiment {html.escape(experiment)}</h1>"
        f"{readiness_banner}"
        "<table><thead><tr><th>Condition</th><th>SCRR</th><th>95% CI</th>"
        f"<th>Tasks</th></tr></thead><tbody>{table_rows}</tbody></table>",
        encoding="utf-8",
    )
    return {"report": str(output_dir / "report.json"), "metrics": metrics}
