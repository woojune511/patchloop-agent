"""Prepare and measure the current agent on dev20 with two independent workers."""

from __future__ import annotations

import argparse
import ast
import json
import shutil
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from pathlib import Path
from time import monotonic

import yaml

from diagnostics import legacy_probe_metadata, parallel_dev_batch
from diagnostics import portfolio_dev20 as old
from diagnostics.positive_verification_panel import require, save
from patchloop import prepared_probe_dependencies as deps
from patchloop.dev import runner
from patchloop.dev.state import DevJournal
from patchloop.dev.test_selection import SelectedTests, selected_check
from patchloop.git_execution import run_git
from patchloop.prepared_source import admission_hash
from patchloop.repository import WorkspaceManager
from patchloop.runtime import git_commit, repository_root, runtime_content_hash
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json, sha256_bytes, sha256_json
from patchloop.verifier.policy import verify_test_tampering

JOURNAL = "run_dev_currentdev20"
PACKAGES = Path("tasks/dev-train/current-dev20")
ROOTS = {
    "marshmallow-code__marshmallow": ("src", "tests", "marshmallow"),
    "pvlib__pvlib-python": ("pvlib", "pvlib/tests", "pvlib"),
    "pydicom__pydicom": ("pydicom", "pydicom/tests", "pydicom"),
    "pylint-dev__astroid": ("astroid", "tests", "astroid"),
    "pyvista__pyvista": ("pyvista", "tests", "pyvista"),
    "sqlfluff__sqlfluff": ("src", "test", "sqlfluff"),
}


def layout(entry):
    return ROOTS[entry["instance_id"].rsplit("-", 1)[0]]


def task_path(entry):
    return repository_root() / PACKAGES / str(entry["index"]) / "public.yaml"


def register():
    """New packages preserve all original private/reference bytes and public issues."""
    manifest, _ = old.baseline()
    for entry in manifest["rows"]:
        source = repository_root() / (
            "tasks/dev-train/swebench-lite-dev-" + entry["instance_id"].replace("__", "-")
        )
        target = task_path(entry).parent
        require(not target.exists(), "current package exists; inspect instead of replacing")
        shutil.copytree(source, target)
        public = yaml.safe_load((source / "public.yaml").read_text(encoding="utf-8"))
        _, tests, _ = layout(entry)
        constraints = public["constraints"]
        constraints["allowed_paths"] = list(
            dict.fromkeys([*constraints["allowed_paths"], tests + "/**"])
        )
        constraints["forbidden_paths"] = [".patchloop-hidden/**"]
        constraints["additive_test_roots"] = [tests]
        check = public["visible_checks"][0]
        command = check["command"]
        require("-c" in command, "review public test launcher")
        prefix = command[: command.index("-c") + 2]
        options = ["-m", "not dbt"] if layout(entry)[2] == "sqlfluff" else []
        public["test_suites"] = [
            {
                **check,
                "id": "public-pytest",
                "command": prefix + options,
                "runner": "pytest",
                "test_roots": [tests],
            }
        ]
        # A public task tag describes the general edit contract, never a task answer.
        public["tags"].append("add-new-test-functions-preserve-existing-tests-and-fixtures")
        (target / "public.yaml").write_text(
            yaml.safe_dump(public, sort_keys=False), encoding="utf-8"
        )
        package = load_task_package(target)
        require(
            package.public.issue.model_dump()
            == load_task_package(source).public.issue.model_dump(),
            "public issue changed",
        )
    return {"registered": len(manifest["rows"]), "provider_calls": 0}


def supplements(entry):
    module = layout(entry)[2]
    common = ["setuptools==80.9.0"]
    if module == "pvlib":
        return common + ["numpy==1.26.4", "pandas==2.2.3", "scipy==1.12.0"]
    if module == "pyvista":
        return common + ["numpy==1.26.4", "vtk==9.3.1", "matplotlib==3.8.4"]
    if module == "pydicom":
        return common + ["numpy==1.26.4"]
    return common


def dependency_path(root, index):
    directory = "compatibility" if index in {1, 12, 13, 15} else "dependencies"
    return root / directory / str(index) / deps.MANIFEST


