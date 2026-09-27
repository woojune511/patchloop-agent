"""Freeze a three-repository original-input pilot without tests, answers or model calls."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import yaml

from diagnostics.anyio_benchmark_prepare import PARQUET_HASH, REVISION, command, fetch
from patchloop.artifacts import ArtifactStore
from patchloop.dev.state import DevJournal
from patchloop.runtime import repository_root
from patchloop.util import sha256_bytes

SEED = "patchloop-original-input-pilot-v1"


def select(rows, excluded):
    eligible = [
        r
        for r in rows
        if r["repo"].lower() not in excluded
        and r["install_config"]
        and r["install_config"]["log_parser"] == "parse_log_pytest"
        and r["problem_statement"]
        and r["docker_image"]
    ]
    ranked = sorted(
        eligible,
        key=lambda r: hashlib.sha256((SEED + "\n" + r["instance_id"]).encode()).hexdigest(),
    )
    result, seen = [], set()
    for row in ranked:
        if row["repo"].lower() in seen:
            continue
        result.append(row)
        seen.add(row["repo"].lower())
        if len(result) == 3:
            break
    if len(result) != 3:
        raise ValueError("fewer than three eligible repositories")
    return result, len(eligible)


def run(output):
    import pyarrow as pa
    import pyarrow.parquet as pq

    root, output = repository_root(), output.resolve()
    if output.is_relative_to(root) or root.is_relative_to(output):
        raise ValueError("external output required")
    ledger = root / "data/benchmark-candidate-ledger.csv"
    excluded = {
        r["upstream_repository"].lower()
        for r in csv.DictReader(ledger.read_text(encoding="utf-8-sig").splitlines())
    }
    inputs = {str(ledger.relative_to(root)): sha256_bytes(ledger.read_bytes())}
    for path in sorted((root / "tasks").glob("*/*/public.yaml")):
        public = yaml.safe_load(path.read_text(encoding="utf-8"))
        url = public["repository"]["url"]
        if "github.com/" in url:
            excluded.add(url.split("github.com/", 1)[1].removesuffix(".git").lower())
        inputs[str(path.relative_to(root))] = sha256_bytes(path.read_bytes())
    raw = fetch(
        f"https://huggingface.co/datasets/nebius/SWE-rebench-leaderboard/"
        f"resolve/{REVISION}/data/2026_03-00000-of-00001.parquet"
    )
    if sha256_bytes(raw) != PARQUET_HASH:
        raise ValueError("dataset hash mismatch")
    # Do not decode solution, test patch, hints or test identities during selection.
    columns = [
        "instance_id",
        "repo",
        "base_commit",
        "problem_statement",
        "install_config",
        "docker_image",
    ]
    rows = pq.read_table(pa.BufferReader(raw), columns=columns).to_pylist()
    selected, eligible = select(rows, excluded)
    output.mkdir(exist_ok=False)
    store = ArtifactStore(output / "operator-artifacts")
    journal = DevJournal(output, "run_dev_originalbaselineselection")
    journal.append(
        "selection_started",
        {
            "official": False,
            "driver_hash": sha256_bytes(Path(__file__).read_bytes()),
            "dataset_hash": PARQUET_HASH,
            "exclusion_inputs": inputs,
        },
    )
    summaries = []
    for row in selected:
        inspection = command(["docker", "image", "inspect", row["docker_image"]])
        ref = store.put_json({"row": row, "image_inspection": inspection})
        journal.append("selected_input", {"artifact": ref.model_dump(mode="json")})
        summaries.append(
            {
                "instance": row["instance_id"],
                "base": row["base_commit"],
                "issue_hash": sha256_bytes(row["problem_statement"].encode()),
                "image": row["docker_image"],
                "image_local": inspection["returncode"] == 0,
            }
        )
    result = {
        "seed": SEED,
        "dataset_revision": REVISION,
        "total_rows": len(rows),
        "eligible_rows": eligible,
        "excluded_repositories": sorted(excluded),
        "selected": summaries,
        "model_execution": "NOT_RUN",
        "environment_calibration": "NOT_RUN",
        "execution_authorized": False,
    }
    journal.append(
        "selection_completed", {"artifact": store.put_json(result).model_dump(mode="json")}
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args().output)
