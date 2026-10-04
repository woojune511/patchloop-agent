"""Public, provider-free comparison of a returned patch and its added pytest cases."""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import asdict
from pathlib import Path, PurePosixPath

from patchloop.artifacts import ArtifactStore
from patchloop.deadline import ExecutionDeadline
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError, PatchLoopError
from patchloop.git_execution import run_git
from patchloop.repair import load_repair_request, load_repair_task, prepared_sandbox
from patchloop.repository import WorkspaceManager
from patchloop.runtime import repository_root, runtime_content_hash
from patchloop.test_additions import UnsupportedTestChange, added_tests
from patchloop.util import sha256_bytes
from patchloop.verifier.policy import _is_test_path, verify_scope


def _pytest_args(command: list[str]) -> list[str] | None:
    executable = command[0].replace("\\", "/").rsplit("/", 1)[-1]
    if re.fullmatch(r"python(?:3(?:\.\d+)?)?(?:\.exe)?", executable) and command[1:3] == [
        "-m",
        "pytest",
    ]:
        return command[3:]
    return None


def _test_state(test: dict) -> str:
    phases = test["phases"]
    if test.get("xfail_marked") or any(p.get("wasxfail") is not None for p in phases):
        return "XFAIL_OR_XPASS"
    if any(p["outcome"] == "failed" and p["when"] != "call" for p in phases):
        return "SETUP_OR_TEARDOWN_ERROR"
    if any(p["outcome"] == "skipped" for p in phases):
        return "SKIPPED"
    if any(p["outcome"] == "failed" and p["when"] == "call" for p in phases):
        return "TEST_FAILED"
    if len(phases) == 3 and all(p["outcome"] == "passed" for p in phases):
        return "PASSED"
    return "NOT_RUN"


def _observation(raw: dict, marker: str | None) -> dict:
    if raw["cleanup_failed"] or raw["deadline_exhausted"]:
        return {"status": "EXECUTION_ERROR"}
    if raw["timed_out"]:
        return {"status": "TIMEOUT"}
    if raw["truncated"]:
        return {"status": "INCOMPLETE_OUTPUT"}
    if marker is None:
        return {"status": "EXIT_ZERO" if raw["exit_code"] == 0 else "NONZERO_EXIT"}
    frames = [line[len(marker) :] for line in raw["stdout"].splitlines() if line.startswith(marker)]
    try:
        if len(frames) != 1:
            raise ValueError("missing or duplicate report")
        report = json.loads(frames[0])
        if report["exit_code"] != raw["exit_code"]:
            raise ValueError("exit code mismatch")
        for test in report["tests"]:
            test["status"] = _test_state(test)
        if report["collection_errors"]:
            status = "COLLECTION_ERROR"
        elif report["collection_skips"] and raw["exit_code"] == 5:
            status = "COLLECTION_SKIPPED"
        elif raw["exit_code"] == 5:
            status = "NOT_COLLECTED"
        elif raw["exit_code"] not in {0, 1}:
            status = "PYTEST_ERROR"
        elif any(t["status"] == "SETUP_OR_TEARDOWN_ERROR" for t in report["tests"]):
            status = "SETUP_OR_TEARDOWN_ERROR"
        else:
            status = "COMPLETED"
        return {"status": status, **report}
    except (ValueError, KeyError, TypeError):
        return {"status": "INVALID_REPORT"}


def _compare(results: list[dict], selectors: list[dict]) -> dict:
    observations = {
        phase: [r for r in results if r["phase"] == phase and r["pytest"]]
        for phase in ("base_with_tests", "patched")
    }
    if any(
        not rows or any(r["observation"]["status"] != "COMPLETED" for r in rows)
        for rows in observations.values()
    ):
        return {"status": "INCONCLUSIVE", "reason": "incomplete or erroneous pytest execution"}
    tables = {
        phase: {(r["check_id"], t["nodeid"]): t for r in rows for t in r["observation"]["tests"]}
        for phase, rows in observations.items()
    }
    before, after = tables["base_with_tests"], tables["patched"]
    missing = [
        dict(s, missing_index=index)
        for s in selectors
        for index in (s["indices"] if s["indices"] is not None else [None])
        if not any(
            t["path"] == s["path"]
            and t["function"] == s["function"]
            and t["parameter_index"] == index
            for t in after.values()
        )
    ]
    if missing or not before or before.keys() != after.keys():
        return {
            "status": "NOT_COLLECTED",
            "missing_selectors": missing,
            "reason": "added tests missing or collection identities differ",
        }
    pairs = [
        {
            "check_id": key[0],
            "nodeid": key[1],
            "before": before[key]["status"],
            "after": after[key]["status"],
        }
        for key in sorted(before)
    ]
    if all(
        p["after"] == "PASSED" and p["before"] in {"TEST_FAILED", "PASSED"} for p in pairs
    ) and any(p["before"] == "TEST_FAILED" for p in pairs):
        status = "OBSERVED_FAIL_THEN_PASS"
    elif all(p["before"] == p["after"] == "PASSED" for p in pairs):
        status = "PASSED_BOTH"
    else:
        status = "INCONCLUSIVE"
    return {"status": status, "tests": pairs}


