from __future__ import annotations

import argparse
import gc
import json
import shutil
import sqlite3
import tempfile
from collections import Counter
from decimal import Decimal
from pathlib import Path
from typing import Any

from patchloop.evals.qualification import load_trace_qualification, qualify_run
from patchloop.evals.runner import (
    _d097_completion_gate,
    _full_schedule_cost_journal_evidence,
    _load_d097_durable_usage_evidence,
)
from patchloop.util import canonical_json, sha256_bytes, sha256_json, sha256_text

SEALED_AT = "2026-08-05T06:58:06Z"
EXPERIMENT_ID = "dev-no-memory-condition-neutral-3000k-20260805-r1"
SOURCE_HARNESS_COMMIT = "67fa85e47c5cf39c0ee03ad69d9d31f9fdd11ac3"
EXECUTION_HASH = "sha256:1a5aaccc4f95f71d285e0e0a9c8ccb27f82e235fbff465ef30f095401fde25f4"
SUITE_HASH = "sha256:e32000918e96e6773986e99d5aa9dc29a9a91fc4f0a89f5e63adde69f78267ed"
RUNTIME_SCHEDULE_HASH = "sha256:2ecbf257117481bfa31d62454221af243cc541470a91abeefdcae1f0912a552d"
SOURCE_SCHEDULE_IDENTITY_HASH = (
    "sha256:e399114a6ea516821a30104a612f7222c0caf3f88def7b5d7472d15f7cc4c27b"
)
SOURCE_EXPANDED_ORDER_HASH = (
    "sha256:dff4f38db99bcbc878e917a6c76e10a6c244701d2a8eb5ea4b43daf427a305ba"
)
PLAN_CANONICAL_HASH = "sha256:36b22999f9633a156cc5d7dd5cff87bbe44eb2485b09b47419e5f39c49b25529"
COST_CONTROL_HASH = "sha256:fc5cd14ddea7dd348094c8e71f16eea9f6e92de16ffdb738e61a0d6f417acff5"
RAW_RESULT_HASH = "sha256:becb176561f5940073469d530a8db0fdb8d19f292bdf2d4c670a79c7aa19f99a"
JOURNAL_FILE_HASH = "sha256:9cf4001098a601e97e01c30238aba427350cc96cbb472a7b757dd8dce8744f98"
FINAL_JOURNAL_EVENT_HASH = "sha256:990f129d88dd59ee136db032cd01029b516c65659dcc1362f9b6470d15db6b40"
PENULTIMATE_JOURNAL_EVENT_HASH = (
    "sha256:cd92011a4eb99ac84091b241f72e964b05ba98b2e9df15c8cad9bb8ecdc21111"
)

SOURCE_FILES = {
    "suite": {
        "path": f"experiments/{EXPERIMENT_ID}.yaml",
        "bytes": 2_741,
        "sha256": ("sha256:7b3c217388e86a2760694e98031b7ac974c8c450075e3433ee977e35b344abb0"),
    },
    "d096-policy": {
        "path": (
            "reports/live-pilot/artifacts/"
            "d096-condition-neutral-resource-policy-baseline-admission.json"
        ),
        "bytes": 19_031,
        "sha256": ("sha256:5c032cff1045a39d1d8d9757205a920b1cd1cfd948c7c4e3e5b526ae6744661d"),
        "semantic_body_hash": (
            "sha256:2e9360d92db5224d181fe8f18254da3850f324b33b24f3833633589085e3b75d"
        ),
    },
    "d097-source-gate": {
        "path": ("reports/live-pilot/artifacts/d097-condition-neutral-baseline-source-gate.json"),
        "bytes": 21_029,
        "sha256": ("sha256:21ed073ad1fbe1985e7a46cabebbfdc836baa303c4434e0777152c1d2d88a777"),
        "semantic_body_hash": (
            "sha256:05d952065136a45914e2fb3c44edcbb553732c9f33484c5412b9135062c6481b"
        ),
    },
}

RUNTIME_FILES = {
    "raw-result": {
        "path": f".patchloop/experiments/{EXPERIMENT_ID}.json",
        "bytes": 190_558,
        "sha256": RAW_RESULT_HASH,
    },
    "campaign-journal": {
        "path": f".patchloop/experiments/journals/{EXPERIMENT_ID}.jsonl",
        "bytes": 58_203,
        "sha256": JOURNAL_FILE_HASH,
    },
    "execution-plan": {
        "path": (
            ".patchloop/experiments/plans/"
            "1a5aaccc4f95f71d285e0e0a9c8ccb27f82e235fbff465ef30f095401fde25f4.json"
        ),
        "bytes": 25_769,
        "sha256": ("sha256:bd2eccea42111df462f27cfdcc5a346e53deec57ebc57da9f552d433675c93f5"),
    },
}

RUN_IDS = (
    "run_575da4ead3334551",
    "run_74364afdc3d94f9c",
    "run_7ecb4b2489c34982",
    "run_5ffc2e1c58784e17",
    "run_3fe55fd3847d4a4d",
    "run_88f96fae3d2442e6",
    "run_3dc602aab8964d77",
    "run_59aac91defac456b",
    "run_cc179262fa664600",
    "run_ac3ae1a7009a4e8b",
    "run_d5c2e22b485a4578",
    "run_92bf10d2a6b14601",
)
BUDGET_RUN_ID = "run_7ecb4b2489c34982"


