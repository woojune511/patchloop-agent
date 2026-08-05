from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter
from decimal import Decimal
from pathlib import Path
from typing import Any

from patchloop.util import canonical_json, sha256_bytes, sha256_json, sha256_text

SEALED_AT = "2026-08-04T23:57:55Z"
EXPERIMENT_ID = "generic-high-headroom-readiness-v2v5-20260804-r1"
SOURCE_HARNESS_COMMIT = "82fbb33f20cabb57a151db871782345c6cafa3f0"
EXECUTION_HASH = "sha256:ae54b9cc14e3bcb80cbead61a003012cec4dbd0e8a205917b3cefdeaf0c11d75"
SUITE_HASH = "sha256:06f4be1917494c340db48fc5fb35ffb9ea443c4fa51ae6ee4cce6e3f0834c99a"
SCHEDULE_HASH = "sha256:e29fd7768666cf9891e40bed872d4739925b0c0ed7ed6187601ee63a9d8349df"
PLAN_CANONICAL_HASH = "sha256:02a0e7ee797ca128a6cdb5d0d38115ed93b57d73bcca1a18705aa2f6ea0c6989"
RAW_RESULT_HASH = "sha256:1b0c7d7452b70d6221c40b284646e50286f8f12b1d125d54bf66c1d89a0cf2b2"
FINAL_JOURNAL_EVENT_HASH = "sha256:fbaa048e3ed89e33de868a7794aa8c7d30b1af915c486e51b174f9630a1083a3"

SOURCE_FILES = {
    "suite": {
        "path": f"experiments/{EXPERIMENT_ID}.yaml",
        "bytes": 1_666,
        "sha256": ("sha256:a7d8382a7e46167bf3c439bcb93ed93a28797d83fb276c22180c74a236a39f67"),
    },
    "source-gate": {
        "path": ("reports/live-pilot/artifacts/d094-high-headroom-readiness-source-gate.json"),
        "bytes": 13_284,
        "sha256": ("sha256:6887936ec141496e35e3a9d3bd6c34cf04cf02d1849bf80208677151a692c6ed"),
    },
}

RUNTIME_FILES = {
    "raw-result": {
        "path": f".patchloop/experiments/{EXPERIMENT_ID}.json",
        "bytes": 44_567,
        "sha256": RAW_RESULT_HASH,
    },
    "campaign-journal": {
        "path": f".patchloop/experiments/journals/{EXPERIMENT_ID}.jsonl",
        "bytes": 5_659,
        "sha256": ("sha256:d5164b3d34bf0ec392d879b62aa0624f001499b0cb89f10c24145ef0aa26905b"),
    },
    "execution-plan": {
        "path": (
            ".patchloop/experiments/plans/"
            "ae54b9cc14e3bcb80cbead61a003012cec4dbd0e8a205917b3cefdeaf0c11d75.json"
        ),
        "bytes": 10_376,
        "sha256": ("sha256:f3e5464903f0f2ded5ce5287e397b505068f04606ebfefb208c82853af5a0476"),
    },
}