def _separate(manager, base, patched, paths, deadline):
    selectors, test_paths, implementation_paths = [], [], []
    for path in paths:
        name = PurePosixPath(path).name
        if name in {"conftest.py", "setup.py"} or not path.endswith(".py"):
            raise UnsupportedTestChange(f"configuration/non-Python change: {path}")
        if _is_test_path(path):
            if not (name.startswith("test_") or name.endswith("_test.py")):
                raise UnsupportedTestChange(f"test helper/fixture change: {path}")
            before = manager.read_base_file(base, path, deadline=deadline)
            after = (patched / path).read_bytes()
            additions = added_tests(before, after, path)
            if not additions:
                raise UnsupportedTestChange(f"changed test file has no supported additions: {path}")
            selectors.extend(additions)
            test_paths.append(path)
        else:
            implementation_paths.append(path)
    if not selectors:
        raise UnsupportedTestChange("no additions to existing test files")
    return selectors, test_paths, implementation_paths


def verify_repair(request_path: Path, patch_path: Path, *, state_root: Path | None = None) -> dict:
    request = load_repair_request(request_path)
    package = load_repair_task(request.task)
    if state_root is None:
        from patchloop.dev.runner import default_state_root

        state_root = request.state_root or default_state_root()
    root = state_root.resolve()
    for protected in (repository_root().resolve(), request.source.resolve()):
        if root == protected or root.is_relative_to(protected) or protected.is_relative_to(root):
            raise ContractError("verification state must be outside source and PatchLoop trees")
    run_id = "run_dev_verify_" + uuid.uuid4().hex[:16]
    journal, store = DevJournal(root, run_id), ArtifactStore(root / "artifacts")
    deadline = ExecutionDeadline.from_remaining(request.limits.wall_time_seconds)
    result = {
        "schema_version": "repair-verification-v1",
        "run_id": run_id,
        "official": False,
        "acceptance": "NOT_RUN",
        "requirement_fit": "NOT_ASSESSED",
        "comparison": {"status": "NOT_RUN"},
        "checks": [],
        "base_commit": package.public.repository.base_commit,
        "public_spec_hash": package.public_spec_hash,
        "runtime_hash": runtime_content_hash(),
        "sandbox": request.sandbox.model_dump(),
        "journal": str(journal.path),
        "changed_files": [],
        "model_calls": 0,
    }
    with journal.execution_lock():
        try:
            patch = patch_path.read_bytes()
            result["request"] = store.put_bytes(request_path.read_bytes()).model_dump(mode="json")
            result["patch"] = store.put_bytes(patch).model_dump(mode="json")
            public_artifact = store.put_json(package.public.model_dump(mode="json"))
            result["public_task"] = public_artifact.model_dump(mode="json")
            journal.append("verification_started", result)
            try:
                paths = WorkspaceManager.patch_changed_files(patch)
            except ContractError as exc:
                if patch.startswith(b"diff --git "):
                    raise UnsupportedTestChange(str(exc)) from exc
                raise
            result["changed_files"] = paths
            manager = WorkspaceManager(
                repository_root() / "fixtures/repositories",
                root / "workspaces",
                local_source=request.source,
            )
            base = manager.create(
                run_id + "_base",
                package.public.repository.url,
                package.public.repository.base_commit,
                deadline=deadline,
            )
            # Only existing regular files; no renames, binary diffs, modes or new files.
            tree = run_git(base, "ls-tree", "-r", "HEAD", deadline=deadline).stdout
            regular = {
                line.split("\t", 1)[1]
                for line in tree.splitlines()
                if line.startswith(("100644 ", "100755 "))
            }
            if any(path not in regular for path in paths) or re.search(
                rb"^(?:new file|deleted file|old mode|new mode|rename |copy |"
                rb"GIT binary patch|Binary files)",
                patch,
                re.MULTILINE,
            ):
                raise UnsupportedTestChange(
                    "only edits to existing regular Python files are supported"
                )
            patched = manager.create(
                run_id + "_patched",
                package.public.repository.url,
                package.public.repository.base_commit,
                deadline=deadline,
            )
            manager.apply_patch(patched, result["patch"]["path"], deadline=deadline)
            summary = manager.diff_summary(patched, deadline=deadline)
            result["scope"] = asdict(verify_scope(summary, package.public.constraints))
            if summary.changed_files != paths or not result["scope"]["passed"]:
                raise UnsupportedTestChange("patch paths or original request scope do not match")
            selectors, test_paths, implementation_paths = _separate(
                manager, base, patched, paths, deadline
            )
            result.update(
                test_additions=selectors,
                test_paths=test_paths,
                implementation_paths=implementation_paths,
            )
            if not any(_pytest_args(c.command) is not None for c in package.public.visible_checks):
                raise UnsupportedTestChange("requires a registered python -m pytest check")
            before = manager.create(
                run_id + "_tests",
                package.public.repository.url,
                package.public.repository.base_commit,
                deadline=deadline,
            )
            for path in test_paths:
                # Copy exact submitted bytes, never regenerate or correct a test.
                (before / path).write_bytes((patched / path).read_bytes())
            result["test_file_hashes"] = {
                p: sha256_bytes((before / p).read_bytes()) for p in test_paths
            }
            result["workspaces"] = {
                "base": str(base),
                "base_with_tests": str(before),
                "patched": str(patched),
            }
            sandbox = prepared_sandbox(request, deadline=deadline)
            script_path = Path(__file__).parent / "sandbox/pytest_report.py"
            script = script_path.read_text(encoding="utf-8")
            for phase, workspace in (
                ("base", base),
                ("base_with_tests", before),
                ("patched", patched),
            ):
                diff_hash = manager.diff_summary(workspace, deadline=deadline).patch_hash
                for check in package.public.visible_checks:
                    deadline.check()
                    args = _pytest_args(check.command)
                    marker = "PATCHLOOP_PYTEST_" + uuid.uuid4().hex + ":"
                    instrumented = check
                    if args is not None:
                        selected = [] if phase == "base" else selectors
                        invocation = repr((args, selected, check.working_directory, marker))
                        command = [check.command[0], "-c", script + "\nmain(*" + invocation + ")"]
                        instrumented = check.model_copy(update={"command": command})
                    action_id = phase + ":" + check.id
                    journal.append(
                        "verification_check_started",
                        {
                            "action_id": action_id,
                            "phase": phase,
                            "diff_hash": diff_hash,
                            "check": check.model_dump(mode="json"),
                            "executed_check_hash": store.put_json(
                                instrumented.model_dump(mode="json")
                            ).content_hash,
                        },
                    )
                    raw = asdict(
                        sandbox.run_check(
                            workspace,
                            instrumented,
                            deadline=deadline,
                            execution_identity={"run_id": run_id, "action_id": action_id},
                        )
                    )
                    row = {
                        "phase": phase,
                        "check_id": check.id,
                        "diff_hash": diff_hash,
                        "pytest": args is not None,
                        "exit_code": raw["exit_code"],
                        "expected_exit_codes": check.expected_exit_codes,
                        "observation": _observation(raw, marker if args is not None else None),
                        "receipt": store.put_json(raw).model_dump(mode="json"),
                    }
                    result["checks"].append(row)
                    journal.append("verification_check_finished", row)
                    if raw["cleanup_failed"] or raw["deadline_exhausted"]:
                        raise ContractError("verification execution cleanup or deadline failed")
            result["comparison"] = _compare(result["checks"], selectors)
            result["status"] = "COMPLETE"
        except UnsupportedTestChange as exc:
            result.update(status="UNSUPPORTED", reason=str(exc))
        except (PatchLoopError, OSError, ValueError) as exc:
            result.update(status="ERROR", reason=str(exc), error_type=type(exc).__name__)
        receipt = store.put_json(result)
        journal.append("verification_finished", {"result": receipt.model_dump(mode="json")})
    return {**result, "result_artifact": receipt.model_dump(mode="json")}
