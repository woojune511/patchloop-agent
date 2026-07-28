from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

from patchloop.contracts import EventType, RunStatus
from patchloop.repository import WorkspaceManager
from patchloop.state import StateStore

TASK = Path("tasks/smoke/csv-quoted-newline/public.yaml").resolve()
WORKER = Path("tests/_process_recovery_worker.py").resolve()


def _wait_for_json(path: Path, process: subprocess.Popen, timeout: float) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            raise AssertionError(
                f"worker exited before evidence was written: "
                f"code={process.returncode}, stdout={stdout!r}, stderr={stderr!r}"
            )
        time.sleep(0.05)
    process.kill()
    stdout, stderr = process.communicate(timeout=10)
    raise AssertionError(
        f"worker evidence timed out: stdout={stdout!r}, stderr={stderr!r}"
    )


def _worker_command(
    mode: str,
    runtime_root: Path,
    run_id: str,
    output: Path,
    *,
    task: Path | None = None,
) -> list[str]:
    command = [
        sys.executable,
        str(WORKER),
        mode,
        "--runtime-root",
        str(runtime_root),
        "--run-id",
        run_id,
        "--output",
        str(output),
    ]
    if task is not None:
        command.extend(["--task", str(task)])
    return command


def test_hard_kill_reclaims_running_patch_without_duplicate_mutation(
    tmp_path,
) -> None:
    runtime_root = tmp_path / "runtime"
    run_id = "run_process_kill_recovery"
    ready_path = tmp_path / "holding.json"
    first = subprocess.Popen(
        _worker_command(
            "start-and-hold",
            runtime_root,
            run_id,
            ready_path,
            task=TASK,
        ),
        cwd=Path.cwd(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        ready = _wait_for_json(ready_path, first, timeout=30)
        assert ready["state"] == "holding-after-postimage-write"
        assert ready["intent_present"] is True
        assert first.poll() is None

        state = StateStore(runtime_root / "state.sqlite3")
        before_events = [
            event.model_dump(mode="json")
            for event in state.list_events(run_id)
        ]
        before_claims = state.list_worker_claims(run_id)
        assert state.get_run_status(run_id) == RunStatus.RUNNING
        assert not any(
            event["type"] in {
                EventType.RUN_COMPLETED,
                EventType.RUN_FAILED,
            }
            for event in before_events
        )

        contender_path = tmp_path / "contender.json"
        contender = subprocess.run(
            _worker_command(
                "resume",
                runtime_root,
                run_id,
                contender_path,
            ),
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        contender_result = json.loads(
            contender_path.read_text(encoding="utf-8")
        )
        assert contender.returncode == 3
        assert contender_result["error"] == "RUN_OWNERSHIP_CONFLICT"
        assert state.get_run_status(run_id) == RunStatus.RUNNING
        assert [
            event.model_dump(mode="json")
            for event in state.list_events(run_id)
        ] == before_events
        assert state.list_worker_claims(run_id) == before_claims

        first.kill()
        first.communicate(timeout=15)
        assert first.returncode != 0

        resumed_path = tmp_path / "resumed.json"
        resumed = subprocess.run(
            _worker_command(
                "resume",
                runtime_root,
                run_id,
                resumed_path,
            ),
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        resumed_result = json.loads(
            resumed_path.read_text(encoding="utf-8")
        )
        assert resumed.returncode == 0, (
            resumed.stdout,
            resumed.stderr,
            resumed_result,
        )
        assert resumed_result["ok"] is True
        assert resumed_result["result"]["run_id"] == run_id
        assert resumed_result["result"]["scope_compliant_success"] is True
    finally:
        if first.poll() is None:
            first.kill()
            first.communicate(timeout=15)

    events = state.list_events(run_id)
    assert [event.sequence for event in events] == list(
        range(1, len(events) + 1)
    )
    assert sum(event.type == EventType.TOOL_CALLED for event in events) == 5
    assert (
        sum(
            event.type == EventType.TOOL_CALLED
            and event.payload.get("tool") == "apply_patch"
            for event in events
        )
        == 1
    )
    assert sum(event.type == EventType.PATCH_PREPARED for event in events) == 1
    assert sum(event.type == EventType.PATCH_APPLIED for event in events) == 1
    assert sum(event.type == EventType.RUN_COMPLETED for event in events) == 1
    assert sum(event.type == EventType.RUN_FAILED for event in events) == 0
    assert state.get_run_status(run_id) == RunStatus.COMPLETED

    claims = state.list_worker_claims(run_id)
    assert len(claims) == 2
    assert claims[0]["prior_status"] == RunStatus.CREATED.value
    assert claims[0]["reclaimed"] is False
    assert claims[1]["prior_status"] == RunStatus.RUNNING.value
    assert claims[1]["reclaimed"] is True
    assert claims[0]["owner_id"] != claims[1]["owner_id"]

    workspace = runtime_root / "workspaces" / run_id / "repo"
    summary = WorkspaceManager.diff_summary(workspace)
    patch_events = [
        event for event in events if event.type == EventType.PATCH_APPLIED
    ]
    accepted = next(
        event for event in events if event.type == EventType.SUBMISSION_ACCEPTED
    )
    assert patch_events[0].payload["worktree_diff_hash"] == summary.patch_hash
    assert accepted.payload["worktree_diff_hash"] == summary.patch_hash
    source = (
        workspace / "mini_data_utils" / "csvlite.py"
    ).read_text(encoding="utf-8")
    assert source.count("import io") == 1
    assert source.count(
        'return list(csv.reader(io.StringIO(text, newline="")))'
    ) == 1
