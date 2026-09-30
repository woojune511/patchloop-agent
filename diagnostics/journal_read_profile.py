"""Bounded, provider-free journal read profile; runtime and journal semantics stay intact."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from unittest.mock import patch

from patchloop.artifacts import ArtifactStore
from patchloop.dev import runner
from patchloop.dev.contracts import DevRunRequest
from patchloop.dev.state import DevJournal
from patchloop.runtime import git_commit, repository_root, runtime_content_hash
from patchloop.util import sha256_bytes


class InterruptedMutation(BaseException):
    """Simulate process loss after applying an edit, before recording its result."""


def measure(request, *, interrupt=False):
    original_events, original_append = DevJournal.events, DevJournal.append
    rows = []
    fired = False

    def events(journal):
        outer = time.perf_counter_ns()
        size = journal.path.stat().st_size if journal.path.exists() else 0
        frame = sys._getframe(1)
        callers = []
        for _ in range(3):
            if frame is None:
                break
            callers.append(f"{Path(frame.f_code.co_filename).name}:{frame.f_code.co_name}")
            frame = frame.f_back
        del frame
        start = time.perf_counter_ns()
        result = original_events(journal)
        duration = time.perf_counter_ns() - start
        turn = next((e["payload"]["turn_id"] for e in reversed(result)
                     if isinstance(e["payload"].get("turn_id"), str)), None)
        rows.append({
            "run_id": journal.run_id, "latest_recorded_turn": turn,
            "callers": callers, "logical_bytes": size, "events": len(result),
            "tail_hash": result[-1]["event_hash"] if result else None,
            "read_validate_ns": duration,
            "observer_ns": time.perf_counter_ns() - outer - duration,
        })
        return result

    def append(journal, event_type, payload=None):
        nonlocal fired
        if (interrupt and not fired and event_type == "action_finished"
                and (payload or {}).get("result", {}).get("tool") == "replace_text"):
            fired = True
            raise InterruptedMutation()
        return original_append(journal, event_type, payload)

    started = time.perf_counter_ns()
    result = None
    with patch.object(DevJournal, "events", events), patch.object(DevJournal, "append", append):
        try:
            result = runner.run_dev(request)
        except InterruptedMutation:
            if not interrupt:
                raise
    wall = time.perf_counter_ns() - started
    assert fired == interrupt
    seen = set()
    groups = defaultdict(lambda: Counter(calls=0, logical_bytes=0, read_validate_ns=0))
    duplicate_ns = 0
    for row in rows:
        prefix = row["run_id"], row["tail_hash"]
        repeated = prefix in seen
        seen.add(prefix)
        row["repeated_prefix"] = repeated
        if repeated and row["callers"][0] != "state.py:append":
            duplicate_ns += row["read_validate_ns"]
        for key in ("caller:" + row["callers"][0], "turn:" + str(row["latest_recorded_turn"])):
            groups[key].update(calls=1, logical_bytes=row["logical_bytes"],
                               read_validate_ns=row["read_validate_ns"])
    total_ns = sum(r["read_validate_ns"] for r in rows)
    return {
        "result": result, "interrupted": fired, "rows": rows, "groups": dict(groups),
        "wall_seconds": wall / 1e9, "read_validate_seconds": total_ns / 1e9,
        "read_validate_wall_fraction": total_ns / wall,
        "observer_seconds": sum(r["observer_ns"] for r in rows) / 1e9,
        "calls": len(rows), "logical_bytes": sum(r["logical_bytes"] for r in rows),
        "repeat_nonappend_seconds_upper_bound": duplicate_ns / 1e9,
        "repeat_nonappend_wall_fraction_upper_bound": duplicate_ns / wall,
    }


def verify_run(request, result):
    run = result["runs"][0]
    assert run["terminal"] == "EVALUATOR_PASS", run
    assert run["evaluator"]["task_acceptance"] == "PASS"
    assert run["evaluator"]["safety_state"] == "NOT_RUN"
    assert run["accepted_mutations"] == 1 and run["cost_nanos"] == 0
    journal = DevJournal(request.state_root, run["run_id"])
    events = journal.events()  # Independently verify the final chain outside measurement.
    actions = [e["payload"]["result"] for e in events if e["event_type"] == "action_finished"]
    assert len({r["action_id"] for r in actions}) == len(actions)
    assert sum(r["tool"] == "replace_text" for r in actions) == 1
    return journal, run


def profile(output: Path):
    root = output.resolve()
    if root.is_relative_to(repository_root().resolve()):
        raise ValueError("measurement state must be outside the repository")
    root.mkdir(parents=True, exist_ok=False)
    store, journal = ArtifactStore(root), DevJournal(root, "run_dev_journalprofile")
    protocol = {
        "base_commit": git_commit(), "runtime_hash": runtime_content_hash(),
        "normal_repetitions": 3, "interrupted_repetitions": 1, "terminal_resume": 1,
        "provider": "mock", "task": "tasks/smoke/csv-quoted-newline/public.yaml",
        "context_policy": "segmented-v1", "planning_policy": "brief-v1",
        "repair_recheck": True, "enable_probes": False,
        "gate": "normal median repeated non-append read time >=1s AND wall fraction >=0.10",
        "limits": "short smoke only; logical bytes, not physical I/O; optimistic reuse bound",
    }
    journal.append("protocol_frozen", protocol)
    summaries = []

    def save(label, measured):
        artifact = store.put_json(measured)
        summary = {k: v for k, v in measured.items() if k not in {"rows", "result"}}
        summary.update(label=label, artifact=artifact.model_dump(mode="json"))
        journal.append("measurement_completed", summary)
        summaries.append(summary)
        print(json.dumps({k: v for k, v in summary.items() if k not in {"groups", "artifact"}}),
              flush=True)

    patch_hashes, call_counts = [], []
    for index in range(3):
        request = DevRunRequest(
            provider="mock", model="mock-dev", task=repository_root() / protocol["task"],
            state_root=root / f"normal-{index + 1}", context_policy="segmented-v1",
            planning_policy="brief-v1", repair_recheck=True,
        )
        measured = measure(request)
        completed, run = verify_run(request, measured["result"])
        patch_hashes.append(run["artifact_hashes"]["submitted_patch"])
        call_counts.append(run["call_counts"])
        save(f"normal-{index + 1}", measured)
    before = completed.path.read_bytes()
    measured = measure(request.model_copy(update={"resume_run_id": run["run_id"]}))
    assert measured["result"]["runs"][0] == run and completed.path.read_bytes() == before
    save("terminal-resume", measured)
    request = request.model_copy(update={"state_root": root / "interrupted"})
    save("interrupted-before-mutation-receipt", measure(request, interrupt=True))
    envelopes = list((request.state_root / "runs").glob("*.envelope.json"))
    assert len(envelopes) == 1
    run_id = envelopes[0].name.removesuffix(".envelope.json")
    partial = DevJournal(request.state_root, run_id)
    prefix = partial.path.read_bytes()
    measured = measure(request.model_copy(update={"resume_run_id": run_id}))
    completed, run = verify_run(request, measured["result"])
    assert completed.path.read_bytes().startswith(prefix)
    assert sum(e["event_type"] == "run_resumed" for e in completed.events()) == 1
    patch_hashes.append(run["artifact_hashes"]["submitted_patch"])
    call_counts.append(run["call_counts"])
    assert len(set(patch_hashes)) == 1 and all(c == call_counts[0] for c in call_counts)
    save("mutation-receipt-resume", measured)
    normal = summaries[:3]
    seconds = statistics.median(s["repeat_nonappend_seconds_upper_bound"] for s in normal)
    fraction = statistics.median(s["repeat_nonappend_wall_fraction_upper_bound"] for s in normal)
    decision = {
        "optimization_gate_met": seconds >= 1 and fraction >= 0.10,
        "median_repeat_nonappend_seconds_upper_bound": seconds,
        "median_repeat_nonappend_wall_fraction_upper_bound": fraction,
        "same_submitted_patch": patch_hashes[0], "same_call_counts": call_counts[0],
        "terminal_resume_journal_unchanged": True, "crash_prefix_preserved": True,
        "terminal_resume_journal_hash": sha256_bytes(before),
        "crash_prefix_hash": sha256_bytes(prefix),
        "profile_source_hash": sha256_bytes(Path(__file__).read_bytes()),
    }
    journal.append("measurement_decision", decision)
    with (root / "summary.json").open("x", encoding="utf-8") as stream:
        json.dump({"protocol": protocol, "measurements": summaries, "decision": decision},
                  stream, indent=2)
    journal.events()
    print(json.dumps(decision, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    profile(parser.parse_args().output)
