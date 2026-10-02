"""Operator-only pinned SWE-bench controls; execute with the isolated harness Python."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


def restore_transport_bytes(path: Path, expected: bytes):
    """Undo only host newline conversion; never edit the upstream script or patch."""
    actual = path.read_bytes()
    if actual != expected and actual.replace(b"\r\n", b"\n") != expected:
        raise ValueError("native transport content differs beyond host newlines")
    path.write_bytes(expected)


def load_predictions(path: Path, allowed: set[str]):
    predictions = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        item = json.loads(line)
        identity = item["instance_id"]
        if identity not in allowed or identity in predictions:
            raise ValueError("unknown or duplicate prediction instance")
        if not isinstance(item.get("model_patch"), str) or not item["model_patch"].strip():
            raise ValueError("native evaluation requires a submitted nonempty patch")
        predictions[identity] = item["model_patch"]
    if not predictions:
        raise ValueError("no submitted predictions")
    return predictions


def run(rows_path: Path, output: Path, predictions_path: Path | None = None):
    # Disable upstream dotenv loading only in the evaluator process.
    os.environ["PYTHON_DOTENV_DISABLED"] = "1"
    from swebench.harness import run_evaluation
    from swebench.harness.constants import LOG_TEST_OUTPUT, RUN_EVALUATION_LOG_DIR
    from swebench.harness.grading import get_logs_eval, parse_test_exit_code
    from swebench.harness.run_evaluation import run_instance
    from swebench.harness.utils import make_test_spec

    import docker

    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    rows = json.loads(rows_path.read_text(encoding="utf-8"))
    allowed_images = {row["image"] for row in rows}
    if len(rows) != 3 or any("@sha256:" not in image for image in allowed_images):
        raise ValueError("three digest-pinned instances required")
    predictions = (
        load_predictions(predictions_path, {row["instance_id"] for row in rows})
        if predictions_path is not None else None
    )
    os.chdir(output)
    raw_client = docker.from_env(timeout=60)
    created = []
    original_copy = run_evaluation.copy_to_container
    expected_files = {}

    def copy_exact(container, source, destination):
        source = Path(source)
        if source.name in expected_files:
            restore_transport_bytes(source, expected_files[source.name])
        return original_copy(container, source, destination)

    run_evaluation.copy_to_container = copy_exact

    class Images:
        def get(self, image):
            if image not in allowed_images:
                raise ValueError("image outside pilot")
            return raw_client.images.get(image)

        def pull(self, *_args, **_kwargs):
            raise RuntimeError("native evaluator may not acquire images")

    class Containers:
        def get(self, name):
            # Upstream looks for an old named container before creating a new one.
            # A collision must not delete or reuse any previous work.
            existing = raw_client.containers.get(name)
            if existing.id not in created:
                raise RuntimeError("unexpected pre-existing container")
            return existing

        def create(self, **kwargs):
            if kwargs["image"] not in allowed_images:
                raise ValueError("image outside pilot")
            kwargs.pop("cap_add", None)
            kwargs.update(
                network_mode="none",
                cap_drop=["ALL"],
                security_opt=["no-new-privileges:true"],
                mem_limit="2g",
                nano_cpus=2_000_000_000,
                pids_limit=128,
            )
            container = raw_client.containers.create(**kwargs)
            created.append(container.id)
            return container

    class Client:
        images = Images()
        containers = Containers()
        api = raw_client.api

    summaries = []
    try:
        for row in rows:
            if predictions is not None and row["instance_id"] not in predictions:
                continue
            spec = make_test_spec(row)
            for mode in (("agent",) if predictions is not None else ("base", "reference")):
                run_id = "lite-dev-controls-" + mode
                pred = {
                    "instance_id": row["instance_id"],
                    "model_name_or_path": mode,
                    "model_patch": (
                        predictions[row["instance_id"]] if predictions is not None
                        else "" if mode == "base" else row["patch"]
                    ),
                }
                expected_files.clear()
                expected_files.update(
                    {
                        "eval.sh": spec.eval_script.encode("utf-8"),
                        "patch.diff": pred["model_patch"].encode("utf-8"),
                    }
                )
                print(f"Starting {row['instance_id']} {mode}", flush=True)
                result = run_instance(
                    spec,
                    pred,
                    Client(),
                    run_id,
                    timeout=300,
                    skip_patch=mode == "base",
                )
                log = (
                    output
                    / RUN_EVALUATION_LOG_DIR
                    / run_id
                    / mode
                    / row["instance_id"]
                    / LOG_TEST_OUTPUT
                )
                # Do not interpret a missing test as an ordinary wrong answer.
                statuses, found = get_logs_eval(spec, str(log)) if log.is_file() else ({}, False)
                required = spec.FAIL_TO_PASS + spec.PASS_TO_PASS
                missing = [case for case in required if case not in statuses]
                test_exit = parse_test_exit_code(log.read_text()) if log.is_file() else None
                report = result[1][row["instance_id"]] if result else {}
                complete = bool(found and not missing and test_exit in (0, 1))
                expected = complete and (
                    predictions is not None or report.get("resolved") is (mode == "reference")
                )
                summary = {
                    "instance_id": row["instance_id"],
                    "mode": mode,
                    "resolved": report.get("resolved"),
                    "complete": complete,
                    "missing_count": len(missing),
                    "test_exit": test_exit,
                    "expected_result": expected,
                    "reported_cases": len(statuses),
                    "required_cases": len(required),
                }
                summaries.append(summary)
                print(json.dumps(summary), flush=True)
                (output / f"control-{len(summaries)}.json").write_text(
                    json.dumps(summary, indent=2),
                    encoding="utf-8",
                )
                if not expected:
                    raise RuntimeError("original calibration gate failed; stop without retuning")
        return summaries
    finally:
        run_evaluation.copy_to_container = original_copy
        remaining = []
        for identity in created:
            try:
                raw_client.containers.get(identity)
                remaining.append(identity)
            except docker.errors.NotFound:
                pass
        (output / "cleanup.json").write_text(
            json.dumps(
                {
                    "created": created,
                    "remaining": remaining,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        raw_client.close()
        if remaining:
            raise RuntimeError("native control container cleanup unconfirmed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--predictions", type=Path)
    args = parser.parse_args()
    run(args.rows.resolve(), args.output, args.predictions)