def prepare_dependencies(root, index):
    entry = old.baseline()[0]["rows"][index - 1]
    require(entry["index"] == index, "invalid task index")
    package = load_task_package(task_path(entry).parent)
    folder = dependency_path(root, index).parent
    result = legacy_probe_metadata.prepare(
        package.public,
        Path(entry["prepared_source"]),
        folder,
        [layout(entry)[0]],
        supplements(entry),
        installed_limit_mib=1024 if layout(entry)[2] == "pyvista" else 256,
        runtime_profile=(
            "python310-v1"
            if index in {1, 12, 13}
            else "python312-graphics-v1"
            if index == 15
            else "python312-v1"
        ),
    )
    return {"index": index, "descriptor": str(result), "provider_calls": 0}


def request(entry, live, root):
    req = old.request(entry, live / str(entry["index"]))
    return req.model_copy(
        update={
            "task": task_path(entry),
            "prepared_probe_dependencies": dependency_path(root, entry["index"]),
        }
    )


def bindings():
    names = [
        *old.bindings(),
        "diagnostics/current_dev20.py",
        "diagnostics/parallel_dev_batch.py",
        "diagnostics/legacy_probe_metadata.py",
        ".agent/current-dev20.md",
    ]
    return {n: sha256_bytes((repository_root() / n).read_bytes()) for n in names}


def freeze(root, live):
    require(not live.exists() and not (root / "manifest.json").exists(), "fresh batch required")
    repo = repository_root().resolve()
    root, live = root.resolve(), live.resolve()
    require(
        not root.is_relative_to(repo)
        and not live.is_relative_to(repo)
        and not root.is_relative_to(live)
        and not live.is_relative_to(root),
        "separate external roots required",
    )
    validation = old.driver.validation_evidence(root)
    runner._require_tracked_clean_paths(repo, list(bindings()))
    rows = []
    for entry in old.baseline()[0]["rows"]:
        req = request(entry, live, root)
        package = load_task_package(req.task.parent)
        runner._live_source_preflight(req.task.parent, package)
        require(package.environment.image_digest == entry["image_digest"], "image drift")
        require(admission_hash(req.prepared_source) == entry["source_hash"], "source drift")
        dependency_hash = deps.admit(req.prepared_probe_dependencies)
        deps.load_dependencies(req.prepared_probe_dependencies, package.public, dependency_hash)
        rows.append(
            {
                "index": entry["index"],
                "instance_id": entry["instance_id"],
                "task_hash": package.task_content_hash,
                "dependency_identity": dependency_hash.model_dump(mode="json"),
                "request": req.model_dump(mode="json"),
            }
        )
    packet = {
        "schema": "current-dev20-v1",
        "head": git_commit(),
        "runtime_hash": runtime_content_hash(),
        "implementation": bindings(),
        "rows": rows,
        "live_root": str(live),
        "workers": 2,
        "model": old.MODEL,
        "row_cap_usd": str(old.ROW_CAP),
        "total_cap_usd": str(old.CAP),
        "pricing": old.price(),
        "native_identity": old.native_identity(),
        "validation_hash": sha256_json(validation),
        "official": False,
        "claim_eligible": False,
        "approval": "PENDING_EXACT_HUMAN_SCOPE",
        "automatic_followup": False,
    }
    save(root, "manifest.json", packet)
    digest = sha256_json(packet)
    DevJournal(root, JOURNAL).append("panel_prepared", {"packet_hash": digest, "provider_calls": 0})
    return digest


def validate(root, digest):
    packet = json.loads((root / "manifest.json").read_bytes())
    require(sha256_json(packet) == digest, "manifest changed")
    require(
        packet["head"] == git_commit()
        and packet["runtime_hash"] == runtime_content_hash()
        and packet["implementation"] == bindings(),
        "implementation drift",
    )
    require(
        packet["workers"] == 2
        and packet["pricing"] == old.price()
        and packet["native_identity"] == old.native_identity(),
        "execution identity drift",
    )
    require(
        packet["validation_hash"] == sha256_json(old.driver.validation_evidence(root)),
        "validation changed",
    )
    require(len(packet["rows"]) == 20, "exact roster required")
    for entry, row in zip(old.baseline()[0]["rows"], packet["rows"], strict=True):
        req = request(entry, Path(packet["live_root"]), root)
        require(
            row["index"] == entry["index"]
            and row["instance_id"] == entry["instance_id"]
            and row["request"] == req.model_dump(mode="json"),
            "request drift",
        )
        package = load_task_package(req.task.parent)
        runner._live_source_preflight(req.task.parent, package)
        require(package.task_content_hash == row["task_hash"], "package drift")
        require(
            deps.admit(req.prepared_probe_dependencies).model_dump(mode="json")
            == row["dependency_identity"],
            "dependencies drift",
        )
    return packet


