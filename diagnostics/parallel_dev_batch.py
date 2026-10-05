"""Bounded independent task processes with a shared provider-admission stop latch.

Row caps are reserved in full, once, with no transfers. Already admitted network
operations settle after a stop; no later count/generation is admitted. Workers
never share solver histories, credentials, workspaces, or mutable model settings.
"""

from __future__ import annotations

import multiprocessing
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from time import monotonic

from diagnostics.positive_verification_panel import require
from patchloop.agent.model import OpenAIResponsesAdapter
from patchloop.dev import runner
from patchloop.dev.contracts import DevRunRequest
from patchloop.dev.cost import usd_to_nanos
from patchloop.dev.state import DevJournal

_STOP = None
_ADMISSION = None


class BatchStopped(RuntimeError):
    """This row has not admitted another network request."""


def stop_workers():
    with _ADMISSION:
        _STOP.set()


class CoordinatedJournal(DevJournal):
    def append(self, event_type, payload=None):
        payload = payload or {}
        # The durable start and stop transition share one admission boundary.
        # Calls admitted before a peer's failure may finish, and must be accounted.
        if event_type in {"input_count_started", "provider_call_started"}:
            with _ADMISSION:
                if _STOP.is_set():
                    super().append("batch_call_prevented", {"operation": event_type})
                    raise BatchStopped("parallel batch stopped before network admission")
                return super().append(event_type, payload)
        if (
            event_type == "input_count_failed"
            or (event_type == "evaluator_finished" and payload.get("stop_remaining") is True)
            or (
                event_type == "provider_call_finished"
                and payload.get("error_code")
                in {
                    "input_token_count_mismatch",
                    "provider_continuation_error",
                }
            )
            or (
                event_type == "action_finished"
                and (payload.get("result", {}).get("output") or {}).get("cleanup_failed")
            )
        ):
            stop_workers()
        return super().append(event_type, payload)


class CoordinatedAdapter(OpenAIResponsesAdapter):
    def count_input_tokens_v2(self, *args, **kwargs):
        try:
            return super().count_input_tokens_v2(*args, **kwargs)
        except BaseException:
            stop_workers()
            raise

    def execute_request(self, *args, **kwargs):
        try:
            result = super().execute_request(*args, **kwargs)
            if result.error and result.error.code in {
                "input_token_count_mismatch",
                "provider_continuation_error",
            }:
                stop_workers()
            return result
        except BaseException:
            stop_workers()
            raise


def initialize_worker(stop, admission):
    global _STOP, _ADMISSION
    _STOP, _ADMISSION = stop, admission
    # Process-local substitution: no prompt change or shared threaded monkeypatch.
    runner.DevJournal = CoordinatedJournal
    runner.OpenAIResponsesAdapter = CoordinatedAdapter


def usage_snapshot(state_root):
    """Retain settled costs even if a peer stop interrupts a row before terminal."""
    records = []
    for path in sorted((state_root / "runs").glob("*.jsonl")):
        events = DevJournal(state_root, path.stem).events()
        started, finished, counts, counted = set(), set(), set(), set()
        cost = 0
        valid = True
        for event in events:
            kind, p = event["event_type"], event["payload"]
            if kind == "provider_call_started":
                started.add(p["call_id"])
            elif kind == "provider_call_finished":
                valid &= p["call_id"] not in finished
                finished.add(p["call_id"])
                cost += p["cost_nanos"]
                valid &= p.get("error_code") != "input_token_count_mismatch"
            elif kind == "input_count_started":
                counts.add(p["count_id"])
            elif kind == "input_count_finished":
                counted.add(p["count_id"])
        records.append(
            {
                "run_id": path.stem,
                "cost_nanos": cost,
                "billing_known": valid and started == finished,
                "counting_known": counts == counted,
                "provider_calls": len(started),
            }
        )
    return {
        "runs": records,
        "cost_nanos": sum(r["cost_nanos"] for r in records),
        "billing_known": all(r["billing_known"] for r in records),
        "counting_known": all(r["counting_known"] for r in records),
    }


def recover_usage(state_root):
    try:
        return usage_snapshot(state_root)
    except Exception as exc:
        return {"runs": [], "cost_nanos": None, "billing_known": False,
                "counting_known": False, "error_type": type(exc).__name__}


