"""Private registered-check adapter; copied into audited task packages only."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import types
from pathlib import Path

DIAGNOSTIC_STREAM_LIMIT_BYTES = 24_000
DIAGNOSTIC_FAILURE_LIMIT_BYTES = 12_000
DIAGNOSTIC_FAILURE_BLOCK_LIMIT = 8

_UNITTEST_SUMMARY = re.compile(rb"Ran [0-9]+ tests? in [^\r\n]+")


def _header_title(line, delimiters):
    """Split delimiter runs without backtracking through whitespace-heavy lines."""
    body = line.lstrip(delimiters)
    if len(line) - len(body) < 3:
        return None
    title = body.rstrip(delimiters)
    if len(body) - len(title) < 3:
        return None
    if (len(title) < 3 or title[:1] not in (b" ", b"\t")
            or title[-1:] not in (b" ", b"\t") or b"\r" in title):
        return None
    return title.strip(b" \t")


def _failure_markers(raw):
    # Recognize ordinary, uncolored pytest sections and unittest text reports only.
    # Scan each byte a fixed number of times, independent of delimiter-like output.
    # This is diagnostic selection, independent of the unchanged benchmark parser.
    offset = 0
    separator = None
    while offset < len(raw):
        newline = raw.find(b"\n", offset)
        end = len(raw) if newline < 0 else newline
        line = raw[offset:end].removesuffix(b"\r")
        start = offset
        offset = len(raw) if newline < 0 else newline + 1
        if separator is not None:
            if line.startswith((b"FAIL:", b"ERROR:")) and b"\r" not in line:
                yield "unittest_case", separator
                separator = None
                continue
            yield "unittest_boundary", separator
            separator = None
        if len(line) >= 3 and not line.strip(b"="):
            separator = start
        elif _header_title(line, b"=") in (b"FAILURES", b"ERRORS"):
            yield "pytest_section", start
        elif _header_title(line, b"_") is not None:
            yield "pytest_case", start
        elif _header_title(line, b"=-") is not None:
            yield "pytest_boundary", start
        elif _UNITTEST_SUMMARY.fullmatch(line):
            yield "unittest_boundary", start
    if separator is not None:
        yield "unittest_boundary", separator


def _failure_ranges(raw):
    """Yield byte ranges; captured-output sections are not failure tracebacks."""
    pytest_section = False
    active = None
    for kind, start in _failure_markers(raw):
        if active is not None:
            yield (*active, start, True)
            active = None
        if kind == "pytest_section":
            pytest_section = True
        elif kind == "pytest_case" and pytest_section:
            active = ("pytest", start)
        elif kind == "unittest_case":
            pytest_section = False
            active = ("unittest", start)
        elif kind != "pytest_boundary" or raw[start:start + 1] == b"=":
            pytest_section = False
    if active is not None:
        yield (*active, len(raw), False)


def _failure_capture(raw):
    selected = []
    recognized_count = original_bytes = unclosed_count = 0
    for format_name, start, end, closed in _failure_ranges(raw):
        recognized_count += 1
        original_bytes += end - start
        unclosed_count += not closed
        if len(selected) < DIAGNOSTIC_FAILURE_BLOCK_LIMIT:
            selected.append((format_name, start, end, closed))
    remaining = DIAGNOSTIC_FAILURE_LIMIT_BYTES
    blocks = []
    for index, (format_name, start, end, closed) in enumerate(selected):
        allowance = remaining // (len(selected) - index)
        retained = min(end - start, allowance)
        remaining -= retained
        if retained == end - start:
            ranges = [(start, end)]
        else:
            # Keep both the test/source context and the exception/assertion end.
            head = (retained + 1) // 2
            ranges = [(start, start + head), (end - (retained - head), end)]
        blocks.append({
            "format": format_name,
            "start_byte": start,
            "end_byte": end,
            "closed_by_marker": closed,
            "original_bytes": end - start,
            "retained_bytes": retained,
            "omitted_bytes": end - start - retained,
            "segments": [{
                "start_byte": left,
                "end_byte": right,
                "encoding": "base64",
                "content": base64.b64encode(raw[left:right]).decode("ascii"),
            } for left, right in ranges],
        })
    retained_bytes = DIAGNOSTIC_FAILURE_LIMIT_BYTES - remaining
    return {
        "recognition": "pytest-sections-unittest-uncolored-text-v1",
        "coverage": "recognized-blocks-only" if recognized_count else "no-recognized-blocks",
        "recognized_block_count": recognized_count,
        "retained_block_count": len(blocks),
        "omitted_block_count": recognized_count - len(blocks),
        "truncated_block_count": sum(block["omitted_bytes"] > 0 for block in blocks),
        "unclosed_block_count": unclosed_count,
        "original_bytes": original_bytes,
        "retained_bytes": retained_bytes,
        "omitted_bytes": original_bytes - retained_bytes,
        "blocks": blocks,
    }


def execution_log(stage, stdout, stderr):
    """Keep private diagnostics in the evaluator receipt, never in solver feedback."""
    streams = {}
    for name, value in (("stdout", stdout), ("stderr", stderr)):
        raw = value if isinstance(value, bytes) else (value or "").encode("utf-8")
        kept = raw[-DIAGNOSTIC_STREAM_LIMIT_BYTES:]
        streams[name] = {
            "encoding": "base64",
            "content": base64.b64encode(kept).decode("ascii"),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "original_bytes": len(raw),
            "retained_bytes": len(kept),
            "omitted_prefix_bytes": len(raw) - len(kept),
            "failure_capture": _failure_capture(raw),
        }
    return {"schema": "private-evaluation-log-v1", "stage": stage, **streams}


def main():
    hidden = Path(__file__).resolve().parent
    sys.path.insert(0, str(hidden / "vendor"))
    # Import the unchanged grading functions and the selected Python parser without
    # upstream package initializers importing Docker/cloud/other-language adapters.
    for name in ("swebench.harness", "swebench.harness.log_parsers"):
        module = types.ModuleType(name)
        module.__path__ = [str(hidden / "vendor" / name.replace(".", "/"))]
        sys.modules[name] = module
    from swebench.harness.log_parsers import python as parsers

    oracle = json.loads((hidden / "oracle.json").read_text())
    parser_name = oracle["spec"]["log_parser"]
    sys.modules["swebench.harness.log_parsers"].PARSER_REGISTRY = {
        parser_name: getattr(parsers, parser_name),
    }
    from swebench.harness.constants import END_TEST_OUTPUT, START_TEST_OUTPUT, TEST_EXIT_CODE
    from swebench.harness.grading import get_eval_report, get_logs_eval
    from swebench.types import TestSpec

    spec = TestSpec(**oracle["spec"])
    with tempfile.TemporaryDirectory(prefix="lite-oracle-") as temporary:
        checkout = Path(temporary) / "repo"
        shutil.copytree(
            Path.cwd(),
            checkout,
            ignore=shutil.ignore_patterns(".git", ".patchloop-hidden", "__pycache__"),
        )
        applied = subprocess.run(
            ["git", "apply", "--whitespace=nowarn", "-"],
            input=oracle["test_patch"],
            cwd=checkout,
            text=True,
            capture_output=True,
        )
        if applied.returncode:
            print(json.dumps({
                "execution_log": execution_log("test_patch", applied.stdout, applied.stderr),
                "status": "ERROR", "reason": "original_test_patch_apply",
            }))
            return 2
        environment = dict(os.environ)
        environment["PYTHONPATH"] = os.pathsep.join([str(checkout / "src"), str(checkout)])
        environment["PATH"] = "/opt/miniconda3/envs/testbed/bin:" + environment["PATH"]
        try:
            result = subprocess.run(
                ["/opt/miniconda3/envs/testbed/bin/python", "-m", *oracle["test_command"]],
                cwd=checkout,
                env=environment,
                text=True,
                capture_output=True,
                timeout=240,
            )
        except subprocess.TimeoutExpired as error:
            print(json.dumps({
                "execution_log": execution_log("timeout", error.stdout, error.stderr),
                "status": "ERROR", "reason": "original_tests_timeout",
            }))
            return 2
        log = Path(temporary) / "test-output.txt"
        log.write_text(
            START_TEST_OUTPUT
            + "\n"
            + result.stdout
            + result.stderr
            + "\n"
            + END_TEST_OUTPUT
            + "\n"
            + TEST_EXIT_CODE
            + ": "
            + str(result.returncode)
            + "\n"
        )
        try:
            statuses, found = get_logs_eval(spec, str(log))
            required = spec.FAIL_TO_PASS + spec.PASS_TO_PASS
            missing = [case for case in required if case not in statuses]
            report = get_eval_report(
                spec,
                {"instance_id": spec.instance_id, "model_patch": "submitted-workspace"},
                str(log),
                include_tests_status=True,
            )[spec.instance_id]
        except Exception as error:
            print(json.dumps({
                "execution_log": execution_log("grading", result.stdout, result.stderr),
                "status": "ERROR", "reason": type(error).__name__, "detail": str(error),
            }))
            return 2
        complete = found and not missing and result.returncode in (0, 1)
        print(
            json.dumps(
                {
                    "execution_log": execution_log("tests", result.stdout, result.stderr),
                    "resolved": report["resolved"],
                    "complete": complete,
                    "test_exit": result.returncode,
                    "missing_count": len(missing),
                    "reported_count": len(statuses),
                    "report": report,
                }
            )
        )
        return (0 if report["resolved"] else 1) if complete else 2


if __name__ == "__main__":
    try:
        exit_code = main()
    except Exception as error:
        print(json.dumps({"status": "ERROR", "reason": type(error).__name__, "detail": str(error)}))
        exit_code = 2
    raise SystemExit(exit_code)
