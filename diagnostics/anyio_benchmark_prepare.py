"""Prepare evaluator-only original-benchmark inputs; never run tests or a model."""

from __future__ import annotations

import argparse
import json
import subprocess
import urllib.request
import uuid
from pathlib import Path

from patchloop.artifacts import ArtifactStore
from patchloop.dev.state import DevJournal
from patchloop.runtime import repository_root
from patchloop.util import sha256_bytes

REVISION = "ab4805dae879e4f4ef81bf9e5cf5afa849f7c55b"
PARQUET_HASH = "sha256:18e198ac18b3c25b307c0aa5d9b6e20d338886e186bf7c12addb759ad4165a61"
HARNESS = "e4907b7a90eafaa1f0a6428fd04fe31cdd8b4284"
INSTANCE = "agronholm__anyio-1121"
BASE = "cb245dba9883516f2ed4c23899de157183a1cb50"
IMAGE = "sha256:063bb968109c70a3fe617d9d30287a3a43d549eb1091b27a030a9af2a74c2320"
IMAGE_REPO = "swerebench/sweb.eval.x86_64.agronholm_1776_anyio-1121"
FILES = (
    "swebench/harness/log_parsers/python.py",
    "swebench/harness/grading.py",
    "swebench/harness/test_spec/test_spec.py",
)
ENV_PROGRAM = """
import importlib.metadata as m, importlib.util, json, sys, subprocess
names = ['pytest', 'trio', 'uvloop', 'hypothesis', 'blockbuster', 'coverage',
         'pytest-mock', 'pytest-timeout', 'trustme', 'truststore', 'psutil']
def version(name):
    try: return m.version(name)
    except m.PackageNotFoundError: return None
def git(*args):
    r = subprocess.run(['git', '-C', '/testbed', *args], capture_output=True, text=True)
    return {'returncode': r.returncode, 'stdout': r.stdout.strip()}
print(json.dumps({'python': sys.version, 'executable': sys.executable,
    'packages': {n: version(n) for n in names},
    'anyio_origin': importlib.util.find_spec('anyio').origin,
    'head': git('rev-parse', 'HEAD'), 'tracked_status': git('status', '--porcelain', '-uno')}))
"""


def partition(row):
    """Explicit allowlist prevents benchmark answers entering an agent packet."""
    if row["instance_id"] != INSTANCE or row["base_commit"] != BASE:
        raise ValueError("benchmark identity mismatch")
    f2p, p2p = row["FAIL_TO_PASS"], row["PASS_TO_PASS"]
    if len(f2p) != 1 or len(p2p) != 32 or len(set(f2p + p2p)) != 33:
        raise ValueError("benchmark case membership mismatch")
    public = {k: row[k] for k in ("instance_id", "repo", "base_commit", "problem_statement")}
    private = {
        k: row[k]
        for k in (
            "test_patch",
            "patch",
            "FAIL_TO_PASS",
            "PASS_TO_PASS",
            "install_config",
            "environment_setup_commit",
            "docker_image",
        )
    }
    return public, private


def fetch(url):
    with urllib.request.urlopen(url, timeout=30) as response:
        return response.read()


def command(args):
    result = subprocess.run(args, capture_output=True, text=True, timeout=45)
    return {
        "argv": args,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def prepare(output):
    # Optional offline-analysis dependency; do not add it to the agent runtime.
    import pyarrow as pa
    import pyarrow.parquet as pq

    output = output.resolve()
    if output.is_relative_to(repository_root()) or repository_root().is_relative_to(output):
        raise ValueError("output must be outside the repository")
    output.mkdir(exist_ok=False)
    journal = DevJournal(output, "run_dev_originalbenchmarkprepare")
    store = ArtifactStore(output / "evaluator-artifacts")

    def record(kind, payload):
        journal.append(kind, {"artifact": store.put_json(payload).model_dump(mode="json")})

    journal.append(
        "preparation_started",
        {
            "official": False,
            "instance": INSTANCE,
            "script_hash": sha256_bytes(Path(__file__).read_bytes()),
        },
    )
    url = (
        f"https://huggingface.co/datasets/nebius/SWE-rebench-leaderboard/resolve/"
        f"{REVISION}/data/2026_03-00000-of-00001.parquet"
    )
    raw = fetch(url)
    if sha256_bytes(raw) != PARQUET_HASH:
        raise ValueError("pinned dataset hash mismatch")
    columns = [
        "instance_id",
        "repo",
        "base_commit",
        "problem_statement",
        "test_patch",
        "patch",
        "FAIL_TO_PASS",
        "PASS_TO_PASS",
        "install_config",
        "environment_setup_commit",
        "docker_image",
    ]
    rows = pq.read_table(pa.BufferReader(raw), columns=columns).to_pylist()
    (row,) = [r for r in rows if r["instance_id"] == INSTANCE]
    public, private = partition(row)
    record(
        "original_inputs_pinned",
        {
            "dataset_url": url,
            "dataset_hash": PARQUET_HASH,
            "public": store.put_json(public).model_dump(mode="json"),
            "evaluator_only": store.put_json(private).model_dump(mode="json"),
            "harness_revision": HARNESS,
            "harness_files": {
                p: store.put_bytes(
                    fetch(
                        f"https://raw.githubusercontent.com/SWE-rebench/SWE-bench-fork/{HARNESS}/{p}"
                    )
                ).model_dump(mode="json")
                for p in FILES
            },
        },
    )
    inspection = command(["docker", "image", "inspect", IMAGE])
    record("image_inspected", inspection)
    if inspection["returncode"]:
        raise RuntimeError("local image unavailable; no pull or build attempted")
    (info,) = json.loads(inspection["stdout"])
    if IMAGE_REPO + "@" + IMAGE not in info["RepoDigests"]:
        raise ValueError("image repository digest mismatch")
    name = "patchloop-original-env-" + uuid.uuid4().hex[:12]
    journal.append("environment_inspection_started", {"container": name, "image": IMAGE})
    try:
        result = command(
            [
                "docker",
                "run",
                "--pull=never",
                "--name",
                name,
                "--network=none",
                "--read-only",
                "--cap-drop=ALL",
                "--security-opt=no-new-privileges",
                "--pids-limit=128",
                "--memory=512m",
                "--cpus=1",
                "--entrypoint",
                "/opt/conda/envs/testbed/bin/python",
                IMAGE,
                "-B",
                "-c",
                ENV_PROGRAM,
            ]
        )
        record("environment_inspected", result)
    finally:
        cleanup = command(["docker", "rm", "-f", name])
        record("environment_cleanup", cleanup)
        if cleanup["returncode"]:
            raise RuntimeError("owned container cleanup unconfirmed")
    if result["returncode"]:
        raise RuntimeError("environment inspection failed")
    environment = json.loads(result["stdout"])
    record(
        "preparation_completed",
        {
            "environment": environment,
            "declared_python": private["install_config"]["python"],
            "oracle_execution": "NOT_RUN",
            "parser_execution": "NOT_RUN",
            "model_execution": "NOT_RUN",
            "ready_for_benchmark_score": False,
        },
    )
    print(
        json.dumps(
            {"output": str(output), "environment": environment, "oracle_execution": "NOT_RUN"},
            indent=2,
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    prepare(parser.parse_args().output)