def canary_target(public, source):
    """Select an existing public test without inspecting private oracle material."""
    command = public.visible_checks[0].command
    path = source / command[command.index("-c") + 2]
    candidates = (
        [path]
        if path.is_file()
        else sorted(
            p
            for p in path.rglob("*.py")
            if p.name.startswith(("test_", "unittest_")) or p.name.endswith("_test.py")
        )
    )
    for candidate in candidates:
        for node in ast.parse(candidate.read_bytes()).body:
            relative = candidate.relative_to(source).as_posix()
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                return f"{relative}::{node.name}"
            if isinstance(node, ast.ClassDef) and (
                node.name.startswith("Test")
                or any(
                    isinstance(base, ast.Attribute) and base.attr == "TestCase"
                    for base in node.bases
                )
            ):
                for method in node.body:
                    if isinstance(method, ast.FunctionDef) and method.name.startswith("test_"):
                        return f"{relative}::{node.name}::{method.name}"
    raise ValueError("no public canary test found")


def preflight_row(root, entry, req):
    package, source, sandbox, identity = old.driver.environment(req)
    result = sandbox.run_probe(
        source,
        "Verify the prepared public import environment.",
        f'import {layout(entry)[2]}\nprint("IMPORT_OK")',
        deadline=None,
        execution_identity={"run_id": JOURNAL, "action_id": f"import{entry['index']}"},
    )
    journal = DevJournal(root, JOURNAL)
    record = {"index": entry["index"], "environment": identity, "import": result}
    journal.append("import_canary_finished", record)
    require(
        result.get("exit_code") == 0 and not result.get("cleanup_failed"),
        f"public import failed for task {entry['index']}",
    )
    target = canary_target(package.public, source)
    check, _ = selected_check(
        package.public.test_suites[0],
        SelectedTests(suite_id="public-pytest", targets=[target]),
        source,
        lambda path: (path, source / path),
    )
    selected = runner._live_sandbox_preflight(package).run_check(
        source,
        check,
        execution_identity={"run_id": JOURNAL, "action_id": f"selected{entry['index']}"},
    )
    record["selected_test"] = {"target": target, "result": asdict(selected)}
    journal.append("selected_canary_finished", {"index": entry["index"], **record["selected_test"]})
    require(selected.passed, f"selected test canary failed for task {entry['index']}")
    return record


def preflight(root, digest):
    packet = validate(root, digest)
    require(not Path(packet["live_root"]).exists(), "no restart")
    capability = json.loads((root / "capabilities.json").read_bytes())
    require(capability["runtime_hash"] == runtime_content_hash(), "capability runtime drift")
    require(
        any(
            e["event_type"] == "capabilities_passed"
            and e["payload"]["hash"] == sha256_json(capability)
            for e in DevJournal(root, JOURNAL).events()
        ),
        "capability receipt changed",
    )
    require(capability["inputs"] == capability_inputs(root), "capability inputs drift")
    receipts = capability["rows"]
    require([r["index"] for r in receipts] == list(range(1, 21)), "incomplete capabilities")
    receipt = {"packet_hash": digest, "rows": receipts, "provider_calls": 0}
    save(root, "preflight.json", receipt)
    DevJournal(root, JOURNAL).append(
        "preflight_passed", {"packet_hash": digest, "receipt_hash": sha256_json(receipt)}
    )
    return receipt


def capability_inputs(root):
    return [
        {
            "index": entry["index"],
            "task_hash": load_task_package(task_path(entry).parent).task_content_hash,
            "source_hash": admission_hash(Path(entry["prepared_source"])),
            "dependencies": deps.admit(dependency_path(root, entry["index"])).model_dump(
                mode="json"
            ),
        }
        for entry in old.baseline()[0]["rows"]
    ]


def capabilities(root):
    require(not (root / "capabilities.json").exists(), "capability evidence already exists")
    inputs = capability_inputs(root)
    runtime_hash = runtime_content_hash()
    driver_hash = sha256_bytes(Path(__file__).read_bytes())

    def check(entry):
        return preflight_row(root, entry, request(entry, root / "unused", root))

    with ThreadPoolExecutor(max_workers=2) as pool:
        receipts = list(pool.map(check, old.baseline()[0]["rows"]))
    require(
        runtime_hash == runtime_content_hash() and inputs == capability_inputs(root),
        "capability inputs changed during checks",
    )
    record = {
        "runtime_hash": runtime_hash,
        "driver_hash": driver_hash,
        "inputs": inputs,
        "rows": receipts,
        "provider_calls": 0,
    }
    save(root, "capabilities.json", record)
    DevJournal(root, JOURNAL).append("capabilities_passed", {"hash": sha256_json(record)})
    return {"tasks": len(receipts), "provider_calls": 0}