def solve_row(serialized):
    req = DevRunRequest.model_validate(serialized)
    started = monotonic()
    result, error = None, None
    try:
        if _STOP.is_set():
            raise BatchStopped("parallel batch stopped before row preparation")
        require(req.repeat == 1 and req.resume_run_id is None, "fresh single row required")
        require(not req.state_root.exists(), "row state exists; no replacement")
        result = runner.run_dev(req)
        if result.get("stop_remaining"):
            stop_workers()
    except BaseException as exc:
        stop_workers()
        error = type(exc).__name__
    usage = recover_usage(req.state_root)
    ok = (
        result is not None
        and not result.get("stop_remaining")
        and usage["billing_known"]
        and usage["counting_known"]
        and result["cost_nanos"] == usage["cost_nanos"]
        and 0 <= usage["cost_nanos"] <= usd_to_nanos(req.max_cost_usd)
    )
    if result is not None:
        ok &= all(
            r["terminal"]
            in {
                "EVALUATOR_PASS",
                "EVALUATOR_FAIL",
                "AGENT_STOPPED",
                "LIMIT_REACHED",
                "COST_CAP_REACHED",
            }
            for r in result["runs"]
        )
    if not ok:
        stop_workers()
    return {
        "result": result,
        "error_type": error,
        "accounting": usage,
        "ok": bool(ok),
        "elapsed_seconds": round(monotonic() - started, 3),
    }


def run_parallel_rows(
    rows,
    *,
    total_cap,
    workers,
    journal,
    after_row,
    execute=solve_row,
    initializer=initialize_worker,
):
    require(type(workers) is int and 1 <= workers <= 4, "workers must be between one and four")
    requests = [DevRunRequest.model_validate(row["request"]) for row in rows]
    require(len({r.task.resolve() for r in requests}) == len(rows), "distinct tasks required")
    roots = [r.state_root.resolve() for r in requests]
    require(
        len(set(roots)) == len(roots)
        and all(not a.is_relative_to(b) for a in roots for b in roots if a != b),
        "independent state roots required",
    )
    require(all(r.repeat == 1 and r.resume_run_id is None for r in requests), "no repeats/resume")
    require(bool(rows) and all(r.max_cost_usd is not None and r.max_cost_usd > 0
                             for r in requests), "positive row allocations required")
    require(total_cap > 0, "positive invocation cap required")
    reserved = sum(usd_to_nanos(r.max_cost_usd) for r in requests)
    require(reserved <= usd_to_nanos(total_cap), "sum of reserved row caps exceeds batch cap")
    ctx = multiprocessing.get_context("spawn")
    stop, admission = ctx.Event(), ctx.Lock()
    completed, pending, cursor = {}, {}, 0
    journal.append(
        "parallel_allocation", {"reserved_nanos": reserved, "workers": workers, "transfer": False}
    )
    with ProcessPoolExecutor(
        max_workers=workers, mp_context=ctx, initializer=initializer, initargs=(stop, admission)
    ) as pool:
        try:
            while pending or cursor < len(rows):
                while not stop.is_set() and cursor < len(rows) and len(pending) < workers:
                    row = rows[cursor]
                    journal.append("row_started", {"index": cursor, "request": row["request"]})
                    pending[pool.submit(execute, row["request"])] = cursor
                    cursor += 1
                if not pending:
                    break
                done, _ = wait(pending, return_when=FIRST_COMPLETED)
                # Process every observed failure before admitting another row.
                finished = []
                for future in done:
                    index = pending.pop(future)
                    try:
                        value = future.result()
                    except BaseException as exc:
                        with admission:
                            stop.set()
                        value = {"ok": False, "error_type": type(exc).__name__, "result": None,
                                 "accounting": recover_usage(requests[index].state_root)}
                    if not value["ok"]:
                        with admission:
                            stop.set()
                    finished.append((index, value))
                for index, value in finished:
                    completed[index] = value
                    journal.append("row_finished", {"index": index, **value})
                    if value["ok"]:
                        try:
                            value["assessment"] = after_row(index, value, requests[index])
                            assessment = value["assessment"]
                            if not assessment["ok"]:
                                # A verified per-task deadline is an unavailable verdict,
                                # not uncertainty shared by otherwise independent workers.
                                # The assessor owns receipt/cleanup validation; all other
                                # unsuccessful assessments still stop new admissions.
                                require(
                                    assessment.get("disposition") == "task_limit",
                                    "evaluation uncertainty/disagreement",
                                )
                                require(
                                    value["accounting"]["billing_known"]
                                    and value["accounting"]["counting_known"],
                                    "task limit has unsettled accounting",
                                )
                                value["ok"] = False
                            journal.append(
                                "row_assessed", {"index": index, "assessment": value["assessment"]}
                            )
                        except BaseException as exc:
                            with admission:
                                stop.set()
                            value["ok"] = False
                            value["assessment_error"] = type(exc).__name__
                            journal.append(
                                "row_assessment_failed",
                                {"index": index, "error_type": type(exc).__name__},
                            )
        except BaseException:
            with admission:
                stop.set()
            # Pool shutdown settles already admitted operations; never kill a billing call.
            raise
    return {
        "rows": [{"index": i, **completed[i]} for i in sorted(completed)],
        "started": cursor,
        "not_started": len(rows) - cursor,
        "stopped": stop.is_set(),
        "allocation": "CLOSED",
    }
