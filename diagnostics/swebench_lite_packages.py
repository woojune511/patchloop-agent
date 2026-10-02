"""Prepare pilot packages from frozen data and compare registered/native controls."""

from __future__ import annotations

import argparse
import json
import shlex
import shutil
from pathlib import Path

import yaml

from patchloop.artifacts import ArtifactStore
from patchloop.contracts import RegisteredCheck
from patchloop.dev.state import DevJournal
from patchloop.repository import WorkspaceManager
from patchloop.runtime import repository_root
from patchloop.sandbox.runner import DockerSandbox
from patchloop.task_loader import load_task_package
from patchloop.util import sha256_bytes

PUBLIC_RUNNER = """import os, shutil, subprocess, sys, tempfile
from pathlib import Path
with tempfile.TemporaryDirectory(prefix="lite-public-") as temporary:
    checkout = Path(temporary) / "repo"
    shutil.copytree(Path.cwd(), checkout,
                   ignore=shutil.ignore_patterns(".git", ".patchloop-hidden", "__pycache__"))
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join([str(checkout / "src"), str(checkout)])
    env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env["PATH"]
    env["HOME"] = temporary
    result = subprocess.run([sys.executable, "-m", "pytest", "-q", *sys.argv[1:]],
                            cwd=checkout, env=env)
    raise SystemExit(result.returncode)
"""

LAYOUTS = {
    "pylint-dev/astroid": ("astroid", ("tests",)),
    # The public issue names JSON conversion and SQ elements. These are existing
    # public regression modules, selected without private test membership.
    "pydicom/pydicom": (
        "pydicom", ("pydicom/tests/test_json.py", "pydicom/tests/test_sequence.py"),
    ),
    "marshmallow-code/marshmallow": ("src/marshmallow", ("tests",)),
}


