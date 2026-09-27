"""Operator-only base/reference calibration of the pinned original AnyIO oracle."""

from __future__ import annotations

import argparse
import ast
import json
import subprocess
import uuid
from pathlib import Path

from diagnostics.anyio_benchmark_prepare import BASE, HARNESS, IMAGE, command, fetch
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact
from patchloop.dev.state import DevJournal
from patchloop.runtime import repository_root
from patchloop.util import sha256_bytes


def selected_source(source, names):
    tree = ast.parse(source)
    nodes = [
        n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in names
    ]
    if {n.name for n in nodes} != set(names):
        raise ValueError("upstream definitions missing")
    return "\n\n".join(ast.get_source_segment(source, n) for n in nodes)


def scoring_source(parser, grading, constants):
    return (
        "from __future__ import annotations\nfrom enum import Enum\n"
        + selected_source(constants, ["TestStatus", "ResolvedStatus", "EvalType"])
        + '\nFAIL_TO_PASS="FAIL_TO_PASS"\nPASS_TO_PASS="PASS_TO_PASS"\n'
        + 'FAIL_TO_FAIL="FAIL_TO_FAIL"\nPASS_TO_FAIL="PASS_TO_FAIL"\n'
        + selected_source(parser, ["parse_log_pytest"])
        + "\n"
        + selected_source(
            grading,
            [
                "test_passed",
                "test_failed",
                "get_eval_tests_report",
                "compute_fail_to_pass",
                "compute_pass_to_pass",
                "get_resolution_status",
            ],
        )
    )


PROGRAM = r"""
import json, os, shlex, subprocess, sys
p = json.load(sys.stdin)
os.chdir('/testbed')
os.environ['PATH'] = '/opt/conda/envs/testbed/bin:' + os.environ['PATH']
def git(args, text=None):
    r = subprocess.run(['git', *args], input=text, text=True, capture_output=True)
    if r.returncode: raise RuntimeError('git step failed: ' + str(args) + r.stderr)
    return r.stdout
assert git(['rev-parse', 'HEAD']).strip() == p['base']
assert not git(['status', '--porcelain', '-uno']).strip()
if p['reference']: git(['apply', '-'], p['private']['patch'])
paths = [line.split('\t')[-1] for line in []]  # populated from test-patch metadata
paths = [line.split('	')[-1] for line in git(
    ['apply', '--numstat', '-'], p['private']['test_patch']).splitlines()]
for path in paths:
    if path.startswith('/') or '..' in path.split('/'): raise ValueError('unsafe patch path')
    exists = subprocess.run(['git', 'cat-file', '-e', p['base'] + ':' + path],
                            capture_output=True).returncode == 0
    if exists: git(['checkout', p['base'], '--', path])
    elif os.path.isfile(path): os.unlink(path)
git(['apply', '-'], p['private']['test_patch'])
args = shlex.split(p['private']['install_config']['test_cmd'])
try:
    r = subprocess.run(args, capture_output=True, text=True, timeout=90)
    print(json.dumps({'returncode': r.returncode, 'stdout': r.stdout,
                      'stderr': r.stderr, 'timed_out': False}))
except subprocess.TimeoutExpired as e:
    print(json.dumps({'returncode': None, 'timed_out': True,
        'stdout': (e.stdout or b'').decode(), 'stderr': (e.stderr or b'').decode()}))
"""