RUNS = (
    {
        "order": 1,
        "task_id": "anyio-interrupt-runner-cleanup",
        "run_id": "run_9fd10f7feeee4df5",
        "qualification_hash": (
            "sha256:6402956a6091245245e620d61212d3cd0cc27e75a325e3ab25692172dc766633"
        ),
        "source_evidence_hash": (
            "sha256:45482f3779dc31b250b87fbc0fb5d683eff86bdfea1541b2e1369cf63b9a5174"
        ),
        "files": {
            "manifest": (
                2_376,
                "sha256:a446b70c8c2c4848a5af7415446edcfa18aa6155615fb32f050a28af93f937ce",
            ),
            "result": (
                4_981,
                "sha256:a8b3b3f538709bd0bab7e113b08f927b9fdb3d51fe67e87d2beb7f223a754546",
            ),
            "provenance": (
                1_397,
                "sha256:595039959283aebbca5c7b9992bfc29441558969e24db6909eef2939e2e458b1",
            ),
            "evaluation-receipt": (
                600,
                "sha256:6b1bcd74e74113f151d421d73c285f5ebc7a9dcd35d13305f39387344611e82e",
            ),
            "qualification": (
                12_539,
                "sha256:a0c354860943966c2fb2c5bd322c6186e30d485c89343807d88788fe676de283",
            ),
            "submitted-patch": (
                567,
                "sha256:980900d852496dc8398de42654d2e1f6fbdbaac3d5389fb4ab45c5a2e7916956",
            ),
        },
    },
    {
        "order": 2,
        "task_id": "pyfakefs-makedirs-parent-traversal",
        "run_id": "run_7449597e84b94446",
        "qualification_hash": (
            "sha256:f18e55b1ebe63af5a6f0d786661d10fb09bdbaadb5a94c4997a95cfe42e5824b"
        ),
        "source_evidence_hash": (
            "sha256:ac0e9d538e3d948917dc07c216ae4cffa75ca6184f23bfbcb94eec4d175ad079"
        ),
        "files": {
            "manifest": (
                2_380,
                "sha256:0cd0879223f6b194f2d26ba700a99429cfd662404a907a418e70b94800dd11ca",
            ),
            "result": (
                4_962,
                "sha256:e6e6801884e6e376d996221e34ec99914f1ade635ad5c84e9feb9d4228c8c966",
            ),
            "provenance": (
                1_398,
                "sha256:da5286f44d43fdb1c4a4bc1827cc8057f835aaee8d9be6332e1d062ae8936df6",
            ),
            "evaluation-receipt": (
                599,
                "sha256:4203cbd3aceea494d9f91961f8f502aa7faa082dca69256fa82cc5d6fe10f497",
            ),
            "qualification": (
                12_105,
                "sha256:f4048561ed51fdf932e22146d2225d1c7dccb4825af5b6fdb8a3896d9bf34eb3",
            ),
            "submitted-patch": (
                509,
                "sha256:f14558292d6f03b9473b31740de84a2f872a57028cc89640aebb6f40e86d09ab",
            ),
        },
    },
    {
        "order": 3,
        "task_id": "hf-hub-xet-endpoint-propagation",
        "run_id": "run_9566c0367bd24f52",
        "qualification_hash": (
            "sha256:54fad91e8909bd4d0f4c83299fc0ad01cbf098fa4b85dbceef13171fc9ddcef8"
        ),
        "source_evidence_hash": (
            "sha256:3751a67fd3ff13ba74752441c3df0a6b9766bc8bb1b1c844bf52180077fd694f"
        ),
        "files": {
            "manifest": (
                2_377,
                "sha256:cc5fc6bd3ce6400c8e42cdc960ebbacdddd6160b6690c8179a7540a37f0a0bbf",
            ),
            "result": (
                4_971,
                "sha256:d16dacbb99789961c0f73b17756d33978914b096649bd935d699ec180f94f29e",
            ),
            "provenance": (
                1_398,
                "sha256:f5bbd0e0fc593ed11d384fe1f2e71aa73a1603c92f868b76608db0419a33a4ee",
            ),
            "evaluation-receipt": (
                599,
                "sha256:d664f6f07d8dbb9e845f300df0fd9079d9d58a9c74a894bca572e43eeaead141",
            ),
            "qualification": (
                12_705,
                "sha256:43c8be5315e936358a4c90e05b14d33e5e9e54d4fe30882bd9c0284f6b759976",
            ),
            "submitted-patch": (
                2_029,
                "sha256:31190ea073801608385a93b68d679fbde69b2ae04657980a26b76bb669ea8533",
            ),
        },
    },
)


