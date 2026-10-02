"""Private registered-check adapter; copied into audited task packages only."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import types
from pathlib import Path


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
            print(json.dumps({"status": "ERROR", "reason": "original_test_patch_apply"}))
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
        except subprocess.TimeoutExpired:
            print(json.dumps({"status": "ERROR", "reason": "original_tests_timeout"}))
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
        statuses, found = get_logs_eval(spec, str(log))
        missing = [case for case in spec.FAIL_TO_PASS + spec.PASS_TO_PASS if case not in statuses]
        report = get_eval_report(
            spec,
            {"instance_id": spec.instance_id, "model_patch": "submitted-workspace"},
            str(log),
            include_tests_status=True,
        )[spec.instance_id]
        complete = found and not missing and result.returncode in (0, 1)
        print(
            json.dumps(
                {
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
