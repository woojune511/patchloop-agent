"""Subprocess-only helper for hard worker recovery tests."""

from __future__ import annotations

import argparse
import json
import os
import time
import uuid
from pathlib import Path

from patchloop.agent.runner import AgentRunner
from patchloop.agent.tools import ToolGateway
from patchloop.errors import PatchLoopError
from patchloop.runtime import build_manifest
from patchloop.sandbox import DockerSandbox
from patchloop.task_loader import load_task_package


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    content = json.dumps(value, sort_keys=True).encode("utf-8")
    try:
        with temporary.open("xb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _start_and_hold(
    runtime_root: Path,
    task_path: Path,
    run_id: str,
    output_path: Path,
) -> int:
    package = load_task_package(task_path.parent)
    manifest = build_manifest(
        package,
        run_id=run_id,
        sandbox_backend="local",
    )

    def hold_after_postimage_write(
        _gateway,
        _patch,
        _baseline_diff_hash,
        *,
        expected_diff_hash=None,
        intent=None,
    ):
        _write_json(
            output_path,
            {
                "state": "holding-after-postimage-write",
                "run_id": run_id,
                "pid": os.getpid(),
                "expected_diff_hash": expected_diff_hash,
                "intent_present": intent is not None,
            },
        )
        while True:
            time.sleep(0.1)

    ToolGateway._finalize_applied_patch = hold_after_postimage_write
    runner = AgentRunner(runtime_root)
    result = runner.start(task_path, model="mock", manifest=manifest)
    _write_json(output_path, {"state": "unexpected-return", "result": result})
    return 2


def _resume(
    runtime_root: Path,
    run_id: str,
    output_path: Path,
) -> int:
    runner = AgentRunner(runtime_root)
    try:
        result = runner.resume(run_id)
    except PatchLoopError as exc:
        _write_json(
            output_path,
            {
                "ok": False,
                "error": exc.code,
                "message": str(exc),
                "details": exc.details,
            },
        )
        return 3
    _write_json(output_path, {"ok": True, "result": result})
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices={"start-and-hold", "resume"})
    parser.add_argument("--runtime-root", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--task", type=Path)
    arguments = parser.parse_args()
    DockerSandbox.available = staticmethod(lambda: False)
    if arguments.mode == "start-and-hold":
        if arguments.task is None:
            parser.error("--task is required for start-and-hold")
        return _start_and_hold(
            arguments.runtime_root,
            arguments.task,
            arguments.run_id,
            arguments.output,
        )
    return _resume(
        arguments.runtime_root,
        arguments.run_id,
        arguments.output,
    )


if __name__ == "__main__":
    raise SystemExit(main())