class D098BuildError(RuntimeError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise D098BuildError(message)


def _read_exact(root: Path, descriptor: dict[str, Any], *, label: str) -> bytes:
    path = root / descriptor["path"]
    try:
        content = path.read_bytes()
    except OSError as exc:
        raise D098BuildError(f"{label} is unavailable") from exc
    _require(len(content) == descriptor["bytes"], f"{label} byte count drifted")
    _require(sha256_bytes(content) == descriptor["sha256"], f"{label} hash drifted")
    return content


def _load_json(content: bytes, *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise D098BuildError(f"{label} is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise D098BuildError(f"{label} must be an object")
    return payload


def _descriptor(
    repo_root: Path,
    path: str,
    *,
    role: str,
    run_id: str | None = None,
) -> dict[str, Any]:
    absolute = repo_root / path
    try:
        content = absolute.read_bytes()
    except OSError as exc:
        raise D098BuildError(f"{role} is unavailable") from exc
    result: dict[str, Any] = {
        "role": role,
        "path": path,
        "bytes": len(content),
        "sha256": sha256_bytes(content),
    }
    if run_id is not None:
        result["run_id"] = run_id
    return result


def _usage_cost_nanos(usage: dict[str, Any]) -> int:
    input_tokens = usage.get("input_tokens")
    cached_input_tokens = usage.get("cached_input_tokens")
    output_tokens = usage.get("output_tokens")
    _require(type(input_tokens) is int and input_tokens >= 0, "input token usage drifted")
    _require(
        type(cached_input_tokens) is int and 0 <= cached_input_tokens <= input_tokens,
        "cached input usage drifted",
    )
    _require(type(output_tokens) is int and output_tokens >= 0, "output usage drifted")
    uncached_input_tokens = input_tokens - cached_input_tokens
    cost = (
        Decimal(uncached_input_tokens) * Decimal("0.75")
        + Decimal(cached_input_tokens) * Decimal("0.075")
        + Decimal(output_tokens) * Decimal("4.5")
    ) / Decimal(1_000_000)
    return int(cost * Decimal(1_000_000_000))


def _journal_projection(content: bytes) -> dict[str, Any]:
    try:
        events = [json.loads(line) for line in content.decode("utf-8").splitlines()]
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise D098BuildError("campaign journal is invalid") from exc
    _require(len(events) == 39, "campaign journal event count drifted")
    previous_hash: str | None = None
    for sequence, event in enumerate(events, start=1):
        _require(isinstance(event, dict), "campaign journal event must be an object")
        body = {key: value for key, value in event.items() if key != "event_hash"}
        _require(event.get("sequence") == sequence, "campaign journal sequence drifted")
        _require(
            event.get("previous_event_hash") == previous_hash,
            "campaign journal predecessor drifted",
        )
        _require(
            event.get("event_hash") == sha256_text(canonical_json(body)),
            "campaign journal hash chain drifted",
        )
        previous_hash = event["event_hash"]
    expected_types = ["CampaignStarted", "FullScheduleCostReserved"]
    for _ in range(12):
        expected_types.extend(["RunStarted", "RunTerminal", "RunCostSettled"])
    expected_types.append("CampaignCompleted")
    _require(
        [event.get("event_type") for event in events] == expected_types,
        "campaign journal event order drifted",
    )
    final = events[-1]
    _require(
        final.get("previous_event_hash") == PENULTIMATE_JOURNAL_EVENT_HASH,
        "campaign journal penultimate hash drifted",
    )
    _require(
        final.get("event_hash") == FINAL_JOURNAL_EVENT_HASH,
        "campaign journal final hash drifted",
    )
    _require(
        final.get("payload", {}).get("result_hash") == RAW_RESULT_HASH,
        "campaign journal result hash drifted",
    )
    return {
        "path": RUNTIME_FILES["campaign-journal"]["path"],
        "bytes": RUNTIME_FILES["campaign-journal"]["bytes"],
        "file_sha256": RUNTIME_FILES["campaign-journal"]["sha256"],
        "event_count": len(events),
        "event_type_counts": dict(sorted(Counter(expected_types).items())),
        "last_event_hash_before_completion": final["previous_event_hash"],
        "final_event_hash": final["event_hash"],
        "result_hash": final["payload"]["result_hash"],
    }


def _trace_projection(
    state_path: Path,
    run_id: str,
    usage: dict[str, Any],
    *,
    budget_branch: bool,
) -> dict[str, Any]:
    if not state_path.is_file():
        raise D098BuildError("durable state database is unavailable")
    uri = f"file:{state_path.as_posix()}?mode=ro"
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
        raise D098BuildError("durable trace could not be read") from exc
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
    blocked_events = [event for event in events if event["type"] == "ModelGenerationBlocked"]
    expected_blocked = 1 if budget_branch else 0
    _require(
        len(blocked_events) == expected_blocked,
        f"model generation block count drifted for {run_id}",
    )
    _require(
        len(model_events) == usage.get("model_calls"),
        f"model call count drifted for {run_id}",
    )
    _require(
        counts.get("ToolCalled", 0) == usage.get("tool_calls"),
        f"tool call count drifted for {run_id}",
    )
    _require(
        usage.get("input_token_count_calls") == len(model_events) + len(blocked_events),
        f"input token pre-count relation drifted for {run_id}",
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
            sum((event["payload"].get(key) or 0) for event in model_events) == usage.get(key),
            f"{key} event sum drifted for {run_id}",
        )
    _require(
        sum((event["payload"].get("total_tokens") or 0) for event in model_events)
        == usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
        f"total token event sum drifted for {run_id}",
    )
    if blocked_events:
        blocked_sequence = blocked_events[0]["sequence"]
        _require(
            all(event["sequence"] < blocked_sequence for event in model_events),
            f"provider response occurred after budget block for {run_id}",
        )
    return {
        "event_count": len(events),
        "checkpoint_count": checkpoint_count,
        "worker_claim_count": len(worker_rows),
        "reclaimed_worker_claim_count": sum(bool(row[0]) for row in worker_rows),
        "completed_model_responses": len(model_events),
        "input_token_precount_calls": usage["input_token_count_calls"],
        "pre_provider_generation_blocks": len(blocked_events),
        "exact_input_token_matches": len(model_events),
        "exact_total_token_matches": len(model_events),
        "truncation_disabled_responses": len(model_events),
        "store_false_responses": len(model_events),
        "previous_response_dependency_count": 0,
        "submission_accepted_count": counts.get("SubmissionAccepted", 0),
        "run_completed_count": counts.get("RunCompleted", 0),
        "run_failed_count": counts.get("RunFailed", 0),
        "memory_retrieval_count": counts.get("MemoryRetrieved", 0),
    }


def _state_bundle_fingerprint(state_path: Path) -> dict[str, dict[str, Any] | None]:
    fingerprint: dict[str, dict[str, Any] | None] = {}
    for suffix in ("", "-wal", "-shm"):
        path = Path(f"{state_path}{suffix}")
        if not path.exists():
            fingerprint[suffix or "database"] = None
            continue
        stat = path.stat()
        fingerprint[suffix or "database"] = {
            "bytes": stat.st_size,
            "mtime_ns": stat.st_mtime_ns,
            "sha256": sha256_bytes(path.read_bytes()),
        }
    return fingerprint


def _copy_state_snapshot(state_path: Path, destination: Path) -> Path:
    _require(state_path.is_file(), "durable state database is unavailable")
    snapshot_path = destination / state_path.name
    shutil.copy2(state_path, snapshot_path)
    wal_path = Path(f"{state_path}-wal")
    if wal_path.is_file():
        shutil.copy2(wal_path, Path(f"{snapshot_path}-wal"))
    return snapshot_path


def _durable_run_documents(
    state_path: Path,
    run_id: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    uri = f"file:{state_path.as_posix()}?mode=ro"
    try:
        connection = sqlite3.connect(uri, uri=True)
        connection.execute("PRAGMA query_only=ON")
        row = connection.execute(
            "SELECT manifest_json, result_json FROM runs WHERE run_id = ?",
            (run_id,),
        ).fetchone()
    except sqlite3.Error as exc:
        raise D098BuildError(f"durable run documents are unavailable for {run_id}") from exc
    finally:
        if "connection" in locals():
            connection.close()
    _require(row is not None, f"durable run row is unavailable for {run_id}")
    manifest = _load_json(row[0].encode("utf-8"), label=f"{run_id} durable manifest")
    _require(row[1] is not None, f"durable result is unavailable for {run_id}")
    result = _load_json(row[1].encode("utf-8"), label=f"{run_id} durable result")
    return manifest, result


def _safe_budget_projection(row: dict[str, Any]) -> dict[str, Any]:
    pressure = row.get("budget_pressure")
    _require(isinstance(pressure, dict), "budget pressure is missing")
    exact = pressure.get("exact_request")
    _require(isinstance(exact, dict), "exact request budget evidence is missing")
    return {
        "configured_limits": pressure.get("configured_limits"),
        "observed_usage": pressure.get("observed_usage"),
        "headroom": pressure.get("headroom"),
        "binding_dimension": pressure.get("binding_dimension"),
        "binding_reason": pressure.get("binding_reason"),
        "blocked_tool_count": pressure.get("blocked_tool_count"),
        "token_tail_triggered": (pressure.get("token_tail") or {}).get("triggered"),
        "exact_request": {
            "blocked": exact.get("blocked"),
            "sequence": exact.get("sequence"),
            "requested_input_tokens": exact.get("requested_input_tokens"),
            "max_output_tokens": exact.get("max_output_tokens"),
            "required_tokens": exact.get("required_tokens"),
            "remaining_tokens": exact.get("remaining_tokens"),
            "deficit_tokens": exact.get("deficit_tokens"),
            "minimum_total_budget_same_prefix": exact.get("minimum_total_budget_same_prefix"),
        },
    }


def _build_seal_from_snapshot(
    *,
    repo_root: Path,
    runtime_root: Path,
    state_path: Path,
    sealed_at: str,
) -> dict[str, Any]:
    _require(
        runtime_root.resolve() == (repo_root / ".patchloop").resolve(),
        "runtime root must be the exact repository runtime",
    )
    source_payloads: dict[str, dict[str, Any]] = {}
    for role, descriptor in SOURCE_FILES.items():
        content = _read_exact(repo_root, descriptor, label=role)
        if role != "suite":
            payload = _load_json(content, label=role)
            _require(
                payload.get("semantic_body_hash") == descriptor["semantic_body_hash"],
                f"{role} semantic hash drifted",
            )
            source_payloads[role] = payload

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
    journal_projection = _journal_projection(journal_content)

    _require(raw_result.get("experiment_id") == EXPERIMENT_ID, "experiment id drifted")
    _require(raw_result.get("execution_hash") == EXECUTION_HASH, "execution hash drifted")
    _require(raw_result.get("suite_hash") == SUITE_HASH, "suite hash drifted")
    _require(
        raw_result.get("schedule_hash") == RUNTIME_SCHEDULE_HASH,
        "runtime schedule hash drifted",
    )
    _require(raw_result.get("expected_runs") == 12, "expected run count drifted")
    _require(raw_result.get("completed_runs") == 12, "completed run count drifted")
    _require(raw_result.get("not_started_runs") == 0, "not-started count drifted")
    _require(raw_result.get("halt_reason") is None, "campaign halt reason drifted")
    _require(
        raw_result.get("actual_model_cost_usd") == 11.838408,
        "campaign list-price cost drifted",
    )
    for key in ("infrastructure_errors", "qualification_errors", "diagnostic_errors"):
        _require(raw_result.get(key) == 0, f"{key} drifted")

    _require(plan.get("experiment_id") == EXPERIMENT_ID, "plan experiment drifted")
    _require(plan.get("execution_hash") == EXECUTION_HASH, "plan execution hash drifted")
    _require(plan.get("suite_hash") == SUITE_HASH, "plan suite hash drifted")
    _require(
        plan.get("schedule_hash") == RUNTIME_SCHEDULE_HASH,
        "plan schedule hash drifted",
    )
    _require(
        sha256_text(canonical_json(plan)) == PLAN_CANONICAL_HASH,
        "plan canonical hash drifted",
    )
    _require(plan.get("ready") is True and plan.get("blockers") == [], "plan drifted")
    _require(
        plan.get("environment", {}).get("git")
        == {"available": True, "commit": SOURCE_HARNESS_COMMIT, "clean": True},
        "source environment drifted",
    )
    approval = plan.get("approval") or {}
    _require(approval.get("invocation_approve_live_cost") is True, "approval drifted")
    _require(
        approval.get("invocation_approved_execution_hash") == EXECUTION_HASH
        and approval.get("matches_execution_hash") is True,
        "approved execution hash drifted",
    )
    runtime_contract = plan.get("runtime_contract") or {}
    _require(
        runtime_contract.get("schema_version")
        == "condition-neutral-comparison-runtime-contract-v2",
        "runtime contract schema drifted",
    )
    _require(
        runtime_contract.get("harness_git_commit") == SOURCE_HARNESS_COMMIT,
        "runtime contract commit drifted",
    )
    _require(
        (plan.get("campaign_cost_control") or {}).get("content_hash") == COST_CONTROL_HASH,
        "cost control hash drifted",
    )
    schedule = plan.get("schedule")
    _require(isinstance(schedule, list) and len(schedule) == 12, "plan schedule drifted")
    _require(
        sha256_text(canonical_json(schedule)) == RUNTIME_SCHEDULE_HASH,
        "plan schedule projection drifted",
    )

    cost_qualification = _full_schedule_cost_journal_evidence(
        repo_root / RUNTIME_FILES["campaign-journal"]["path"],
        plan["campaign_cost_control"],
        run_root=runtime_root,
        expected_execution_hash=EXECUTION_HASH,
        expected_execution_plan_hash=PLAN_CANONICAL_HASH,
        expected_schedule=schedule,
        durable_usage_resolver=lambda run_id, schedule_row_id, root: (
            _load_d097_durable_usage_evidence(
                run_id,
                schedule_row_id,
                root,
                state_path=state_path,
            )
        ),
    )
    _require(
        canonical_json(cost_qualification)
        == canonical_json(raw_result.get("campaign_cost_qualification")),
        "campaign cost qualification drifted",
    )
    gate = _d097_completion_gate(
        raw_result.get("runs") or [],
        expected_execution_hash=EXECUTION_HASH,
        expected_schedule=schedule,
        expected_campaign_cost_control_hash=COST_CONTROL_HASH,
        campaign_cost_qualification=cost_qualification,
    )
    _require(
        canonical_json(gate) == canonical_json(raw_result.get("completion_gate")),
        "completion gate recomputation drifted",
    )
    _require(gate.get("passed") is True, "completion gate did not pass")

    rows = raw_result.get("runs")
    _require(isinstance(rows, list) and len(rows) == 12, "run rows drifted")
    _require([row.get("run_id") for row in rows] == list(RUN_IDS), "run order drifted")
    _require(len(set(RUN_IDS)) == 12, "run IDs are not unique")

    raw_artifacts = [{"role": role, **descriptor} for role, descriptor in RUNTIME_FILES.items()]
    portable_rows: list[dict[str, Any]] = []
    memory_candidates: list[dict[str, Any]] = []
    aggregate_usage = Counter()
    aggregate_trace = Counter()
    outcome_counts = Counter()
    task_successes = Counter()
    task_attempts = Counter()

    for expected, row in zip(schedule, rows, strict=True):
        run_id = row.get("run_id")
        _require(isinstance(run_id, str), "run ID is missing")
        _require(
            all(
                row.get(field) == expected.get(field)
                for field in (
                    "order",
                    "schedule_row_id",
                    "task_id",
                    "split",
                    "dataset_role",
                    "condition",
                    "repetition",
                )
            ),
            f"schedule binding drifted for {run_id}",
        )
        _require(row.get("attempt_status") == "terminal", f"terminal status drifted for {run_id}")
        result = row.get("result")
        qualification_summary = row.get("qualification")
        usage = row.get("usage")
        _require(isinstance(result, dict), f"result missing for {run_id}")
        _require(isinstance(qualification_summary, dict), f"qualification missing for {run_id}")
        _require(isinstance(usage, dict), f"usage missing for {run_id}")
        _require(
            canonical_json(usage) == canonical_json(result.get("usage")),
            f"usage projection drifted for {run_id}",
        )
        budget_branch = run_id == BUDGET_RUN_ID
        outcome = result.get("outcome_kind")
        if budget_branch:
            _require(outcome == "agent_failure", "budget row outcome drifted")
            _require(result.get("official") is False, "budget row became official")
            _require(result.get("evaluation_status") == "not_run", "budget row was evaluated")
            terminal_error = result.get("terminal_error") or {}
            details = terminal_error.get("details") or {}
            _require(
                terminal_error.get("type") == "ModelGenerationBudgetError"
                and details.get("reason_code") == "exact_request_budget_exceeded"
                and details.get("generation_started") is False,
                "budget terminal contract drifted",
            )
            terminal_branch = "canonical_pre_provider_budget"
        else:
            _require(
                outcome in {"resolved", "task_failure"}, f"official outcome drifted for {run_id}"
            )
            _require(result.get("official") is True, f"official evaluator drifted for {run_id}")
            _require(
                result.get("agent_submission_status") == "completed"
                and result.get("evaluation_status") == "completed"
                and result.get("terminal_error") is None,
                f"official lifecycle drifted for {run_id}",
            )
            terminal_branch = "official_evaluator"

        run_artifacts: list[dict[str, Any]] = []
        for role in ("manifest", "result", "provenance"):
            descriptor = _descriptor(
                repo_root,
                f".patchloop/artifacts/runs/{run_id}/{role}.json",
                role=role,
                run_id=run_id,
            )
            run_artifacts.append(descriptor)
            raw_artifacts.append(descriptor)
        artifact_payloads = {
            role: _load_json(
                (repo_root / f".patchloop/artifacts/runs/{run_id}/{role}.json").read_bytes(),
                label=f"{run_id} {role}",
            )
            for role in ("manifest", "result", "provenance")
        }
        durable_manifest, durable_result = _durable_run_documents(state_path, run_id)
        _require(
            canonical_json(artifact_payloads["manifest"]) == canonical_json(durable_manifest),
            f"manifest artifact differs from durable state for {run_id}",
        )
        _require(
            canonical_json(artifact_payloads["result"])
            == canonical_json(durable_result)
            == canonical_json(result),
            f"result artifact differs from durable campaign state for {run_id}",
        )
        qualification_descriptor = _descriptor(
            repo_root,
            f".patchloop/qualifications/{run_id}.json",
            role="qualification",
            run_id=run_id,
        )
        run_artifacts.append(qualification_descriptor)
        raw_artifacts.append(qualification_descriptor)

        persisted = load_trace_qualification(run_id, root=runtime_root)
        task_path = repo_root / expected["task"]
        recomputed = qualify_run(
            run_id,
            task_dir=task_path.parent,
            root=runtime_root,
            persist=False,
            state_path=state_path,
        )
        _require(
            canonical_json(persisted) == canonical_json(recomputed),
            f"qualification recomputation drifted for {run_id}",
        )
        _require(
            qualification_summary.get("read_only_recomputation", {}).get("matched") is True,
            f"stored recomputation summary drifted for {run_id}",
        )
        _require(
            persisted.get("qualification_hash") == qualification_summary.get("qualification_hash")
            and persisted.get("source_evidence_hash")
            == qualification_summary.get("source_evidence_hash"),
            f"qualification identity drifted for {run_id}",
        )
        checks = persisted.get("checks")
        expected_check_count = 28 if budget_branch else 29
        _require(
            isinstance(checks, list)
            and len(checks) == expected_check_count
            and all(check.get("passed") is True for check in checks),
            f"qualification checks drifted for {run_id}",
        )

        if budget_branch:
            _require(
                artifact_payloads["provenance"]
                == {
                    "evaluation_reached": False,
                    "outcome_kind": "agent_failure",
                    "error_type": "ModelGenerationBudgetError",
                    "error_code": "MODEL_GENERATION_BUDGET_EXCEEDED",
                },
                "budget provenance artifact drifted",
            )
            _require(
                not (
                    repo_root / f".patchloop/artifacts/runs/{run_id}/evaluation-receipt.json"
                ).exists(),
                "budget row unexpectedly has an evaluator receipt",
            )
            _require(
                not (repo_root / f".patchloop/runs/{run_id}/submitted.patch").exists(),
                "budget row unexpectedly has a submitted patch",
            )
        else:
            receipt_descriptor = _descriptor(
                repo_root,
                f".patchloop/artifacts/runs/{run_id}/evaluation-receipt.json",
                role="evaluation-receipt",
                run_id=run_id,
            )
            patch_descriptor = _descriptor(
                repo_root,
                f".patchloop/runs/{run_id}/submitted.patch",
                role="submitted-patch",
                run_id=run_id,
            )
            run_artifacts.extend([receipt_descriptor, patch_descriptor])
            raw_artifacts.extend([receipt_descriptor, patch_descriptor])
            receipt = _load_json(
                (repo_root / receipt_descriptor["path"]).read_bytes(),
                label=f"{run_id} evaluation receipt",
            )
            by_role = {descriptor["role"]: descriptor for descriptor in run_artifacts}
            _require(receipt.get("run_id") == run_id, f"receipt run ID drifted for {run_id}")
            for role in ("manifest", "result", "provenance"):
                _require(
                    receipt.get("file_hashes", {}).get(f"{role}.json") == by_role[role]["sha256"],
                    f"receipt {role} hash drifted for {run_id}",
                )
            _require(
                receipt.get("worktree_diff_hash") == patch_descriptor["sha256"],
                f"receipt submitted patch hash drifted for {run_id}",
            )

        failure_id = persisted.get("failure_record_id")
        if failure_id is not None:
            failure_descriptor = _descriptor(
                repo_root,
                f".patchloop/failures/dev-train/{failure_id}.json",
                role="failure-record",
                run_id=run_id,
            )
            failure = _load_json(
                (repo_root / failure_descriptor["path"]).read_bytes(),
                label=f"{run_id} failure record",
            )
            _require(
                failure.get("failure_id") == failure_id and failure.get("run_id") == run_id,
                f"failure record binding drifted for {run_id}",
            )
            run_artifacts.append(failure_descriptor)
            raw_artifacts.append(failure_descriptor)

        cost_nanos = _usage_cost_nanos(usage)
        _require(
            cost_nanos == int(Decimal(str(usage.get("model_cost_usd"))) * Decimal(1_000_000_000)),
            f"usage cost drifted for {run_id}",
        )
        trace = _trace_projection(
            state_path,
            run_id,
            usage,
            budget_branch=budget_branch,
        )
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
        aggregate_usage["total_tokens"] += usage["input_tokens"] + usage["output_tokens"]
        aggregate_usage["model_cost_nanos"] += cost_nanos
        for key, value in trace.items():
            if type(value) is int:
                aggregate_trace[key] += value
        outcome_counts[outcome] += 1
        task_attempts[row["task_id"]] += 1
        task_successes[row["task_id"]] += int(result.get("scope_compliant_success") is True)

        memory_candidate = bool(
            terminal_branch == "official_evaluator"
            and outcome == "task_failure"
            and persisted.get("memory_candidate_eligible") is True
        )
        if memory_candidate:
            memory_candidates.append(
                {
                    "run_id": run_id,
                    "task_id": row["task_id"],
                    "repetition": row["repetition"],
                    "failure_record_id": failure_id,
                    "qualification_hash": persisted["qualification_hash"],
                    "source_evidence_hash": persisted["source_evidence_hash"],
                }
            )

        verdicts = result.get("verdicts") or {}
        portable_rows.append(
            {
                "order": row["order"],
                "schedule_row_id": row["schedule_row_id"],
                "task_id": row["task_id"],
                "dataset_role": row["dataset_role"],
                "condition": row["condition"],
                "repetition": row["repetition"],
                "run_id": run_id,
                "terminal_branch": terminal_branch,
                "result": {
                    "attempt_status": row["attempt_status"],
                    "agent_submission_status": result["agent_submission_status"],
                    "evaluation_status": result["evaluation_status"],
                    "official": result["official"],
                    "outcome_kind": outcome,
                    "scope_compliant_success": result["scope_compliant_success"],
                    "verdicts": verdicts,
                    "terminal_error": (
                        {
                            "type": result["terminal_error"]["type"],
                            "code": result["terminal_error"]["code"],
                            "reason_code": result["terminal_error"]["details"]["reason_code"],
                            "generation_started": result["terminal_error"]["details"][
                                "generation_started"
                            ],
                        }
                        if budget_branch
                        else None
                    ),
                },
                "usage": {
                    **usage,
                    "total_tokens": usage["input_tokens"] + usage["output_tokens"],
                    "model_cost_nanos": cost_nanos,
                },
                "qualification": {
                    "qualified": True,
                    "trace_integrity_passed": persisted["trace_integrity_passed"],
                    "leakage_scan_passed": persisted["leakage_scan_passed"],
                    "evaluation_reached": persisted["evaluation_reached"],
                    "memory_candidate_eligible": persisted["memory_candidate_eligible"],
                    "failure_record_id": failure_id,
                    "passed_checks": expected_check_count,
                    "total_checks": expected_check_count,
                    "qualification_hash": persisted["qualification_hash"],
                    "source_evidence_hash": persisted["source_evidence_hash"],
                    "read_only_recomputation_matched": True,
                },
                "budget_pressure": _safe_budget_projection(row),
                "trace": trace,
                "raw_artifacts": run_artifacts,
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
    aggregate_usage_payload["model_cost_nanos"] = aggregate_usage["model_cost_nanos"]
    aggregate_usage_payload["model_cost_usd"] = float(
        Decimal(aggregate_usage["model_cost_nanos"]) / Decimal(1_000_000_000)
    )
    _require(
        aggregate_usage_payload
        == {
            "input_tokens": 10_492_742,
            "cached_input_tokens": 0,
            "cache_write_input_tokens": 0,
            "output_tokens": 881_967,
            "reasoning_output_tokens": 805_212,
            "total_tokens": 11_374_709,
            "model_calls": 613,
            "input_token_count_calls": 614,
            "tool_calls": 964,
            "wall_clock_ms": 7_258_662,
            "model_cost_nanos": 11_838_408_000,
            "model_cost_usd": 11.838408,
        },
        "aggregate usage drifted",
    )
    expected_trace_totals = {
        "event_count": 4_536,
        "checkpoint_count": 978,
        "worker_claim_count": 12,
        "reclaimed_worker_claim_count": 0,
        "completed_model_responses": 613,
        "input_token_precount_calls": 614,
        "pre_provider_generation_blocks": 1,
        "exact_input_token_matches": 613,
        "exact_total_token_matches": 613,
        "truncation_disabled_responses": 613,
        "store_false_responses": 613,
        "previous_response_dependency_count": 0,
        "submission_accepted_count": 11,
        "run_completed_count": 11,
        "run_failed_count": 1,
        "memory_retrieval_count": 0,
    }
    _require(dict(aggregate_trace) == expected_trace_totals, "aggregate trace drifted")
    _require(
        outcome_counts == {"resolved": 2, "task_failure": 9, "agent_failure": 1},
        "outcome counts drifted",
    )
    _require(len(memory_candidates) == 9, "memory candidate count drifted")
    _require(
        BUDGET_RUN_ID not in {candidate["run_id"] for candidate in memory_candidates},
        "budget terminal entered the memory candidate set",
    )

    task_rows = [
        {
            "task_id": task_id,
            "attempts": task_attempts[task_id],
            "successes": task_successes[task_id],
            "success_rate": task_successes[task_id] / task_attempts[task_id],
        }
        for task_id in sorted(task_attempts)
    ]
    _require(
        sum(row["successes"] > 0 for row in task_rows) == 1,
        "task-first success count drifted",
    )

    body = {
        "milestone": "D-098",
        "evidence_kind": "measured-condition-neutral-no-memory-baseline-result-seal",
        "recorded_at": raw_result["created_at"],
        "sealed_at": sealed_at,
        "source_contract": {
            "harness_git_commit": SOURCE_HARNESS_COMMIT,
            "suite": SOURCE_FILES["suite"],
            "d096_policy_and_admission": SOURCE_FILES["d096-policy"],
            "d097_source_gate": SOURCE_FILES["d097-source-gate"],
            "execution_plan": {
                **RUNTIME_FILES["execution-plan"],
                "canonical_hash": PLAN_CANONICAL_HASH,
            },
            "schedule_identities": {
                "pre_shuffle_admission_schedule_hash": SOURCE_SCHEDULE_IDENTITY_HASH,
                "source_expanded_order_hash": SOURCE_EXPANDED_ORDER_HASH,
                "runtime_schedule_hash": RUNTIME_SCHEDULE_HASH,
                "meanings_are_distinct": True,
            },
        },
        "experiment": {
            "experiment_id": EXPERIMENT_ID,
            "purpose": raw_result["purpose"],
            "execution_hash": EXECUTION_HASH,
            "suite_hash": SUITE_HASH,
            "schedule_hash": RUNTIME_SCHEDULE_HASH,
            "schedule_seed": raw_result["schedule_seed"],
            "expected_runs": 12,
            "completed_runs": 12,
            "conditions": ["no_memory"],
            "repetitions": 2,
            "approved_maximum_cost_usd": 164.0,
            "campaign_scoped_project_cap_exception_used": True,
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
        },
        "baseline_admission": {
            "schema_version": "development-no-memory-baseline-result-v1",
            "passed": True,
            "denominator_rows": 12,
            "official_evaluator_rows": 11,
            "canonical_budget_terminal_rows": 1,
            "terminal_branches_mutually_exclusive_and_exhaustive": True,
            "comparison_denominator_eligible": True,
            "memory_review_eligible": True,
            "memory_admission_unlocked": False,
        },
        "campaign_cost": {
            "cost_control_hash": COST_CONTROL_HASH,
            "qualification": cost_qualification,
            "full_schedule_reserve_usd": 163.35,
            "hard_cap_usd": 164.0,
            "actual_usage_derived_standard_list_price_usd": 11.838408,
            "actual_invoice_claimed": False,
            "free_tier_treatment_claimed": False,
        },
        "aggregate_usage": aggregate_usage_payload,
        "aggregate_trace": expected_trace_totals,
        "runs": portable_rows,
        "memory_review_candidates": {
            "schema_version": "memory-review-candidate-set-v1",
            "eligibility_basis": "official-evaluator-task-failure-only",
            "candidate_count": 9,
            "candidates": memory_candidates,
            "excluded_resolved_count": 2,
            "excluded_budget_run_ids": [BUDGET_RUN_ID],
            "rules_created": 0,
            "review_completed": False,
            "dedup_completed": False,
            "leak_scan_completed": False,
            "memory_admission_unlocked": False,
        },
        "journal_seal": journal_projection,
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
            "journal_runtime_reconciliation_verified": True,
            "execution_plan_exact_hash_verified": True,
            "completion_gate_read_only_recomputed": True,
            "qualification_files_verified": 12,
            "qualification_checks_passed": 347,
            "read_only_recomputation_matches": 12,
            "official_receipts_and_submitted_patch_hashes_verified": 11,
            "budget_receipt_and_submitted_patch_absence_verified": True,
            "prompt_usage_reconciliation_passed": True,
            "input_precount_relation": "614=613-completed-provider-calls+1-pre-provider-block",
            "leak_safe_projection_only": True,
        },
        "analysis": {
            "exact_development_baseline_scrr": {
                "successes": 2,
                "attempts": 12,
                "rate": 2 / 12,
            },
            "official_evaluator_hidden_acceptance": {
                "successes": 2,
                "attempts": 11,
                "rate": 2 / 11,
                "diagnostic_only": True,
            },
            "task_first_results": task_rows,
            "task_first_mean_success_rate": 1 / 6,
            "outcome_counts": dict(sorted(outcome_counts.items())),
            "memory_effect_estimated": False,
            "held_out_performance_estimated": False,
            "confidence_interval_computed": False,
            "interpretation": "exact-development-no-memory-baseline-only",
        },
        "claims_boundary": {
            "live_provider_execution_observed": True,
            "provider_model_calls_observed": 613,
            "official_evaluator_runs_observed": 11,
            "development_no_memory_baseline_result_established": True,
            "development_baseline_denominator_complete": True,
            "comparison_denominator_eligible": True,
            "memory_review_eligible": True,
            "memory_admission_unlocked": False,
            "memory_index_frozen": False,
            "core_campaign_unlocked": False,
            "analysis_ready": False,
            "held_out_or_cross_condition_effect_estimated": False,
            "automatic_rerun_authorized": False,
            "hidden_driven_tuning_authorized": False,
            "per_row_atomic_sqlite_consumption_claimed": False,
            "duplicate_paid_call_prevention_claimed": False,
            "live_resume_supported": False,
            "actual_invoice_or_free_tier_treatment_claimed": False,
            "original_result_journal_run_or_qualification_modified": False,
            "seal_provider_calls": 0,
            "seal_evaluator_calls": 0,
            "seal_added_model_cost_usd": 0.0,
        },
        "next_gate": {
            "decision_required": "public-evidence-memory-review-dedup-and-leak-scan",
            "current_experiment_hard_consumed": True,
            "current_execution_hash_reusable": False,
            "automatic_successor_authorized": False,
            "memory_review_candidate_count": 9,
            "memory_rule_admission_completed": False,
            "memory_index_build_authorized": False,
            "core_campaign_unlocked": False,
            "new_live_execution_authorized": False,
        },
    }
    body_hash = sha256_json(body)
    return {
        "schema_version": "condition-neutral-no-memory-baseline-d098-evidence-v1",
        "report_id": f"d098_{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": body,
    }


def build_seal(
    *, repo_root: Path, runtime_root: Path, sealed_at: str = SEALED_AT
) -> dict[str, Any]:
    _require(sealed_at == SEALED_AT, "sealed_at must match the exact D-098 seal time")
    _require(
        runtime_root.resolve() == (repo_root / ".patchloop").resolve(),
        "runtime root must be the exact repository runtime",
    )
    source_state_path = runtime_root / "state.sqlite3"
    before = _state_bundle_fingerprint(source_state_path)
    with tempfile.TemporaryDirectory(prefix="patchloop-d098-state-") as temporary:
        snapshot_state_path = _copy_state_snapshot(source_state_path, Path(temporary))
        try:
            payload = _build_seal_from_snapshot(
                repo_root=repo_root,
                runtime_root=runtime_root,
                state_path=snapshot_state_path,
                sealed_at=sealed_at,
            )
        finally:
            gc.collect()
    after = _state_bundle_fingerprint(source_state_path)
    _require(after == before, "source SQLite/WAL/SHM bundle changed during seal build")
    lowered = canonical_json(payload).lower()
    for marker in (
        "c:\\users\\",
        "diff --git",
        "@@ -",
        "openai_api_key",
        "authorization: bearer",
        '"private_spec_hash"',
        '"verifier_results"',
        '"evidence_artifacts"',
        '"request_body"',
        '"response_body"',
        '"patch_body"',
        '"reference_patch"',
    ):
        _require(marker not in lowered, f"portable seal contains forbidden marker: {marker}")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the content-addressed D-098 no-memory baseline result seal."
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
        output = args.output if args.output.is_absolute() else repo_root / args.output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