class D095BuildError(RuntimeError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise D095BuildError(message)


def _read_exact(root: Path, descriptor: dict[str, Any], *, label: str) -> bytes:
    path = root / descriptor["path"]
    try:
        content = path.read_bytes()
    except OSError as exc:
        raise D095BuildError(f"{label} is unavailable") from exc
    _require(len(content) == descriptor["bytes"], f"{label} byte count drifted")
    _require(sha256_bytes(content) == descriptor["sha256"], f"{label} hash drifted")
    return content


def _load_json(content: bytes, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise D095BuildError(f"{label} is not valid JSON") from exc
    if not isinstance(value, dict):
        raise D095BuildError(f"{label} must be an object")
    return value


def _run_file_descriptor(expected: dict[str, Any], role: str) -> dict[str, Any]:
    run_id = expected["run_id"]
    size, digest = expected["files"][role]
    if role == "qualification":
        path = f".patchloop/qualifications/{run_id}.json"
    elif role == "submitted-patch":
        path = f".patchloop/runs/{run_id}/submitted.patch"
    else:
        filename = "evaluation-receipt.json" if role == "evaluation-receipt" else f"{role}.json"
        path = f".patchloop/artifacts/runs/{run_id}/{filename}"
    return {
        "role": role,
        "run_id": run_id,
        "path": path,
        "bytes": size,
        "sha256": digest,
    }


def _journal_projection(content: bytes) -> dict[str, Any]:
    try:
        rows = [json.loads(line) for line in content.decode("utf-8").splitlines() if line]
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise D095BuildError("campaign journal is invalid") from exc
    _require(len(rows) == 8, "campaign journal must contain eight events")
    previous_hash: str | None = None
    for sequence, row in enumerate(rows, start=1):
        _require(row.get("sequence") == sequence, "campaign journal sequence drifted")
        _require(
            row.get("previous_event_hash") == previous_hash,
            "campaign journal predecessor drifted",
        )
        payload = {key: value for key, value in row.items() if key != "event_hash"}
        _require(
            row.get("event_hash") == sha256_text(canonical_json(payload)),
            "campaign journal hash chain drifted",
        )
        previous_hash = row["event_hash"]
    expected_types = [
        "CampaignStarted",
        "RunStarted",
        "RunTerminal",
        "RunStarted",
        "RunTerminal",
        "RunStarted",
        "RunTerminal",
        "CampaignCompleted",
    ]
    _require(
        [row.get("event_type") for row in rows] == expected_types,
        "campaign journal event order drifted",
    )
    final = rows[-1]
    _require(final["event_hash"] == FINAL_JOURNAL_EVENT_HASH, "final journal event drifted")
    _require(
        final.get("payload", {}).get("result_hash") == RAW_RESULT_HASH,
        "campaign completion result hash drifted",
    )
    return {
        "path": RUNTIME_FILES["campaign-journal"]["path"],
        "bytes": RUNTIME_FILES["campaign-journal"]["bytes"],
        "file_sha256": RUNTIME_FILES["campaign-journal"]["sha256"],
        "event_count": len(rows),
        "event_types": expected_types,
        "sequences": list(range(1, 9)),
        "last_event_hash_before_completion": final["previous_event_hash"],
        "final_event_hash": final["event_hash"],
        "result_hash": final["payload"]["result_hash"],
    }


def _trace_projection(
    state_path: Path,
    run_id: str,
    usage: dict[str, Any],
) -> dict[str, Any]:
    if not state_path.is_file():
        raise D095BuildError("durable state database is unavailable")
    uri = f"file:{state_path.as_posix()}?mode=ro&immutable=1"
    try:
        connection = sqlite3.connect(uri, uri=True)
        connection.execute("PRAGMA query_only=ON")
        event_rows = connection.execute(
            "SELECT event_json FROM events WHERE run_id = ? ORDER BY sequence",
            (run_id,),
        ).fetchall()
        checkpoint_count = connection.execute(
            "SELECT COUNT(*) FROM checkpoints WHERE run_id = ?", (run_id,)
        ).fetchone()[0]
        worker_rows = connection.execute(
            "SELECT reclaimed FROM run_worker_claims WHERE run_id = ?", (run_id,)
        ).fetchall()
    except (sqlite3.Error, TypeError) as exc:
        raise D095BuildError("durable trace could not be read") from exc
    finally:
        if "connection" in locals():
            connection.close()
    events = [json.loads(row[0]) for row in event_rows]
    _require(events, f"durable trace is missing for {run_id}")
    _require(
        [event["sequence"] for event in events] == list(range(1, len(events) + 1)),
        f"durable trace sequence drifted for {run_id}",
    )
    counts = Counter(event["type"] for event in events)
    model_events = [event for event in events if event["type"] == "ModelCalled"]
    _require(
        len(model_events) == usage.get("model_calls"),
        f"model call count drifted for {run_id}",
    )
    _require(
        counts.get("ToolCalled", 0) == usage.get("tool_calls"),
        f"tool call count drifted for {run_id}",
    )
    _require(
        usage.get("input_token_count_calls") == len(model_events),
        f"input token count call drifted for {run_id}",
    )
    _require(
        all(
            event["payload"].get("response_status") == "completed"
            and event["payload"].get("requested_input_tokens")
            == event["payload"].get("input_tokens")
            and event["payload"].get("input_token_count_match") is True
            and event["payload"].get("total_token_count_match") is True
            and event["payload"].get("response_truncation") == "disabled"
            and event["payload"].get("store") is False
            and event["payload"].get("previous_response_id_used") is False
            for event in model_events
        ),
        f"model telemetry drifted for {run_id}",
    )
    for key in (
        "input_tokens",
        "cached_input_tokens",
        "cache_write_input_tokens",
        "output_tokens",
        "reasoning_output_tokens",
    ):
        _require(
            sum(event["payload"].get(key, 0) for event in model_events)
            == usage.get(key),
            f"{key} event sum drifted for {run_id}",
        )
    _require(
        sum(event["payload"].get("total_tokens", 0) for event in model_events)
        == usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
        f"total token event sum drifted for {run_id}",
    )
    return {
        "event_count": len(events),
        "checkpoint_count": checkpoint_count,
        "worker_claim_count": len(worker_rows),
        "reclaimed_worker_claim_count": sum(bool(row[0]) for row in worker_rows),
        "event_type_counts": dict(sorted(counts.items())),
        "completed_model_responses": len(model_events),
        "exact_input_token_matches": len(model_events),
        "exact_total_token_matches": len(model_events),
        "truncation_disabled_responses": len(model_events),
        "store_false_responses": len(model_events),
        "previous_response_dependency_count": 0,
    }


def _usage_cost(usage: dict[str, Any]) -> Decimal:
    uncached_input_tokens = usage["input_tokens"] - usage["cached_input_tokens"]
    return (
        Decimal(uncached_input_tokens) * Decimal("0.75")
        + Decimal(usage["cached_input_tokens"]) * Decimal("0.075")
        + Decimal(usage["output_tokens"]) * Decimal("4.5")
    ) / Decimal(1_000_000)


def build_seal(
    *, repo_root: Path, runtime_root: Path, sealed_at: str = SEALED_AT
) -> dict[str, Any]:
    suite_descriptor = SOURCE_FILES["suite"]
    source_gate_descriptor = SOURCE_FILES["source-gate"]
    _read_exact(repo_root, suite_descriptor, label="D-094 suite")
    source_gate = _load_json(
        _read_exact(repo_root, source_gate_descriptor, label="D-094 source gate"),
        label="D-094 source gate",
    )
    _require(
        source_gate.get("semantic_body_hash")
        == "sha256:ab7be9ad2448d1016b88d451e271330844fc11d8fd4b890f08142618446ff929",
        "D-094 source gate semantic hash drifted",
    )

    _require(
        runtime_root.resolve() == (repo_root / ".patchloop").resolve(),
        "runtime root must be the exact repository runtime",
    )
    raw_result = _load_json(
        _read_exact(repo_root, RUNTIME_FILES["raw-result"], label="raw result"),
        label="raw result",
    )
    plan = _load_json(
        _read_exact(repo_root, RUNTIME_FILES["execution-plan"], label="execution plan"),
        label="execution plan",
    )
    journal_content = _read_exact(
        repo_root,
        RUNTIME_FILES["campaign-journal"],
        label="campaign journal",
    )
    journal = _journal_projection(journal_content)

    _require(raw_result.get("experiment_id") == EXPERIMENT_ID, "experiment id drifted")
    _require(raw_result.get("execution_hash") == EXECUTION_HASH, "execution hash drifted")
    _require(raw_result.get("suite_hash") == SUITE_HASH, "suite hash drifted")
    _require(raw_result.get("schedule_hash") == SCHEDULE_HASH, "schedule hash drifted")
    _require(raw_result.get("expected_runs") == 3, "expected run count drifted")
    _require(raw_result.get("completed_runs") == 3, "completed run count drifted")
    _require(raw_result.get("not_started_runs") == 0, "not-started run count drifted")
    _require(raw_result.get("halt_reason") is None, "campaign halt reason drifted")
    _require(raw_result.get("actual_model_cost_usd") == 0.9374115, "cost drifted")
    _require(
        raw_result.get("campaign_journal", {}).get("last_event_hash_before_completion")
        == journal["last_event_hash_before_completion"],
        "raw result journal predecessor drifted",
    )

    _require(plan.get("execution_hash") == EXECUTION_HASH, "plan execution hash drifted")
    _require(plan.get("suite_hash") == SUITE_HASH, "plan suite hash drifted")
    _require(plan.get("schedule_hash") == SCHEDULE_HASH, "plan schedule hash drifted")
    _require(
        sha256_text(canonical_json(plan)) == PLAN_CANONICAL_HASH, "plan canonical hash drifted"
    )
    _require(plan.get("ready") is True and plan.get("blockers") == [], "approved plan drifted")
    _require(
        plan.get("environment", {}).get("git")
        == {"available": True, "commit": SOURCE_HARNESS_COMMIT, "clean": True},
        "source environment drifted",
    )
    approval = plan.get("approval", {})
    _require(approval.get("invocation_approve_live_cost") is True, "approval flag drifted")
    _require(
        approval.get("invocation_approved_execution_hash") == EXECUTION_HASH,
        "approved hash drifted",
    )
    _require(approval.get("matches_execution_hash") is True, "approval match drifted")

    gate = raw_result.get("completion_gate", {})
    expected_gate_values = {
        "schema_version": "generic-high-headroom-readiness-gate-v1",
        "gate_id": "d094-generic-high-headroom-readiness",
        "passed": True,
        "expected_runs": 3,
        "terminal_runs": 3,
        "qualified_runs": 3,
        "evaluator_reached_runs": 3,
        "official_evaluator_runs": 3,
        "accepted_submission_runs": 3,
        "prompt_telemetry_complete_runs": 3,
        "usage_reconciled_runs": 3,
        "persisted_result_verified_runs": 3,
        "qualification_recomputed_runs": 3,
        "model_or_tool_call_budget_block_runs": 0,
        "terminal_loop_failure_runs": 0,
        "budget_terminal_runs": 0,
        "task_successes": 0,
        "task_success_required": False,
        "comparison_denominator_eligible": False,
        "memory_admission_unlocked": False,
    }
    _require(
        all(gate.get(key) == value for key, value in expected_gate_values.items()),
        "completion gate drifted",
    )
    for key in ("infrastructure_errors", "qualification_errors", "diagnostic_errors"):
        _require(raw_result.get(key) == 0, f"{key} drifted")

    raw_rows = raw_result.get("runs")
    _require(isinstance(raw_rows, list) and len(raw_rows) == 3, "run rows drifted")
    portable_rows: list[dict[str, Any]] = []
    raw_artifacts: list[dict[str, Any]] = [
        {"role": role, **descriptor} for role, descriptor in RUNTIME_FILES.items()
    ]
    aggregate_usage = Counter()
    aggregate_trace = Counter()

    for expected, row in zip(RUNS, raw_rows, strict=True):
        run_id = expected["run_id"]
        _require(row.get("order") == expected["order"], f"order drifted for {run_id}")
        _require(row.get("task_id") == expected["task_id"], f"task drifted for {run_id}")
        _require(row.get("run_id") == run_id, f"run id drifted for {run_id}")
        _require(row.get("attempt_status") == "terminal", f"terminal status drifted for {run_id}")

        descriptors = {role: _run_file_descriptor(expected, role) for role in expected["files"]}
        for descriptor in descriptors.values():
            _read_exact(repo_root, descriptor, label=f"{run_id} {descriptor['role']}")
            raw_artifacts.append(descriptor)
        durable_result = _load_json(
            (repo_root / descriptors["result"]["path"]).read_bytes(),
            label=f"{run_id} durable result",
        )
        _require(
            canonical_json(durable_result) == canonical_json(row.get("result")),
            f"durable result projection drifted for {run_id}",
        )
        manifest = _load_json(
            (repo_root / descriptors["manifest"]["path"]).read_bytes(),
            label=f"{run_id} manifest",
        )
        _require(
            manifest.get("harness_git_commit") == SOURCE_HARNESS_COMMIT,
            f"manifest commit drifted for {run_id}",
        )
        _require(
            manifest.get("experiment", {}).get("execution_hash") == EXECUTION_HASH,
            f"manifest execution hash drifted for {run_id}",
        )
        receipt = _load_json(
            (repo_root / descriptors["evaluation-receipt"]["path"]).read_bytes(),
            label=f"{run_id} evaluation receipt",
        )
        _require(receipt.get("run_id") == run_id, f"evaluation receipt drifted for {run_id}")
        for role in ("manifest", "provenance", "result"):
            _require(
                receipt.get("file_hashes", {}).get(f"{role}.json") == descriptors[role]["sha256"],
                f"evaluation receipt file hash drifted for {run_id}",
            )
        _require(
            receipt.get("worktree_diff_hash") == descriptors["submitted-patch"]["sha256"],
            f"submitted patch receipt drifted for {run_id}",
        )

        result = row.get("result", {})
        _require(
            canonical_json(row.get("usage")) == canonical_json(result.get("usage")),
            f"row/result usage drifted for {run_id}",
        )
        verdicts = result.get("verdicts", {})
        _require(
            result.get("agent_submission_status") == "completed",
            f"submission status drifted for {run_id}",
        )
        _require(
            result.get("evaluation_status") == "completed",
            f"evaluation status drifted for {run_id}",
        )
        _require(result.get("official") is True, f"official evaluator drifted for {run_id}")
        _require(result.get("outcome_kind") == "task_failure", f"outcome drifted for {run_id}")
        _require(result.get("terminal_error") is None, f"terminal error drifted for {run_id}")
        _require(
            verdicts
            == {
                "hidden_tests": "fail",
                "regression_tests": "pass",
                "scope_policy": "pass",
                "safety_policy": "pass",
            },
            f"verdict projection drifted for {run_id}",
        )

        usage = row.get("usage", {})
        _require(
            _usage_cost(usage) == Decimal(str(usage.get("model_cost_usd"))),
            f"usage cost drifted for {run_id}",
        )
        total_tokens = usage["input_tokens"] + usage["output_tokens"]
        for key in (
            "input_tokens",
            "cached_input_tokens",
            "cache_write_input_tokens",
            "output_tokens",
            "reasoning_output_tokens",
            "model_calls",
            "input_token_count_calls",
            "tool_calls",
            "wall_clock_ms",
        ):
            aggregate_usage[key] += usage[key]
        aggregate_usage["total_tokens"] += total_tokens
        aggregate_usage["model_cost_usd_nanos"] += int(
            Decimal(str(usage["model_cost_usd"])) * Decimal(1_000_000_000)
        )

        qualification = _load_json(
            (repo_root / descriptors["qualification"]["path"]).read_bytes(),
            label=f"{run_id} qualification",
        )
        checks = qualification.get("checks")
        _require(
            isinstance(checks, list) and len(checks) == 28,
            f"qualification checks drifted for {run_id}",
        )
        _require(
            all(check.get("passed") is True for check in checks),
            f"qualification failure drifted for {run_id}",
        )
        _require(
            qualification.get("qualified") is True, f"qualification status drifted for {run_id}"
        )
        _require(
            qualification.get("qualification_hash") == expected["qualification_hash"],
            f"qualification hash drifted for {run_id}",
        )
        _require(
            qualification.get("source_evidence_hash") == expected["source_evidence_hash"],
            f"source evidence hash drifted for {run_id}",
        )
        summary = row.get("qualification", {})
        _require(
            summary.get("qualification_hash") == expected["qualification_hash"],
            f"qualification summary drifted for {run_id}",
        )
        _require(
            summary.get("read_only_recomputation", {}).get("matched") is True,
            f"qualification recomputation drifted for {run_id}",
        )
        _require(
            summary.get("read_only_recomputation", {}).get("qualification_hash")
            == expected["qualification_hash"]
            and summary.get("read_only_recomputation", {}).get(
                "recomputed_qualification_hash"
            )
            == expected["qualification_hash"],
            f"qualification recomputation hash drifted for {run_id}",
        )
        readiness_checks = summary.get("readiness_checks", {})
        expected_readiness_check_ids = {
            "submission_lifecycle",
            "prompt_token_integrity",
            "usage_reconciliation",
            "persisted_result",
            "disabled_call_guard_contract",
        }
        _require(
            set(readiness_checks) == expected_readiness_check_ids,
            f"readiness check projection drifted for {run_id}",
        )
        _require(
            all(
                check
                == {
                    "schema_version": "qualification-gate-check-projection-v1",
                    "check_id": check_id,
                    "check_count": 1,
                    "passed": True,
                }
                for check_id, check in readiness_checks.items()
            ),
            f"readiness check evidence drifted for {run_id}",
        )
        _require(
            summary.get("model_or_tool_call_budget_blocks", {}).get("event_sequences") == [],
            f"call-budget block drifted for {run_id}",
        )

        pressure = row.get("budget_pressure", {})
        _require(
            pressure.get("binding_dimension") == "none", f"budget binding drifted for {run_id}"
        )
        _require(
            pressure.get("exact_request", {}).get("blocked") is False,
            f"exact request block drifted for {run_id}",
        )
        trace = _trace_projection(runtime_root / "state.sqlite3", run_id, usage)
        aggregate_trace.update(
            {
                "events": trace["event_count"],
                "checkpoints": trace["checkpoint_count"],
                "worker_claims": trace["worker_claim_count"],
                "reclaimed_worker_claims": trace["reclaimed_worker_claim_count"],
                "completed_model_responses": trace["completed_model_responses"],
                "exact_input_token_matches": trace["exact_input_token_matches"],
                "exact_total_token_matches": trace["exact_total_token_matches"],
                "truncation_disabled_responses": trace["truncation_disabled_responses"],
                "store_false_responses": trace["store_false_responses"],
                "previous_response_dependency_count": trace["previous_response_dependency_count"],
            }
        )

        portable_rows.append(
            {
                "order": row["order"],
                "schedule_row_id": row["schedule_row_id"],
                "task_id": row["task_id"],
                "dataset_role": row["dataset_role"],
                "condition": row["condition"],
                "repetition": row["repetition"],
                "run_id": run_id,
                "result": {
                    "attempt_status": row["attempt_status"],
                    "agent_submission_status": result["agent_submission_status"],
                    "evaluation_status": result["evaluation_status"],
                    "official": result["official"],
                    "outcome_kind": result["outcome_kind"],
                    "scope_compliant_success": result["scope_compliant_success"],
                    "verdicts": verdicts,
                    "terminal_error": result["terminal_error"],
                },
                "usage": {**usage, "total_tokens": total_tokens},
                "qualification": {
                    "qualified": True,
                    "trace_integrity_passed": qualification["trace_integrity_passed"],
                    "leakage_scan_passed": qualification["leakage_scan_passed"],
                    "evaluation_reached": qualification["evaluation_reached"],
                    "passed_checks": 28,
                    "total_checks": 28,
                    "qualification_hash": expected["qualification_hash"],
                    "source_evidence_hash": expected["source_evidence_hash"],
                    "read_only_recomputation_matched": True,
                    "model_or_tool_call_budget_block_sequences": [],
                },
                "budget_pressure": {
                    "configured_limits": pressure["configured_limits"],
                    "observed_usage": pressure["observed_usage"],
                    "headroom": pressure["headroom"],
                    "binding_dimension": pressure["binding_dimension"],
                    "binding_reason": pressure["binding_reason"],
                    "exact_request_blocked": False,
                },
                "trace": trace,
            }
        )

    aggregate_usage_payload = {
        key: aggregate_usage[key]
        for key in (
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
    }
    aggregate_usage_payload["model_cost_usd"] = float(
        Decimal(aggregate_usage["model_cost_usd_nanos"]) / Decimal(1_000_000_000)
    )
    _require(
        aggregate_usage_payload
        == {
            "input_tokens": 957_052,
            "cached_input_tokens": 0,
            "cache_write_input_tokens": 0,
            "output_tokens": 48_805,
            "reasoning_output_tokens": 43_265,
            "total_tokens": 1_005_857,
            "model_calls": 63,
            "input_token_count_calls": 63,
            "tool_calls": 119,
            "wall_clock_ms": 446_060,
            "model_cost_usd": 0.9374115,
        },
        "aggregate usage drifted",
    )
    aggregate_trace_payload = dict(aggregate_trace)
    _require(
        aggregate_trace_payload
        == {
            "events": 552,
            "checkpoints": 122,
            "worker_claims": 3,
            "reclaimed_worker_claims": 0,
            "completed_model_responses": 63,
            "exact_input_token_matches": 63,
            "exact_total_token_matches": 63,
            "truncation_disabled_responses": 63,
            "store_false_responses": 63,
            "previous_response_dependency_count": 0,
        },
        "aggregate trace drifted",
    )

    runtime_contract = plan["runtime_contract"]
    body = {
        "milestone": "D-095",
        "evidence_kind": "measured-live-high-headroom-readiness-result-seal",
        "recorded_at": raw_result["created_at"],
        "sealed_at": sealed_at,
        "source_contract": {
            "harness_git_commit": SOURCE_HARNESS_COMMIT,
            "suite": suite_descriptor,
            "d094_source_gate": {
                **source_gate_descriptor,
                "semantic_body_hash": source_gate["semantic_body_hash"],
                "gate_id": source_gate["gate_id"],
            },
            "execution_plan": {
                **RUNTIME_FILES["execution-plan"],
                "canonical_hash": PLAN_CANONICAL_HASH,
            },
        },
        "experiment": {
            "experiment_id": EXPERIMENT_ID,
            "purpose": raw_result["purpose"],
            "execution_hash": EXECUTION_HASH,
            "suite_hash": SUITE_HASH,
            "schedule_hash": SCHEDULE_HASH,
            "schedule_seed": raw_result["schedule_seed"],
            "expected_runs": 3,
            "completed_runs": 3,
            "conditions": ["no_memory"],
            "repetitions": 1,
            "approved_maximum_cost_usd": 41.0,
            "one_use_execution_hash_consumed": True,
        },
        "environment": {
            "dataset": raw_result["dataset"],
            "runtime_contract": runtime_contract,
            "openai_sdk": plan["environment"]["openai_sdk"],
            "docker_images": plan["environment"]["docker"]["images"],
            "credential_value_embedded": False,
            "custom_openai_base_url_used": False,
        },
        "original_campaign_result": {
            "raw_result": RUNTIME_FILES["raw-result"],
            "completion_gate": gate,
            "infrastructure_errors": 0,
            "qualification_errors": 0,
            "diagnostic_errors": 0,
            "not_started_runs": 0,
            "halt_reason": None,
            "actual_list_price_model_cost_usd": raw_result["actual_model_cost_usd"],
        },
        "aggregate_usage": aggregate_usage_payload,
        "aggregate_trace": aggregate_trace_payload,
        "runs": portable_rows,
        "journal_seal": journal,
        "raw_local_artifacts": raw_artifacts,
        "portable_contract": {
            "self_contained_without_local_runtime_artifacts": True,
            "private_spec_embedded": False,
            "hidden_assertion_embedded": False,
            "reference_patch_embedded": False,
            "submitted_patch_body_embedded": False,
            "model_or_tool_body_embedded": False,
            "api_key_or_authorization_embedded": False,
            "raw_artifact_paths_are_non_authoritative_pointers": True,
            "semantic_body_is_content_addressed": True,
        },
        "evidence_validation": {
            "raw_result_exact_hash_verified": True,
            "journal_hash_chain_verified": True,
            "execution_plan_exact_hash_verified": True,
            "run_result_and_evaluator_receipt_hashes_verified": True,
            "qualification_files_verified": 3,
            "qualification_checks_passed": 84,
            "read_only_recomputation_matches": 3,
            "prompt_usage_reconciliation_passed": True,
            "leak_safe_projection_only": True,
        },
        "analysis": {
            "workflow_readiness_disposition": "passed",
            "task_correctness_disposition": "zero-of-three-hidden-acceptance",
            "task_successes": 0,
            "task_failures": 3,
            "hidden_acceptance_successes": 0,
            "regression_scope_safety_successes": 3,
            "budget_confound_observed": False,
            "interpretation": "exact-tuple-workflow-readiness-calibration-only",
            "three_million_tokens_generally_sufficient": False,
        },
        "claims_boundary": {
            "live_provider_execution_observed": True,
            "provider_model_calls_observed": 63,
            "official_evaluator_runs_observed": 3,
            "workflow_readiness_gate_passed": True,
            "task_successes": 0,
            "task_success_is_readiness_requirement": False,
            "calibration_only": True,
            "no_memory_performance_baseline_established": False,
            "success_rate_estimated": False,
            "comparison_denominator_eligible": False,
            "comparison_resource_policy_frozen": False,
            "memory_review_authorized": False,
            "memory_admission_unlocked": False,
            "memory_index_frozen": False,
            "core_campaign_unlocked": False,
            "analysis_ready": False,
            "actual_invoice_or_free_tier_treatment_claimed": False,
            "hidden_driven_tuning_authorized": False,
            "automatic_rerun_authorized": False,
            "original_result_journal_run_or_qualification_modified": False,
            "seal_provider_calls": 0,
            "seal_evaluator_calls": 0,
            "seal_added_model_cost_usd": 0.0,
        },
        "next_gate": {
            "decision_required": (
                "separate-condition-neutral-resource-policy-and-baseline-admission"
            ),
            "current_experiment_hard_consumed": True,
            "current_execution_hash_reusable": False,
            "automatic_successor_authorized": False,
            "hidden_outcome_driven_tuning_authorized": False,
            "new_live_execution_authorized": False,
            "resource_policy_freeze_completed": False,
            "no_memory_baseline_admitted": False,
            "memory_review_or_index_unlocked": False,
            "core_campaign_unlocked": False,
        },
    }
    body_hash = sha256_json(body)
    return {
        "schema_version": "generic-high-headroom-readiness-d095-evidence-v1",
        "report_id": f"d095_{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": body,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the content-addressed D-095 measured-result seal."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    parser.add_argument("--runtime-root", type=Path)
    parser.add_argument("--sealed-at", default=SEALED_AT)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    runtime_root = args.runtime_root.resolve() if args.runtime_root else repo_root / ".patchloop"
    payload = build_seal(
        repo_root=repo_root,
        runtime_root=runtime_root,
        sealed_at=args.sealed_at,
    )
    rendered = (
        json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        if args.compact
        else json.dumps(payload, ensure_ascii=False, indent=2)
    )
    if args.output is None:
        print(rendered)
    else:
        output = args.output
        if not output.is_absolute():
            output = repo_root / output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
