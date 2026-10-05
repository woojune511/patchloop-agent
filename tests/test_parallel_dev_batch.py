"""Actual spawned processes: overlap, admission stop, settlement and allocation."""

import multiprocessing
import time
from decimal import Decimal
from pathlib import Path

import pytest

from diagnostics import parallel_dev_batch as batch
from patchloop.dev.contracts import DevRunRequest
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError


def rows(root, count=3):
    return [
        {
            "request": DevRunRequest(
                provider="openai",
                model="gpt-5.4-mini-2026-03-17",
                env_file=root / "unused.env",
                task=root / f"task{i}/public.yaml",
                state_root=root / str(i),
                max_cost_usd=Decimal("1"),
            ).model_dump(mode="json")
        }
        for i in range(count)
    ]


def rendezvous(req):
    root = Path(req["state_root"])
    root.mkdir()
    (root / "entered").touch()
    if root.name in {"0", "1"}:
        peer = root.parent / ("1" if root.name == "0" else "0") / "entered"
        deadline = time.monotonic() + 10
        while not peer.exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        assert peer.exists(), "tasks did not overlap"
    return root


def successful(req):
    root = rendezvous(req)
    return {"ok": True, "result": str(root), "accounting": batch.usage_snapshot(root)}


def failing_with_inflight_peer(req):
    root = rendezvous(req)
    journal = batch.CoordinatedJournal(root, "run_dev_peer")
    if root.name == "0":
        deadline = time.monotonic() + 10
        while not (root.parent / "1/admitted").exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        assert (root.parent / "1/admitted").exists()
        batch.stop_workers()
        return {"ok": False, "accounting": batch.usage_snapshot(root)}
    journal.append("provider_call_started", {"call_id": "first"})
    (root / "admitted").touch()
    assert batch._STOP.wait(10)
    journal.append("provider_call_finished", {"call_id": "first", "cost_nanos": 17})
    with pytest.raises(batch.BatchStopped):
        journal.append("provider_call_started", {"call_id": "blocked"})
    return {"ok": False, "accounting": batch.usage_snapshot(root)}


@pytest.mark.parametrize("fail", [False, True])
def test_spawned_rows_overlap_and_peer_stop_settles_without_next_dispatch(tmp_path, fail):
    result = batch.run_parallel_rows(
        rows(tmp_path),
        total_cap=Decimal("3"),
        workers=2,
        journal=DevJournal(tmp_path / "batch", "run_dev_batch"),
        after_row=lambda *args: {"ok": True},
        execute=failing_with_inflight_peer if fail else successful,
    )
    assert result["started"] == (2 if fail else 3)
    assert result["not_started"] == (1 if fail else 0)
    assert result["stopped"] == fail
    if fail:
        usage = result["rows"][1]["accounting"]
        assert usage["billing_known"] and usage["cost_nanos"] == 17
        assert usage["runs"][0]["provider_calls"] == 1
        assert not (tmp_path / "2").exists()


def test_batch_allocation_rejected_before_process_launch(tmp_path):
    with pytest.raises(ContractError, match="exceeds batch cap"):
        batch.run_parallel_rows(
            rows(tmp_path), total_cap=Decimal("2"), workers=2, journal=None, after_row=None
        )


def test_unknown_billing_preserves_settled_cost_and_blocks_admission(tmp_path, monkeypatch):
    ctx = multiprocessing.get_context("spawn")
    monkeypatch.setattr(batch, "_STOP", ctx.Event())
    monkeypatch.setattr(batch, "_ADMISSION", ctx.Lock())
    journal = batch.CoordinatedJournal(tmp_path, "run_dev_unknown")
    journal.append("provider_call_started", {"call_id": "a"})
    journal.append("provider_call_finished", {"call_id": "a", "cost_nanos": 13})
    journal.append("provider_call_started", {"call_id": "b"})
    journal.append("input_count_failed", {"count_id": "failed"})
    with pytest.raises(batch.BatchStopped):
        journal.append("input_count_started", {"count_id": "blocked"})
    usage = batch.usage_snapshot(tmp_path)
    assert not usage["billing_known"] and usage["cost_nanos"] == 13


def test_known_row_deadline_keeps_independent_workers_and_remaining_rows_running(tmp_path):
    result = batch.run_parallel_rows(
        rows(tmp_path, count=4), total_cap=Decimal("4"), workers=2,
        journal=DevJournal(tmp_path / "batch", "run_dev_batch"),
        execute=successful,
        after_row=lambda index, *_: (
            {"ok": False, "status": "FAIL", "agreement": False, "disposition": "task_limit"}
            if index == 0 else {"ok": True, "status": "PASS", "agreement": True}
        ),
    )
    assert result["started"] == 4 and result["not_started"] == 0
    assert not result["stopped"]
    assert not result["rows"][0]["ok"]
    assert result["rows"][0]["assessment"]["agreement"] is False
    assert all(row["ok"] for row in result["rows"][1:])


@pytest.mark.parametrize("disposition, known", [(None, True), ("task_limit", False)])
def test_disagreement_or_unsettled_deadline_still_stops_batch(tmp_path, disposition, known):
    def assess(index, value, request):
        value["accounting"]["billing_known"] = known
        return {"ok": False, "disposition": disposition}

    result = batch.run_parallel_rows(
        rows(tmp_path), total_cap=Decimal("3"), workers=2,
        journal=DevJournal(tmp_path / "batch", "run_dev_batch"),
        execute=successful, after_row=assess,
    )
    assert result["stopped"]
    assert all(not row["ok"] for row in result["rows"])


def test_evaluator_cleanup_uncertainty_stops_next_admission(tmp_path, monkeypatch):
    ctx = multiprocessing.get_context("spawn")
    monkeypatch.setattr(batch, "_STOP", ctx.Event())
    monkeypatch.setattr(batch, "_ADMISSION", ctx.Lock())
    journal = batch.CoordinatedJournal(tmp_path, "run_dev_cleanup")
    journal.append("evaluator_finished", {"stop_remaining": True})
    with pytest.raises(batch.BatchStopped):
        journal.append("provider_call_started", {"call_id": "blocked"})


def test_worker_preserves_runtime_stop_even_for_accounted_limit(tmp_path, monkeypatch):
    ctx = multiprocessing.get_context("spawn")
    monkeypatch.setattr(batch, "_STOP", ctx.Event())
    monkeypatch.setattr(batch, "_ADMISSION", ctx.Lock())
    monkeypatch.setattr(batch.runner, "run_dev", lambda _: {
        "cost_nanos": 0, "stop_remaining": True,
        "runs": [{"terminal": "LIMIT_REACHED"}],
    })
    result = batch.solve_row(rows(tmp_path, count=1)[0]["request"])
    assert result["accounting"]["billing_known"]
    assert not result["ok"] and batch._STOP.is_set()