def calibrate(prepared, output):
    prepared, output = prepared.resolve(), output.resolve()
    for protected in (repository_root(), prepared):
        if output.is_relative_to(protected) or protected.is_relative_to(output):
            raise ValueError("output overlaps protected input")
    old = DevJournal(prepared, "run_dev_originalbenchmarkprepare")
    old_hash = sha256_bytes(old.path.read_bytes())
    source = ArtifactStore(prepared / "evaluator-artifacts")

    def read(ref):
        return source.read_bytes(Artifact.model_validate(ref))

    events = old.events()
    if events[-1]["event_type"] != "preparation_completed":
        raise ValueError("preparation incomplete")
    event = next(e for e in events if e["event_type"] == "original_inputs_pinned")
    manifest = json.loads(read(event["payload"]["artifact"]))
    if manifest["harness_revision"] != HARNESS:
        raise ValueError("harness revision changed")
    private = json.loads(read(manifest["evaluator_only"]))
    output.mkdir(exist_ok=False)
    store = ArtifactStore(output / "evaluator-artifacts")
    journal = DevJournal(output, "run_dev_originalbenchmarkcalibration")

    def record(kind, data):
        journal.append(kind, {"artifact": store.put_json(data).model_dump(mode="json")})

    constants = fetch(
        f"https://raw.githubusercontent.com/SWE-rebench/SWE-bench-fork/"
        f"{HARNESS}/swebench/harness/constants/__init__.py"
    ).decode()
    code = scoring_source(
        read(manifest["harness_files"]["swebench/harness/log_parsers/python.py"]).decode(),
        read(manifest["harness_files"]["swebench/harness/grading.py"]).decode(),
        constants,
    )
    record(
        "calibration_prepared",
        {
            "official": False,
            "input_journal_hash": old_hash,
            "driver_hash": sha256_bytes(Path(__file__).read_bytes()),
            "constants": store.put_text(constants).model_dump(mode="json"),
            "scoring_source": store.put_text(code).model_dump(mode="json"),
            "program": store.put_text(PROGRAM).model_dump(mode="json"),
        },
    )
    scoring = {}
    exec(compile(code, "<pinned-upstream-functions>", "exec"), scoring)
    summary = []
    for label in ("BASE", "REFERENCE"):
        name = "patchloop-original-cal-" + uuid.uuid4().hex[:12]
        journal.append("calibration_started", {"label": label, "container": name})
        try:
            r = subprocess.run(
                [
                    "docker",
                    "run",
                    "--pull=never",
                    "--name",
                    name,
                    "--network=none",
                    "--cap-drop=ALL",
                    "--security-opt=no-new-privileges",
                    "--pids-limit=256",
                    "--memory=2g",
                    "--cpus=2",
                    "-i",
                    "--entrypoint",
                    "/opt/conda/envs/testbed/bin/python",
                    IMAGE,
                    "-B",
                    "-c",
                    PROGRAM,
                ],
                input=json.dumps(
                    {"base": BASE, "reference": label == "REFERENCE", "private": private}
                ),
                text=True,
                capture_output=True,
                timeout=115,
            )
            record(
                "container_result",
                {
                    "label": label,
                    "returncode": r.returncode,
                    "stdout": r.stdout,
                    "stderr": r.stderr,
                },
            )
        finally:
            cleanup = command(["docker", "rm", "-f", name])
            record("container_cleanup", cleanup)
            if cleanup["returncode"]:
                raise RuntimeError("cleanup unconfirmed")
        if r.returncode:
            raise RuntimeError("calibration setup failed; see private receipt")
        result = json.loads(r.stdout)
        statuses = scoring["parse_log_pytest"](result["stdout"] + result["stderr"], None)
        report = scoring["get_eval_tests_report"](statuses, private)
        required = private["FAIL_TO_PASS"] + private["PASS_TO_PASS"]
        missing = [n for n in required if n not in statuses]
        row = {
            "label": label,
            "returncode": result["returncode"],
            "timed_out": result["timed_out"],
            "missing_required": len(missing),
            "f2p_pass": len(report["FAIL_TO_PASS"]["success"]),
            "p2p_pass": len(report["PASS_TO_PASS"]["success"]),
            "resolution": scoring["get_resolution_status"](report),
            "extra_nonpassing": {
                k: v for k, v in statuses.items() if k not in required and v != "PASSED"
            },
            "infrastructure_complete": not result["timed_out"]
            and result["returncode"] in (0, 1)
            and not missing,
        }
        record("oracle_result", {"summary": row, "report": report, "statuses": statuses})
        summary.append(row)
    if sha256_bytes(old.path.read_bytes()) != old_hash:
        raise RuntimeError("original journal changed")
    record("calibration_completed", {"rows": summary, "model_execution": "NOT_RUN"})
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    calibrate(args.prepared, args.output)
