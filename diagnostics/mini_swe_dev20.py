"""Prepare/run one pinned mini-SWE-agent baseline on the existing dev20 roster."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

import yaml

from diagnostics import current_dev20, portfolio_dev20
from diagnostics.mini_swe_runtime import (
    MODEL,
    ROW_CAP,
    SOLVER_SECONDS,
    UPSTREAM_REVISION,
    CountedModel,
    PublicContainer,
    command,
    load_upstream,
)
from diagnostics.positive_verification_panel import require, save
from patchloop.artifacts import ArtifactStore
from patchloop.deadline import ExecutionDeadline, ExecutionDeadlineExceeded
from patchloop.dev.state import DevJournal
from patchloop.environment import load_exact_openai_api_key
from patchloop.prepared_source import load_source
from patchloop.repository import WorkspaceManager
from patchloop.runtime import git_commit, repository_root, runtime_content_hash
from patchloop.task_loader import load_public_task, load_task_package
from patchloop.util import canonical_json, sha256_bytes, sha256_json
from patchloop.verifier.policy import verify_dependencies, verify_scope, verify_test_tampering

FILES = (
    "diagnostics/mini_swe_dev20.py",
    "diagnostics/mini_swe_runtime.py",
    "diagnostics/swebench_lite_native.py",
    ".agent/mini-swe-baseline.md",
)
JOURNAL = "run_dev_minidev20"


def file_hash(path):
    return sha256_bytes(Path(path).read_bytes())


def bindings(root):
    paths = {name: repository_root() / name for name in FILES}
    paths.update(
        {
            p.relative_to(repository_root()).as_posix(): p
            for p in (repository_root() / "diagnostics").glob("*.py")
        }
    )
    for directory in ("upstream/src", "python-libs"):
        paths.update(
            {
                p.relative_to(root).as_posix(): p
                for p in (root / directory).rglob("*")
                if p.is_file() and "__pycache__" not in p.parts
            }
        )
    return {name: file_hash(path) for name, path in sorted(paths.items())}


def task_text(public):
    """Only the public contract is accepted by this projection function."""
    return (
        public.issue.title
        + "\n\n"
        + public.issue.description
        + "\n\nPublic task contract (not additional bug hints):\n"
        + canonical_json(
            {
                "constraints": public.constraints.model_dump(mode="json"),
                "visible_checks": [c.model_dump(mode="json") for c in public.visible_checks],
            }
        )
        + "\nThe repository is in /testbed. Dependencies are preinstalled. "
        "Network access is disabled. Temporary reproduction files may be kept in /tmp. "
        "Only your submitted source patch is evaluated.\n"
    )


def prepare(root: Path, live: Path, env_file: Path | None = None):
    require(not (root / "manifest.json").exists() and not live.exists(), "fresh roots required")
    repo = repository_root().resolve()
    credential_file = (env_file or repo / ".env").resolve()
    load_exact_openai_api_key(credential_file)  # validate locally; never export/copy the value
    require(
        not root.is_relative_to(repo)
        and not live.is_relative_to(repo)
        and not root.is_relative_to(live)
        and not live.is_relative_to(root),
        "separate external preparation/live roots required",
    )
    load_upstream(root)
    config = yaml.safe_load(
        (root / "upstream/src/minisweagent/config/benchmarks/swebench.yaml").read_text(
            encoding="utf-8"
        )
    )
    # Keep both prompt templates and observation/error templates byte-for-byte.
    config["agent"].update(
        step_limit=40, cost_limit=1.20, wall_time_limit_seconds=SOLVER_SECONDS, output_path=None
    )
    config["model"].update(model_name=MODEL, model_kwargs={"reasoning_effort": "xhigh"})
    save(root, "config.json", config)
    rows = []
    for entry in portfolio_dev20.baseline()[0]["rows"]:
        public_path = current_dev20.task_path(entry)
        package = load_task_package(public_path.parent)
        public = load_public_task(public_path)
        require(public.split == "dev-train", "dev-train only")
        source, checkout = load_source(
            Path(entry["prepared_source"]),
            public.repository.url,
            public.repository.base_commit,
            expected_hash=entry["source_hash"],
        )
        folder = root / "public" / str(entry["index"])
        folder.mkdir(parents=True, exist_ok=False)
        archive = folder / "source.tar"
        command(
            [
                "git",
                "-C",
                checkout,
                "archive",
                "--format=tar",
                "--output",
                archive,
                source.git_commit,
            ]
        )
        text = task_text(public)
        (folder / "task.txt").write_bytes(text.encode("utf-8"))
        image = json.loads(command(["docker", "image", "inspect", entry["image"]]).stdout)[0]
        require(not image["Config"].get("Volumes"), "image-declared volumes are unsupported")
        rows.append(
            {
                "index": entry["index"],
                "instance_id": entry["instance_id"],
                "task": str(public_path),
                "task_content_hash": package.task_content_hash,
                "base_commit": public.repository.base_commit,
                "source_archive": str(archive),
                "source_archive_hash": file_hash(archive),
                "task_text": str(folder / "task.txt"),
                "task_text_hash": file_hash(folder / "task.txt"),
                "prepared_source": entry["prepared_source"],
                "source_hash": entry["source_hash"],
                "native_row": entry["native_row"],
                "native_row_hash": entry["native_row_hash"],
                "image": entry["image"],
                "image_id": image["Id"],
                "public_module": current_dev20.layout(entry)[2],
            }
        )
    require(len(rows) == 20, "exact 20-task roster required")
    packet = {
        "schema_version": "mini-swe-dev20-v1",
        "official": False,
        "claim_eligible": False,
        "agent": "mini-SWE-agent",
        "version": "2.4.6",
        "revision": UPSTREAM_REVISION,
        "model": MODEL,
        "reasoning_effort": "xhigh",
        "max_output_tokens": 25000,
        "credential_file": str(credential_file),
        "repeat": 1,
        "workers": 1,
        "row_cap_usd": str(ROW_CAP),
        "total_cap_usd": "24.00",
        "max_model_calls": 40,
        "max_shell_actions": 100,
        "solver_seconds": SOLVER_SECONDS,
        "native_evaluation_seconds": 330,
        "accepted_edit_limit": None,
        "retry": False,
        "resume": False,
        "harness_git_commit": git_commit(),
        "runtime_hash": runtime_content_hash(),
        "bindings": bindings(root),
        "config_hash": file_hash(root / "config.json"),
        "native_identity": portfolio_dev20.native_identity(),
        "pricing": portfolio_dev20.price(),
        "rows": rows,
        "live_root": str(live),
        "authorization": "PENDING",
        "comparison": "descriptive external baseline; historical PatchLoop rows only",
        "differences": [
            "upstream linear history and bash tools",
            "no four-edit limit",
            "source-only submission per upstream prompt",
            "one worker",
            "native correctness grading; registered runtime safety NOT_RUN",
        ],
    }
    save(root, "manifest.json", packet)
    digest = sha256_json(packet)
    DevJournal(root, JOURNAL).append(
        "external_panel_prepared", {"packet_hash": digest, "provider_calls": 0}
    )
    return {"packet_hash": digest, "rows": len(rows), "provider_calls": 0}


def validate(root, digest):
    packet = json.loads((root / "manifest.json").read_bytes())
    require(sha256_json(packet) == digest, "packet hash mismatch")
    require(packet["bindings"] == bindings(root), "implementation/dependency drift")
    require(packet["config_hash"] == file_hash(root / "config.json"), "configuration drift")
    require(packet["runtime_hash"] == runtime_content_hash(), "PatchLoop runtime drift")
    require(packet["native_identity"] == portfolio_dev20.native_identity(), "native harness drift")
    require(packet["pricing"] == portfolio_dev20.price(), "pricing drift")
    for row in packet["rows"]:
        require(
            load_task_package(Path(row["task"]).parent).task_content_hash
            == row["task_content_hash"],
            "task package drift",
        )
        for path, digest_name in (
            ("source_archive", "source_archive_hash"),
            ("task_text", "task_text_hash"),
            ("native_row", "native_row_hash"),
        ):
            require(file_hash(row[path]) == row[digest_name], f"{path} drift")
        image = json.loads(command(["docker", "image", "inspect", row["image"]]).stdout)[0]
        require(image["Id"] == row["image_id"], "local image drift")
    return packet


def preflight(root, digest):
    packet = validate(root, digest)
    require(not (root / "preflight.json").exists(), "preflight evidence is immutable")
    results = []
    for row in packet["rows"]:
        env = PublicContainer(
            row, root / "canaries" / str(row["index"]), ExecutionDeadline.from_remaining(120)
        )
        try:
            # Operator-only readiness check. No model, task answer, or hidden test input.
            script = (
                "test ! -e /root/eval.sh && test ! -e /eval.sh && "
                "test ! -e /patch.diff && test ! -e /.patchloop-hidden && "
                "test ! -e /testbed/.patchloop-hidden && "
                'test $(git rev-list --count HEAD) = 1 && test -z "$(git remote)" && '
                f"python -c 'import {row['public_module']}; import pytest; "
                'print("PUBLIC_ENVIRONMENT_READY")\''
            )
            result = env.operator_command(script)
            require(b"PUBLIC_ENVIRONMENT_READY" in result.stdout, "public canary failed")
            inspection = json.loads(command(["docker", "inspect", env.name]).stdout)[0]
            require(not inspection["Mounts"], "unexpected host mount")
            host = inspection["HostConfig"]
            require(host["NetworkMode"] == "none" and host["ReadonlyRootfs"], "sandbox drift")
            results.append(
                {
                    "index": row["index"],
                    "instance_id": row["instance_id"],
                    "image_id": inspection["Image"],
                    "public_environment": "PASS",
                    "inspection_hash": ArtifactStore(root / "artifacts")
                    .put_json(inspection)
                    .content_hash,
                }
            )
        finally:
            env.cleanup()
    receipt = {
        "packet_hash": digest,
        "rows": results,
        "provider_calls": 0,
        "cost_usd": "0",
        "live": "NOT_RUN",
        "requires": ["exact live scope", "isolated bash exception"],
    }
    save(root, "preflight.json", receipt)
    DevJournal(root, JOURNAL).append("external_preflight_passed", {"receipt": sha256_json(receipt)})
    return receipt


def assess_patch(root, row, patch):
    """Fresh host checkout for static policy, then unchanged isolated native grader."""
    source = Path(row["prepared_source"])
    public = load_public_task(row["task"])
    manager = WorkspaceManager(
        repository_root() / "fixtures",
        root / "policy-workspaces",
        prepared_source=source,
        prepared_source_hash=row["source_hash"],
    )
    workspace = manager.create("submitted", public.repository.url, public.repository.base_commit)
    try:
        manager.apply_patch(workspace, patch)
        summary = manager.diff_summary(workspace)
        policy = [
            verify_scope(summary, public.constraints),
            verify_dependencies(summary, public.constraints),
            verify_test_tampering(summary),
        ]  # upstream requires source-only patches
        passed = all(result.passed for result in policy)
    except Exception as exc:
        return {"native": "NOT_RUN", "scope": "FAIL", "error_type": type(exc).__name__}
    if not passed:
        return {
            "native": "NOT_RUN",
            "scope": "FAIL",
            "violations": [v for result in policy for v in result.violations],
        }
    prediction = {
        "instance_id": row["instance_id"],
        "model_name_or_path": "mini-swe-agent",
        "model_patch": patch.read_text(encoding="utf-8"),
    }
    save(root, "predictions.jsonl", prediction)
    with (root / "native.log").open("xb") as log:
        code = subprocess.run(
            [
                str(portfolio_dev20.NATIVE_PYTHON),
                "-X",
                "utf8",
                "-m",
                "diagnostics.swebench_lite_native",
                "--rows",
                row["native_row"],
                "--predictions",
                str(root / "predictions.jsonl"),
                "--output",
                str(root / "native"),
            ],
            cwd=repository_root(),
            env=portfolio_dev20.native_env(),
            stdout=log,
            stderr=subprocess.STDOUT,
            timeout=330,
            check=False,
        ).returncode
    cleanup = json.loads((root / "native/cleanup.json").read_bytes())
    require(not cleanup["remaining"], "native cleanup unconfirmed")
    result = json.loads((root / "native/control-1.json").read_bytes())
    require(code == 0 and result["complete"], "native evaluation failed/incomplete")
    return {
        "native": "PASS" if result["resolved"] else "FAIL",
        "scope": "PASS",
        "native_cleanup": "CONFIRMED",
        "registered": "NOT_RUN",
    }


def run(root, digest):
    from openai import OpenAI

    packet = validate(root, digest)
    approval = json.loads((root / "authorization.json").read_bytes())
    require(
        approval.get("packet_hash") == digest
        and approval.get("live_authorized") is True
        and approval.get("isolated_bash_exception") is True,
        "exact human approval required",
    )
    preflight_receipt = json.loads((root / "preflight.json").read_bytes())
    require(preflight_receipt["packet_hash"] == digest, "preflight does not match packet")
    live = Path(packet["live_root"])
    live.mkdir(parents=True, exist_ok=False)  # no restart/resume/replacement
    journal = DevJournal(live, JOURNAL)
    Agent = load_upstream(root)
    config = json.loads((root / "config.json").read_bytes())
    rows = []
    with (
        journal.execution_lock(),
        OpenAI(
            api_key=load_exact_openai_api_key(packet["credential_file"]),
            max_retries=0,
            base_url="https://api.openai.com/v1",
            timeout=180,
        ) as client,
    ):
        for row in packet["rows"]:
            folder = live / str(row["index"])
            start = time.monotonic()
            deadline = ExecutionDeadline.from_remaining(SOLVER_SECONDS)
            model = CountedModel(client, config["model"], folder, deadline)
            env = None
            result = {
                "index": row["index"],
                "instance_id": row["instance_id"],
                "native": "NOT_RUN",
                "scope": "NOT_RUN",
                "submitted": False,
            }
            stop = False
            try:
                env = PublicContainer(row, folder, deadline)
                agent = Agent(model, env, **config["agent"])
                answer = agent.run(Path(row["task_text"]).read_text(encoding="utf-8"))
                deadline.check()
                result["terminal"] = answer.get("exit_status")
                save(folder, "trajectory.json", agent.serialize())
                if (
                    answer.get("exit_status") == "Submitted"
                    and answer.get("submission", "").strip()
                ):
                    patch = folder / "submitted.patch"
                    patch.write_bytes(answer["submission"].encode("utf-8"))
                    result.update(submitted=True, patch_hash=file_hash(patch))
                env.cleanup()  # no solver process exists when private grading starts
                if result["submitted"]:
                    result.update(assess_patch(folder, row, patch))
            except ExecutionDeadlineExceeded:
                result["terminal"] = "SolverDeadline"
            except Exception as exc:
                result.update(terminal="OperationalStop", error_type=type(exc).__name__)
                stop = True
            finally:
                try:
                    if env is not None:
                        env.cleanup()
                except Exception as exc:
                    result["cleanup_error"] = type(exc).__name__
                    stop = True
                result.update(
                    cost_nanos=model.ledger.spent_nanos,
                    billing_known=not model.uncertain,
                    model_calls=model.calls,
                    elapsed_seconds=time.monotonic() - start,
                )
                rows.append(result)
                save(folder, "result.json", result)
                journal.append("external_row_finished", result)
            print(canonical_json(result), flush=True)
            if stop or model.uncertain:
                break
    completed = {r["index"] for r in rows}
    rows.extend(
        {
            "index": r["index"],
            "instance_id": r["instance_id"],
            "native": "NOT_RUN",
            "terminal": "NOT_STARTED",
            "cost_nanos": None,
        }
        for r in packet["rows"]
        if r["index"] not in completed
    )
    report = {
        "official": False,
        "claim_eligible": False,
        "packet_hash": digest,
        "rows": rows,
        "resolved": sum(r["native"] == "PASS" for r in rows),
        "planned": 20,
        "recorded_cost_nanos": sum(r.get("cost_nanos") or 0 for r in rows),
        "billing_known": all(r.get("billing_known", True) for r in rows),
        "automatic_followup": False,
    }
    save(live, "summary.json", report)
    journal.append("external_panel_finished", {"summary_hash": sha256_json(report)})
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "preflight", "run"))
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--live-root", type=Path)
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--packet-hash")
    args = parser.parse_args()
    root = args.root.resolve()
    if args.command == "prepare":
        require(args.live_root is not None, "--live-root required")
        result = prepare(root, args.live_root.resolve(), args.env_file)
    else:
        require(args.packet_hash is not None, "--packet-hash required")
        result = globals()[args.command](root, args.packet_hash)
    print(canonical_json(result))


if __name__ == "__main__":
    main()
