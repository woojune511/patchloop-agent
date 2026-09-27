"""Build and locally validate three original-input packages, without model calls."""

from __future__ import annotations

import argparse
import json
import re
import shlex
import shutil
import subprocess
from pathlib import Path

import yaml

from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact
from patchloop.dev.state import DevJournal
from patchloop.repository import WorkspaceManager
from patchloop.runtime import repository_root, runtime_content_hash
from patchloop.sandbox.runner import DockerSandbox
from patchloop.task_loader import load_task_package
from patchloop.util import sha256_bytes
from patchloop.verifier.policy import verify_public_api, verify_scope

SOURCE = Path("C:/pt/analyses/original-pilot-calibration-20260927-v1")
SELECTION = Path("C:/pt/analyses/original-input-pilot-selection-20260927-v1")
NAMES = {
    "vprusso__toqito-1538": ("original-toqito-1538", "toqito", "vprusso/toqito"),
    "idaholab__montepy-933_interface": ("original-montepy-933", "montepy", "idaholab/MontePy"),
    "unit8co__darts-3065": ("original-darts-3065", "darts", "unit8co/darts"),
}

PUBLIC_RUNNER = """import os, shutil, subprocess, sys, tempfile
from pathlib import Path
with tempfile.TemporaryDirectory(prefix="public-tests-") as temp:
    checkout = Path(temp) / "repo"
    shutil.copytree(Path.cwd(), checkout,
                   ignore=shutil.ignore_patterns(".git", ".patchloop-hidden", "__pycache__"))
    env = dict(os.environ)
    env["PYTHONPATH"] = str(checkout)
    env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env["PATH"]
    result = subprocess.run([sys.executable, "-m", *sys.argv[1:]], cwd=checkout, env=env)
    raise SystemExit(result.returncode)
"""


def production_patch(patch, source_root):
    chunks = re.split(r"(?=^diff --git )", patch, flags=re.MULTILINE)
    selected = []
    for chunk in chunks:
        match = re.match(r"diff --git a/(.+) b/(.+)\n", chunk)
        if match and match[1] == match[2]:
            path = match[1]
            if path.startswith(source_root + "/") and "/tests/" not in path:
                selected.append(chunk)
    if not selected:
        raise ValueError("no production reference patch")
    return "".join(selected)


