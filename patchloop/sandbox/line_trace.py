"""Standalone stdlib collector, copied read-only beside sandbox launchers.

Line-entry observations in the launch thread are advisory, not a sandbox or an
oracle. No values, source bodies, other files, threads or subprocesses are recorded.
"""

from __future__ import annotations

import dis
import hashlib
import json
import os
import runpy
import sys
import types
from contextlib import suppress
from pathlib import Path


def marker(request: dict) -> bytes:
    return b"\x1ePATCHLOOP-LINES:" + request["request_hash"].encode("ascii") + b":"


class LineTrace:
    def __init__(self, request: dict, root: str) -> None:
        self.request = request
        self.rows = []
        self.targets = {}
        self.trace = self._trace
        self.previous = sys.gettrace()
        # Retain real I/O before project code may patch Python's filesystem APIs.
        self.write = os.write
        self.open = open
        self.gettrace = sys.gettrace
        self.settrace = sys.settrace
        for index, target in enumerate(request["files"]):
            row = {"index": index, "status": "unknown", "executable": [], "executed": []}
            self.rows.append(row)
            path = Path(root) / target["path"]
            try:
                with self.open(path, "rb") as stream:
                    raw = stream.read()
                if "sha256:" + hashlib.sha256(raw).hexdigest() != target["file_hash"]:
                    row["reason"] = "source_hash_mismatch"
                    continue
                code = compile(raw, str(path), "exec", dont_inherit=True)
                lines = set()
                pending = [code]
                while pending:
                    current = pending.pop()
                    lines.update(line for _, line in dis.findlinestarts(current) if line > 0)
                    pending.extend(c for c in current.co_consts if isinstance(c, types.CodeType))
                executable = lines.intersection(target["changed_lines"])
                row.update(status="collected", executable=sorted(executable))
                self.targets[str(path)] = (row, executable, set(), path, target["file_hash"])
            except (OSError, SyntaxError, ValueError):
                row["reason"] = "source_unavailable_or_uncompilable"

    def _trace(self, frame, event, arg):
        del arg
        target = self.targets.get(frame.f_code.co_filename)
        if target is None:
            return None
        if event == "line" and frame.f_lineno in target[1]:
            target[2].add(frame.f_lineno)
        return self.trace

    def start(self) -> None:
        if self.previous is None:
            self.settrace(self.trace)

    def finish(self) -> None:
        active = self.previous is None and self.gettrace() is self.trace
        if self.gettrace() is self.trace:
            self.settrace(self.previous)
        for row, _lines, hits, path, expected_hash in self.targets.values():
            try:
                with self.open(path, "rb") as stream:
                    actual_hash = "sha256:" + hashlib.sha256(stream.read()).hexdigest()
                    unchanged = actual_hash == expected_hash
            except OSError:
                unchanged = False
            if not active or not unchanged:
                row.update(status="unknown", reason="trace_or_source_changed", executed=[])
            else:
                row["executed"] = sorted(hits)
        report = {"request_hash": self.request["request_hash"], "files": self.rows}
        # A missing report is unknown; never replace the check's exit status.
        with suppress(OSError):
            self.write(2, marker(self.request) + json.dumps(report, separators=(",", ":")).encode()
                       + b"\n")


def main() -> None:
    request_path, root, mode, *arguments = sys.argv[1:]
    request = json.loads(Path(request_path).read_bytes())
    collector = LineTrace(request, root)
    # Match Python -c/-m/script argv, import path and __main__, not wrapper globals.
    sys.path[0] = os.getcwd()
    collector.start()
    try:
        if mode == "-c":
            sys.argv = ["-c", *arguments[1:]]
            namespace = types.ModuleType("__main__")
            sys.modules["__main__"] = namespace
            exec(compile(arguments[0], "<string>", "exec"), namespace.__dict__)
        elif mode == "-m":
            sys.argv = [arguments[0], *arguments[1:]]
            runpy.run_module(arguments[0], run_name="__main__", alter_sys=True)
        else:
            sys.argv = [mode, *arguments]
            sys.path[0] = str(Path(mode).resolve().parent)
            runpy.run_path(mode, run_name="__main__")
    finally:
        collector.finish()


if __name__ == "__main__":
    main()
