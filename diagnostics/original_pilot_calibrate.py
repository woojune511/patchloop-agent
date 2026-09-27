"""Explicitly authorized image acquisition and isolated three-task calibration."""

from __future__ import annotations

import argparse
import json
import subprocess
import uuid
from pathlib import Path

from diagnostics.anyio_benchmark_calibrate import PROGRAM
from diagnostics.anyio_benchmark_prepare import PARQUET_HASH, REVISION, command, fetch
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact
from patchloop.dev.state import DevJournal
from patchloop.runtime import repository_root
from patchloop.util import sha256_bytes

SELECTION = Path("C:/pt/analyses/original-input-pilot-selection-20260927-v1")
CALIBRATION = Path("C:/pt/analyses/anyio-original-benchmark-calibration-20260927-v1")
ENV = """import json,sys,subprocess,importlib.metadata as m
def git(*args):
 r=subprocess.run(['git','-C','/testbed',*args],capture_output=True,text=True)
 return {'code':r.returncode,'stdout':r.stdout.strip()}
print(json.dumps({'python':sys.version,'pytest':m.version('pytest'),
'head':git('rev-parse','HEAD'),'status':git('status','--porcelain','-uno')}))
"""


def run(output):
    import pyarrow as pa
    import pyarrow.parquet as pq

    output = output.resolve()
    for root in (repository_root(), SELECTION, CALIBRATION):
        if output.is_relative_to(root) or root.is_relative_to(output):
            raise ValueError("output overlaps existing evidence")
    output.mkdir(exist_ok=False)
    store = ArtifactStore(output / "evaluator-artifacts")
    journal = DevJournal(output, "run_dev_originalpilotcalibration")

    def record(kind, value):
        journal.append(kind, {"artifact": store.put_json(value).model_dump(mode="json")})

    def read(root, sub, ref):
        return ArtifactStore(root / sub).read_bytes(Artifact.model_validate(ref))

    selection_journal = DevJournal(SELECTION, "run_dev_originalbaselineselection")
    selection = json.loads(
        read(SELECTION, "operator-artifacts", selection_journal.events()[-1]["payload"]["artifact"])
    )
    prior = DevJournal(CALIBRATION, "run_dev_originalbenchmarkcalibration").events()[0]
    prior_data = json.loads(read(CALIBRATION, "evaluator-artifacts", prior["payload"]["artifact"]))
    scoring_code = read(CALIBRATION, "evaluator-artifacts", prior_data["scoring_source"])
    scoring = {}
    exec(compile(scoring_code, "<pinned-upstream-functions>", "exec"), scoring)
    record(
        "authorized_preparation",
        {
            "official": False,
            "paid_authorized": False,
            "selection_hash": sha256_bytes(selection_journal.path.read_bytes()),
            "driver_hash": sha256_bytes(Path(__file__).read_bytes()),
            "container_program": store.put_text(PROGRAM).model_dump(mode="json"),
            "scoring_code": store.put_bytes(scoring_code).model_dump(mode="json"),
            "image_targets": [r["image"] for r in selection["selected"]],
        },
    )
    raw = fetch(
        f"https://huggingface.co/datasets/nebius/SWE-rebench-leaderboard/"
        f"resolve/{REVISION}/data/2026_03-00000-of-00001.parquet"
    )
    assert sha256_bytes(raw) == PARQUET_HASH
    cols = [
        "instance_id",
        "base_commit",
        "problem_statement",
        "patch",
        "test_patch",
        "FAIL_TO_PASS",
        "PASS_TO_PASS",
        "install_config",
    ]
    rows = pq.read_table(pa.BufferReader(raw), columns=cols).to_pylist()
    summaries = []
    for selected in selection["selected"]:
        instance = selected["instance"]
        image = selected["image"]
        (row,) = [r for r in rows if r["instance_id"] == instance]
        assert row["base_commit"] == selected["base"]
        assert sha256_bytes(row["problem_statement"].encode()) == selected["issue_hash"]
        record("oracle_bound", {"instance": instance, "row": row})
        print("Pulling " + image, flush=True)
        journal.append("pull_started", {"image": image})
        pull = subprocess.run(
            ["docker", "pull", image], capture_output=True, text=True, timeout=1200
        )
        record(
            "pull_finished",
            {"image": image, "code": pull.returncode, "stdout": pull.stdout, "stderr": pull.stderr},
        )
        if pull.returncode:
            summaries.append(
                {"instance": instance, "status": "IMAGE_FAILED", "calibration": "NOT_RUN"}
            )
            continue
        info = command(["docker", "image", "inspect", image])
        record("image_bound", info)
        (metadata,) = json.loads(info["stdout"])
        digest = next(d for d in metadata["RepoDigests"] if d.startswith(image.split(":")[0] + "@"))
        print("Bound " + digest, flush=True)

        def container(program, payload=None, *, instance=instance, digest=digest):
            name = "patchloop-pilot-cal-" + uuid.uuid4().hex[:12]
            journal.append(
                "container_started", {"instance": instance, "name": name, "image": digest}
            )
            try:
                result = subprocess.run(
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
                        "--memory=4g",
                        "--cpus=2",
                        "-i",
                        "--entrypoint",
                        "/opt/conda/envs/testbed/bin/python",
                        digest,
                        "-B",
                        "-c",
                        program,
                    ],
                    input=json.dumps(payload),
                    capture_output=True,
                    text=True,
                    timeout=115,
                )
                receipt = {
                    "code": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                }
                record("container_result", receipt)
                return receipt
            except subprocess.TimeoutExpired:
                record("container_timeout", {"name": name})
                return {"code": 124, "stdout": "", "stderr": "outer timeout"}
            finally:
                cleanup = command(["docker", "rm", "-f", name])
                record("container_cleanup", cleanup)
                if cleanup["returncode"]:
                    raise RuntimeError("cleanup uncertain")

        environment = container(ENV)
        if environment["code"]:
            summaries.append(
                {"instance": instance, "status": "ENVIRONMENT_FAILED", "calibration": "NOT_RUN"}
            )
            continue
        env = json.loads(environment["stdout"])
        if env["head"]["stdout"] != selected["base"] or env["status"]["stdout"]:
            summaries.append(
                {"instance": instance, "status": "SOURCE_MISMATCH", "calibration": "NOT_RUN"}
            )
            continue
        for label in ("BASE", "REFERENCE"):
            print(instance + " " + label, flush=True)
            result = container(
                PROGRAM,
                {"base": selected["base"], "reference": label == "REFERENCE", "private": row},
            )
            if result["code"]:
                summaries.append(
                    {
                        "instance": instance,
                        "label": label,
                        "status": "SETUP_FAILED",
                        "correctness": "NOT_RUN",
                    }
                )
                continue
            test = json.loads(result["stdout"])
            statuses = scoring["parse_log_pytest"](test["stdout"] + test["stderr"], None)
            report = scoring["get_eval_tests_report"](statuses, row)
            required = row["FAIL_TO_PASS"] + row["PASS_TO_PASS"]
            complete = (
                not test["timed_out"]
                and test["returncode"] in (0, 1)
                and all(n in statuses for n in required)
            )
            summary = {
                "instance": instance,
                "label": label,
                "digest": digest,
                "python": env["python"],
                "required_complete": complete,
                "exit": test["returncode"],
                "timed_out": test["timed_out"],
                "missing": sum(n not in statuses for n in required),
                "f2p": [len(report["FAIL_TO_PASS"]["success"]), len(row["FAIL_TO_PASS"])],
                "p2p": [len(report["PASS_TO_PASS"]["success"]), len(row["PASS_TO_PASS"])],
                "resolution": scoring["get_resolution_status"](report) if complete else "NOT_RUN",
            }
            record("oracle_result", {"summary": summary, "report": report, "statuses": statuses})
            summaries.append(summary)
            print(json.dumps(summary), flush=True)
    record("calibration_completed", {"rows": summaries, "model_execution": "NOT_RUN"})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--authorized-image-acquisition", action="store_true", required=True)
    run(parser.parse_args().output)