def build_package(row, target: Path, upstream: Path, *, source_roots=None,
                  public_pytest_args=None):
    """Build an external package with public checks supplied independently of the oracle."""
    if (source_roots is None) != (public_pytest_args is None):
        raise ValueError("supply both public source roots and check arguments")
    root = repository_root()
    task_id = "swebench-lite-dev-" + row["instance_id"].replace("__", "-")
    warning_options_override = False
    vendor_paths = [
        "__init__.py",
        "types.py",
        "harness/constants/__init__.py",
        "harness/grading.py",
        "harness/infra_failure.py",
        "harness/log_parsers/python.py",
    ]
    target.mkdir(parents=True, exist_ok=False)
    hidden = target / "hidden"
    hidden.mkdir(exist_ok=True)
    license_path = next(
        (upstream.parent / "swebench-5.0.2.dist-info/licenses").glob("LICENSE*")
    )
    shutil.copyfile(license_path, hidden / "SWE-bench-LICENSE")
    for name in vendor_paths:
        dest = hidden / "vendor/swebench" / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((upstream / name).read_bytes())
    shutil.copyfile(root / "diagnostics/swebench_lite_oracle.py", hidden / "run_oracle.py")
    # Derive only private command metadata from the original evaluation script.
    commands = [
        shlex.split(line)
        for line in row["eval_script"].splitlines()
        if line.startswith("pytest ")
    ]
    if len(commands) != 1:
        raise ValueError("pilot requires one original pytest command")
    spec = {
        k: row[k]
        for k in (
            "instance_id",
            "image",
            "repo",
            "version",
            "FAIL_TO_PASS",
            "PASS_TO_PASS",
            "log_parser",
            "eval_type",
        )
    }
    spec["eval_script_list"] = []
    (hidden / "oracle.json").write_text(
        json.dumps(
            {
                "spec": spec,
                "test_patch": row["test_patch"],
                "test_command": commands[0],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (target / "reference.patch").write_bytes(row["patch"].encode("utf-8"))
    if source_roots is None or public_pytest_args is None:
        source_root, tests_roots = LAYOUTS[row["repo"]]
        source_roots = [source_root]
        public_pytest_args = list(tests_roots)
    else:
        warning_options_override = True
    warning_options = [] if warning_options_override else (
        [
            "-W",
            "ignore:pkg_resources is deprecated as an API:DeprecationWarning",
            "-W",
            "ignore:Deprecated call to `pkg_resources.declare_namespace:DeprecationWarning",
        ]
        if row["repo"] == "pylint-dev/astroid"
        else []
    )
    public = {
        "schema_version": "task-public-v1",
        "task_id": task_id,
        "task_version": 1,
        "split": "dev-train",
        "repository": {
            "url": "https://github.com/" + row["repo"] + ".git",
            "base_commit": row["base_commit"],
            "language": "python",
        },
        "issue": {
            "title": row["problem_statement"].splitlines()[0],
            "description": row["problem_statement"],
        },
        "constraints": {
            "allowed_paths": [source_root + "/**" for source_root in source_roots],
            "forbidden_paths": ["tests/**", "test/**", "**/tests/**", ".patchloop-hidden/**"],
            "max_changed_files": 4,
            "max_diff_lines": 1000,
            "dependency_changes_allowed": False,
            "public_api_changes_allowed": True,
        },
        "visible_checks": [
            {
                "id": "base-regression",
                "command": [
                    "/opt/miniconda3/envs/testbed/bin/python",
                    "-B",
                    "-c",
                    PUBLIC_RUNNER,
                    *public_pytest_args,
                    *warning_options,
                ],
                "timeout_seconds": 300,
                "environment": {"PYTHONPATH": "/workspace"},
            }
        ],
        "tags": ["swebench-lite", "dev", "original-input", "development"],
    }
    private = {
        "schema_version": "task-private-v2",
        "task_id": task_id,
        "task_version": 1,
        "hidden_checks": [
            {
                "id": "original-oracle",
                "command": [
                    "/opt/miniconda3/bin/python",
                    "-B",
                    ".patchloop-hidden/run_oracle.py",
                ],
                "timeout_seconds": 300,
                "infrastructure_exit_codes": [2],
            }
        ],
        "hidden_artifacts": [
            {"path": p.relative_to(target).as_posix(), "sha256": sha256_bytes(p.read_bytes())}
            for p in sorted(hidden.rglob("*"))
            if p.is_file()
        ],
        "reference_patch": {
            "path": "reference.patch",
            "sha256": sha256_bytes((target / "reference.patch").read_bytes()),
        },
        "audit": {},
    }
    environment = {
        "schema_version": "task-environment-v1",
        "evaluator_image": row["image"],
        "image_digest": row["image"].split("@")[1],
    }
    for filename, content in [
        ("public.yaml", public),
        ("private.yaml", private),
        ("environment.yaml", environment),
    ]:
        (target / filename).write_text(
            yaml.safe_dump(content, sort_keys=False), encoding="utf-8"
        )
    return load_task_package(target)


def run(prepared: Path, output: Path):
    prepared, output = prepared.resolve(), output.resolve()
    root = repository_root()
    if output.is_relative_to(root) or root.is_relative_to(output):
        raise ValueError("external output required")
    output.mkdir(parents=True, exist_ok=False)
    store = ArtifactStore(output / "evaluator-artifacts")
    journal = DevJournal(output, "run_dev_swebenchlitepackages")

    def record(kind, value):
        journal.append(kind, {"artifact": store.put_json(value).model_dump(mode="json")})

    record(
        "package_preparation_started",
        {
            "driver_hash": sha256_bytes(Path(__file__).read_bytes()),
            "model_calls": 0,
            "scope": "three dev tasks; no test split",
        },
    )
    controls = prepared / "native-controls-lf"
    observed = [json.loads((controls / f"control-{i}.json").read_text()) for i in range(1, 7)]
    if not all(r["expected_result"] for r in observed):
        raise ValueError("original native controls must pass first")
    rows = json.loads((prepared / "evaluator-artifacts/selected-rows.json").read_text())
    upstream = prepared / "harness-venv/Lib/site-packages/swebench"
    for row in rows:
        task_id = "swebench-lite-dev-" + row["instance_id"].replace("__", "-")
        target = output / "draft-packages" / task_id
        package = build_package(row, target, upstream)
        hidden = target / "hidden"
        public = package.public.model_dump(mode="json")
        source = prepared / "sources-lf" / row["instance_id"] / "prepared-source.json"
        manager = WorkspaceManager(
            root / "fixtures",
            output / "workspaces",
            prepared_source=source,
            prepared_source_hash=sha256_bytes(source.read_bytes()),
        )
        sandbox = DockerSandbox(row["image"])
        for label in ("base", "reference"):
            workspace = manager.create(
                task_id + "-" + label, public["repository"]["url"], row["base_commit"]
            )
            if label == "reference":
                manager.apply_patch(workspace, target / "reference.patch")
            visible = sandbox.run_check(
                workspace, RegisteredCheck.model_validate(public["visible_checks"][0])
            )
            # A separate, never solver-mounted checkout receives the private assets.
            shutil.copytree(hidden, workspace / ".patchloop-hidden")
            secret = sandbox.run_check(workspace, package.private.hidden_checks[0])
            record(
                "registered_control",
                {
                    "instance": row["instance_id"],
                    "label": label,
                    "public": visible.__dict__,
                    "private": secret.__dict__,
                    "package_hash": package.task_content_hash,
                },
            )
            print(
                json.dumps(
                    {
                        "instance": row["instance_id"],
                        "label": label,
                        "public_exit": visible.exit_code,
                        "private_exit": secret.exit_code,
                    }
                ),
                flush=True,
            )
            try:
                summary = json.loads(secret.stdout)
            except ValueError:
                summary = {}
            if (
                visible.exit_code != 0
                or secret.exit_code != (1 if label == "base" else 0)
                or not summary.get("complete")
                or summary.get("resolved") is not (label == "reference")
            ):
                raise RuntimeError("registered/native calibration mismatch; stop")
        record("package_validated", {"task": task_id, "task_hash": package.task_content_hash})
    record("completed", {"model_calls": 0, "official": False})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.prepared, args.output)
