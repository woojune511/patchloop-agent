"""Private registered-check adapter; copied into audited task packages only."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import types
from pathlib import Path

DIAGNOSTIC_STREAM_LIMIT_BYTES = 24_000


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