def run(output):
    output = output.resolve()
    root = repository_root()
    if output.is_relative_to(root) or root.is_relative_to(output):
        raise ValueError("external output required")
    output.mkdir(exist_ok=False)
    journal = DevJournal(output, "run_dev_originalpilotpackages")
    store = ArtifactStore(output / "evaluator-artifacts")
    old = ArtifactStore(SOURCE / "evaluator-artifacts")
    events = DevJournal(SOURCE, "run_dev_originalpilotcalibration").events()

    def read(event):
        return json.loads(old.read_bytes(Artifact.model_validate(event["payload"]["artifact"])))

    source_data = read(events[0])
    scoring = old.read_bytes(Artifact.model_validate(source_data["scoring_code"]))
    oracles = [read(e) for e in events if e["event_type"] == "oracle_bound"]
    summary = read(events[-1])["rows"]

    def record(kind, value):
        journal.append(kind, {"artifact": store.put_json(value).model_dump(mode="json")})

    record(
        "package_preparation_started",
        {
            "official": False,
            "runtime_hash": runtime_content_hash(),
            "driver_hash": sha256_bytes(Path(__file__).read_bytes()),
        },
    )
    manager = WorkspaceManager(root / "fixtures", output / "workspaces")
    for entry in oracles:
        instance = entry["instance"]
        row = entry["row"]
        name, src, repo = NAMES[instance]
        target = root / "tasks/dev-train" / name
        if target.exists():
            tracked = subprocess.run(
                ["git", "ls-files", "--", str(target)],
                cwd=root,
                capture_output=True,
                text=True,
                check=True,
            )
            if tracked.stdout or load_task_package(target).public.task_id != name:
                raise ValueError("refusing to replace an existing tracked task")
            record(
                "draft_replaced",
                {
                    "task": name,
                    "files": {
                        p.relative_to(target).as_posix(): store.put_bytes(
                            p.read_bytes()
                        ).model_dump(mode="json")
                        for p in target.rglob("*")
                        if p.is_file()
                    },
                },
            )
        image = next(r["digest"] for r in summary if r["instance"] == instance)
        url = "https://github.com/" + repo + ".git"
        print("Preparing " + name, flush=True)
        workspace = manager.create(name, url, row["base_commit"])
        args = shlex.split(row["install_config"]["test_cmd"])
        paths = [a for a in args if a.endswith(".py")]
        assert paths and all((workspace / p).is_file() for p in paths)
        assert (workspace / src).is_dir()
        hidden = target / "hidden"
        hidden.mkdir(parents=True, exist_ok=True)

        def write(path, data, target=target):
            (target / path).write_text(
                yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8"
            )

        public = {
            "schema_version": "task-public-v1",
            "task_id": name,
            "task_version": 1,
            "split": "dev-train",
            "repository": {"url": url, "base_commit": row["base_commit"], "language": "python"},
            "issue": {
                "title": row["problem_statement"].splitlines()[0],
                "description": row["problem_statement"],
            },
            "constraints": {
                "allowed_paths": [src + "/**"],
                "forbidden_paths": ["tests/**", "**/tests/**", ".patchloop-hidden/**"],
                "max_changed_files": 4,
                "max_diff_lines": 1000,
                "dependency_changes_allowed": False,
                "public_api_changes_allowed": True,
            },
            "visible_checks": [
                {
                    "id": "base-regression",
                    "command": [
                        "/opt/conda/envs/testbed/bin/python",
                        "-B",
                        "-c",
                        PUBLIC_RUNNER,
                        *args,
                        *(
                            [
                                "--deselect",
                                paths[0]
                                + "::test_sandwiched_renyi_conditional_entropy_unsupported_uparrow",
                            ]
                            if src == "toqito"
                            else []
                        ),
                    ],
                    "timeout_seconds": 120,
                    "environment": {"PYTHONPATH": "/workspace"},
                }
            ],
            "tags": ["original-input-pilot", "swe-rebench", "development"],
        }
        write("public.yaml", public)
        reference = production_patch(row["patch"], src).encode()
        (target / "reference.patch").write_bytes(reference)
        shutil.copyfile(root / "diagnostics/original_task_oracle.py", hidden / "run_oracle.py")
        (hidden / "scoring.py").write_bytes(scoring)
        (hidden / "oracle.json").write_text(
            json.dumps(
                {
                    "test_patch": row["test_patch"],
                    "test_cmd": row["install_config"]["test_cmd"],
                    "FAIL_TO_PASS": row["FAIL_TO_PASS"],
                    "PASS_TO_PASS": row["PASS_TO_PASS"],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        write(
            "private.yaml",
            {
                "schema_version": "task-private-v2",
                "task_id": name,
                "task_version": 1,
                "hidden_checks": [
                    {
                    "id": "original-oracle",
                    "infrastructure_exit_codes": [2],
                        "command": [
                            "/opt/conda/envs/testbed/bin/python",
                            "-B",
                            ".patchloop-hidden/run_oracle.py",
                        ],
                        "timeout_seconds": 120,
                        "environment": {"PYTHONPATH": "/workspace"},
                    }
                ],
                "hidden_artifacts": [
                    {"path": "hidden/" + p.name, "sha256": sha256_bytes(p.read_bytes())}
                    for p in sorted(hidden.iterdir())
                ],
                "reference_patch": {"path": "reference.patch", "sha256": sha256_bytes(reference)},
                "audit": {},
            },
        )
        write(
            "environment.yaml",
            {
                "schema_version": "task-environment-v1",
                "evaluator_image": image,
                "image_digest": image.split("@")[1],
                "source_image_tag": image.split("@")[0] + ":latest",
            },
        )
        package = load_task_package(target)
        assert package.public.issue.description == row["problem_statement"]
        sandbox = DockerSandbox(image)
        for label in ("BASE", "REFERENCE"):
            if label == "REFERENCE":
                manager.apply_patch(workspace, target / "reference.patch")
            # Public check first: no private material in its mount.
            visible = sandbox.run_check(workspace, package.public.visible_checks[0])
            shutil.copytree(hidden, workspace / ".patchloop-hidden")
            private = sandbox.run_check(workspace, package.private.hidden_checks[0])
            # Remove only our injected test assets from this fresh owned workspace.
            injected = workspace / ".patchloop-hidden"
            if injected.is_symlink() or injected.resolve().parent != workspace.resolve():
                raise ValueError("private injection escaped the owned workspace")
            shutil.rmtree(injected)
            diff = manager.diff_summary(workspace)
            policy = verify_scope(diff, package.public.constraints)
            api = verify_public_api(diff, package.public.constraints, workspace)
            record(
                "package_validation",
                {
                    "task": name,
                    "label": label,
                    "visible": visible.__dict__,
                    "private": private.__dict__,
                    "scope": policy.__dict__,
                    "api": api.__dict__,
                    "diff_lines": diff.diff_lines,
                    "package_hash": package.task_content_hash,
                },
            )
            print(
                json.dumps(
                    {
                        "task": name,
                        "label": label,
                        "visible_exit": visible.exit_code,
                        "private_exit": private.exit_code,
                        "scope": policy.passed,
                        "api": api.passed,
                        "diff_lines": diff.diff_lines,
                        "private_stdout": private.stdout[-180:],
                    }
                ),
                flush=True,
            )
    record("package_preparation_completed", {"model_execution": "NOT_RUN"})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args().output)
