"""Template copied into private task packages; never exposed to a solving agent."""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def main():
    hidden = Path(__file__).resolve().parent
    oracle = json.loads((hidden / "oracle.json").read_text())
    scoring = {}
    exec(compile((hidden / "scoring.py").read_text(), "<pinned-scoring>", "exec"), scoring)
    with tempfile.TemporaryDirectory(prefix="original-oracle-") as temp:
        checkout = Path(temp) / "repo"
        shutil.copytree(
            Path.cwd(),
            checkout,
            ignore=shutil.ignore_patterns(".git", ".patchloop-hidden", "__pycache__"),
        )
        patch = subprocess.run(
            ["git", "apply", "--whitespace=nowarn", "-"],
            input=oracle["test_patch"],
            text=True,
            cwd=checkout,
            capture_output=True,
        )
        if patch.returncode:
            print(
                json.dumps(
                    {"status": "SETUP_FAILED", "reason": "test_patch_apply", "detail": patch.stderr}
                )
            )
            return 2
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(checkout / "src") + os.pathsep + str(checkout)
        environment["PATH"] = str(Path(sys.executable).parent) + os.pathsep + environment["PATH"]
        try:
            result = subprocess.run(
                shlex.split(oracle["test_cmd"]),
                cwd=checkout,
                env=environment,
                text=True,
                capture_output=True,
                timeout=90,
            )
        except subprocess.TimeoutExpired:
            print(json.dumps({"status": "NOT_RUN", "reason": "test_timeout"}))
            return 2
        statuses = scoring["parse_log_pytest"](result.stdout + result.stderr, None)
        required = oracle["FAIL_TO_PASS"] + oracle["PASS_TO_PASS"]
        missing = [case for case in required if case not in statuses]
        report = scoring["get_eval_tests_report"](statuses, oracle)
        complete = result.returncode in (0, 1) and not missing
        resolution = scoring["get_resolution_status"](report) if complete else "NOT_RUN"
        print(
            json.dumps(
                {
                    "status": resolution,
                    "pytest_exit": result.returncode,
                    "missing": missing,
                    "report": report,
                }
            )
        )
        return 0 if resolution == "RESOLVED_FULL" else (1 if complete else 2)


if __name__ == "__main__":
    raise SystemExit(main())