def assess(root, entry, value, req):
    require(value["accounting"]["billing_known"], "unsettled row")
    run = value["result"]["runs"][0]
    if not run.get("artifact_hashes", {}).get("submitted_patch"):
        return {"ok": True, "status": "NOT_RUN", "reason": "unsubmitted"}
    workspace = req.state_root / "workspaces" / run["run_id"] / "repo"
    diff = WorkspaceManager.diff_summary(workspace)
    require(diff.patch_hash == run["artifact_hashes"]["submitted_patch"], "submitted source drift")
    task = load_task_package(req.task.parent).public
    policy = verify_test_tampering(diff, task.constraints, workspace)
    require(policy.passed, "submitted tests violate preservation contract")
    paths = policy.details["test_files"]
    source_patch = run_git(
        workspace, "diff", "--binary", "HEAD", "--", ".", *[f":(exclude){path}" for path in paths]
    ).stdout.encode("utf-8")
    result = old.native_assessment(root, entry, value, req, evaluation_patch=source_patch)
    result["omitted_additive_test_paths"] = paths
    return result


def summarize(outcome, entries):
    for row in outcome["rows"]:
        row["instance_id"] = entries[row["index"]]["instance_id"]
    outcome["planned"] = len(entries)
    outcome["resolved"] = sum(
        r.get("assessment", {}).get("ok") is True and r["assessment"].get("status") == "PASS"
        for r in outcome["rows"]
    )
    outcome["recorded_cost_nanos"] = sum(
        r.get("accounting", {}).get("cost_nanos") or 0 for r in outcome["rows"]
    )
    outcome["billing_known"] = all(
        r.get("accounting", {}).get("billing_known") is True for r in outcome["rows"]
    )
    outcome["complete_agreeing_evaluation"] = len(outcome["rows"]) == len(entries) and all(
        r["ok"] and r.get("assessment", {}).get("agreement") is True for r in outcome["rows"]
    )
    outcome["official"] = outcome["claim_eligible"] = False
    return outcome


def run(root, digest):
    packet = validate(root, digest)
    approval = json.loads((root / "authorization.json").read_bytes())
    require(
        approval.get("approved") is True
        and approval.get("packet_hash") == digest
        and bool(approval.get("human_message")),
        "exact human scope approval required",
    )
    journal = DevJournal(root, JOURNAL)
    with journal.execution_lock():
        events = journal.events()
        require(not any(e["event_type"] == "panel_started" for e in events), "no restart/resume")
        receipt = json.loads((root / "preflight.json").read_bytes())
        require(
            any(
                e["event_type"] == "preflight_passed"
                and e["payload"]["packet_hash"] == digest
                and e["payload"]["receipt_hash"] == sha256_json(receipt)
                for e in events
            ),
            "preflight required",
        )
        live = Path(packet["live_root"])
        require(not live.exists(), "fresh live root required")
        live.mkdir()
        journal.append(
            "panel_started", {"packet_hash": digest, "authorization_hash": sha256_json(approval)}
        )
        entries = old.baseline()[0]["rows"]
        started = monotonic()
        outcome = parallel_dev_batch.run_parallel_rows(
            packet["rows"],
            total_cap=old.CAP,
            workers=packet["workers"],
            journal=journal,
            after_row=lambda i, v, req: assess(root, entries[i], v, req),
        )
        outcome["wall_seconds"] = round(monotonic() - started, 3)
        summarize(outcome, entries)
        save(root, "result.json", outcome)
        journal.append("panel_closed", {"result_hash": sha256_json(outcome)})
        return outcome


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=["register", "dependencies", "capabilities", "freeze", "preflight", "run"],
    )
    parser.add_argument("--root", type=Path)
    parser.add_argument("--live-root", type=Path)
    parser.add_argument("--index", type=int)
    parser.add_argument("--packet-hash")
    args = parser.parse_args()
    if args.command == "register":
        result = register()
    elif args.command == "dependencies":
        result = prepare_dependencies(args.root.resolve(), args.index)
    elif args.command == "freeze":
        result = freeze(args.root.resolve(), args.live_root.resolve())
    elif args.command == "capabilities":
        result = capabilities(args.root.resolve())
    else:
        result = globals()[args.command](args.root.resolve(), args.packet_hash)
    print(canonical_json(result))


if __name__ == "__main__":
    main()
