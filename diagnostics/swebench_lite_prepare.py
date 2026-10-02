"""Freeze a small SWE-bench Lite dev pilot without model or Docker execution."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import urllib.request
from pathlib import Path

from patchloop.artifacts import ArtifactStore
from patchloop.dev.state import DevJournal
from patchloop.runtime import repository_root
from patchloop.util import sha256_bytes

DATASET = "SWE-bench/SWE-bench_Lite"
REVISION = "b0dde1093fe417d83b7184254edf8199c1f0dff5"
DATASET_PATH = "data/dev-00000-of-00001.parquet"
DATASET_HASH = "sha256:b90bcbfaca1b5f65155500124a977876c264a4003ab384aca4dfc39a54bef89f"
HARNESS = "02e7a74ffd0b707aab73d203fe87bdc7c76afc8e"
SEED = "patchloop-swebench-lite-dev-20261002-v1"
PUBLIC_FIELDS = ("instance_id", "repo", "base_commit", "problem_statement")
PRIVATE_FIELDS = (
    "patch",
    "test_patch",
    "FAIL_TO_PASS",
    "PASS_TO_PASS",
    "eval_script",
    "log_parser",
    "eval_type",
    "image",
    "version",
    "environment_setup_commit",
)
HARNESS_FILES = (
    "pyproject.toml",
    "swebench/types.py",
    "swebench/harness/utils.py",
    "swebench/harness/run_evaluation.py",
    "swebench/harness/grading.py",
    "swebench/harness/log_parsers/python.py",
)


def select_rows(rows, count=3):
    """Selection depends only on IDs and repository diversity, never on answers."""
    ids = [row["instance_id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate instance IDs")
    if count < 1:
        raise ValueError("positive count required")
    ranked = sorted(
        rows,
        key=lambda row: hashlib.sha256((SEED + "\n" + row["instance_id"]).encode()).hexdigest(),
    )
    selected, repos = [], set()
    for row in ranked:
        if row["repo"] not in repos:
            selected.append(row)
            repos.add(row["repo"])
            if len(selected) == count:
                return selected
    raise ValueError("insufficient distinct repositories")


def partition(row):
    public = {key: row[key] for key in PUBLIC_FIELDS}
    private = {key: row[key] for key in PRIVATE_FIELDS}
    for key in ("FAIL_TO_PASS", "PASS_TO_PASS"):
        if isinstance(private[key], str):
            private[key] = json.loads(private[key])
        if not isinstance(private[key], list) or not all(
            isinstance(case, str) for case in private[key]
        ):
            raise ValueError("invalid test membership")
    cases = private["FAIL_TO_PASS"] + private["PASS_TO_PASS"]
    if not private["FAIL_TO_PASS"] or len(cases) != len(set(cases)):
        raise ValueError("empty or overlapping test membership")
    if any(
        not isinstance(private[k], str) or not private[k].strip()
        for k in ("patch", "test_patch", "eval_script", "image")
    ):
        raise ValueError("missing original evaluation material")
    return public, private


def fetch(url):
    with urllib.request.urlopen(url, timeout=30) as response:
        return response.read()


def prepare(output):
    # Optional preparation dependency, not a PatchLoop runtime dependency.
    import pyarrow.parquet as pq

    output = output.resolve()
    root = repository_root().resolve()
    if output.is_relative_to(root) or root.is_relative_to(output):
        raise ValueError("new external output directory required")
    output.mkdir(parents=True, exist_ok=False)
    journal = DevJournal(output, "run_dev_swebenchliteprepare")
    private_store = ArtifactStore(output / "evaluator-artifacts")
    public_store = ArtifactStore(output / "public-artifacts")

    def record(kind, value):
        journal.append(kind, {"artifact": private_store.put_json(value).model_dump(mode="json")})

    record(
        "preparation_started",
        {
            "official": False,
            "dataset": DATASET,
            "revision": REVISION,
            "split": "dev",
            "selection_seed": SEED,
            "selection_count": 3,
            "selection_rule": "sha256(seed + newline + instance_id), first per repository",
            "driver_hash": sha256_bytes(Path(__file__).read_bytes()),
        },
    )
    raw = fetch(f"https://huggingface.co/datasets/{DATASET}/resolve/{REVISION}/{DATASET_PATH}")
    if sha256_bytes(raw) != DATASET_HASH:
        raise ValueError("pinned dataset hash mismatch")
    record("dataset_bound", private_store.put_bytes(raw).model_dump(mode="json"))
    rows = pq.read_table(io.BytesIO(raw)).to_pylist()
    if len(rows) != 23:
        raise ValueError("expected 23 development instances")
    selected = select_rows(rows)
    metadata = []
    for row in selected:
        public, private = partition(row)
        public_ref = public_store.put_json(public).model_dump(mode="json")
        private_ref = private_store.put_json(private).model_dump(mode="json")
        task_id = "swebench-lite-dev-" + row["instance_id"].replace("__", "-")
        record(
            "instance_bound",
            {
                "instance_id": row["instance_id"],
                "public": public_ref,
                "private": private_ref,
                "proposed_task_id": task_id,
            },
        )
        metadata.append(
            {
                "instance_id": row["instance_id"],
                "repo": row["repo"],
                "base_commit": row["base_commit"],
                "image": row["image"],
                "proposed_task_path": "tasks/dev-train/" + task_id,
                "public_artifact": public_ref,
            }
        )
    sources = {}
    for name in HARNESS_FILES:
        content = fetch(f"https://raw.githubusercontent.com/SWE-bench/SWE-bench/{HARNESS}/{name}")
        sources[name] = private_store.put_bytes(content).model_dump(mode="json")
    record("harness_sources_bound", {"revision": HARNESS, "files": sources})
    plan = {
        "status": "PREPARED_NOT_RUN",
        "official": False,
        "claim_eligible": False,
        "dataset": DATASET,
        "revision": REVISION,
        "dataset_hash": DATASET_HASH,
        "split": "dev",
        "harness_revision": HARNESS,
        "instances": metadata,
        "model": "gpt-5.4-mini-2026-03-17",
        "reasoning": "xhigh",
        "max_output_tokens": 25000,
        "repeat_per_task": 1,
        "credential_file": str(root / ".env"),
        "credential_loaded": False,
        "proposed_per_task_cap_usd": "1.20",
        "proposed_invocation_cap_usd": "3.60",
        "limits": {
            "model_calls": 40,
            "actions": 100,
            "accepted_edits": 4,
            "seconds_per_task": 1800,
        },
        "policies": {
            "context": "segmented-v1",
            "segments": "result-or-size-v1",
            "planning": "brief-v1",
            "probes": True,
            "probe_policy": "none",
            "repair_recheck": True,
            "inspection": "protected-v1",
            "cost_admission": "per-call-v1",
        },
        "stop_rules": [
            "zero SDK retries; stop all on count, transport, billing or cleanup uncertainty",
            "no retries, replacement tasks, continuations, budget transfers or test corrections",
            "no live call before exact packages, isolated calibration and cap are authorized",
        ],
        "pending": [
            "authorize acquisition of only the three selected evaluator images; bind digests",
            "implement and validate package/official-evaluator integration",
            "base/reference controls with original tests; no missing-case or setup errors",
            "freeze checked-in dev-train packages and verify public/private boundary",
            "authorize exact three-run USD 3.60 invocation after successful preflight",
        ],
        "evaluation": "unchanged pinned official harness; one final patch per task",
        "test_split_execution": "NOT_RUN; no 300-task invocation authorized",
        "model_calls": 0,
        "container_runs": 0,
        "image_pulls": 0,
    }
    record("preparation_completed", plan)
    # Human-readable projection; the content-addressed journal artifact is authoritative.
    (output / "plan.json").write_text(json.dumps(plan, indent=2), encoding="utf-8")
    journal.events()
    return plan


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = prepare(args.output)
    print(
        json.dumps(
            {
                "status": result["status"],
                "instances": [r["instance_id"] for r in result["instances"]],
                "output": str(args.output.resolve()),
            },
            indent=2,
        )
    )
