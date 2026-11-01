"""Two bounded selected-test executions on isolated, identity-bound public source."""

from __future__ import annotations

import copy
import json
import re
import uuid
from dataclasses import asdict
from pathlib import Path

from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact
from patchloop.dev.check_feedback import output_tail
from patchloop.dev.mutation_tools import MUTATION_TOOLS
from patchloop.errors import ContractError, RecoveryError
from patchloop.git_execution import run_git
from patchloop.repair_verification import _observation, compare_selected_observations
from patchloop.repository import WorkspaceManager
from patchloop.runtime import repository_root
from patchloop.sandbox.public_pytest import reporting_copy_command
from patchloop.util import sha256_bytes, sha256_json

PREPARED = "test_comparison_prepared"
STARTED = "test_comparison_child_started"
FINISHED = "test_comparison_child_finished"
COMPLETE = "test_comparison_finished"


class ComparisonExecutionUncertain(RecoveryError):
    code = "TEST_COMPARISON_EXECUTION_UNCERTAIN"


def has_comparison(arguments: dict) -> bool:
    return arguments.get("comparison") is not None


def execution_cost(arguments: dict) -> int:
    """Admission cost in physical sandbox executions, including the selected action."""
    return 2 if has_comparison(arguments) else 1


def schema() -> dict:
    return {"anyOf": [{"type": "null"}, {
        "type": "object", "additionalProperties": False,
        "properties": {
            "baseline": {"type": "string", "enum": ["original_base", "before_mutation"]},
            "mutation_action_id": {"type": ["string", "null"], "minLength": 1,
                                   "maxLength": 500},
        }, "required": ["baseline", "mutation_action_id"],
    }]}


def _receipt(events, kind, action_id):
    rows = [event["payload"] for event in events if event["event_type"] == kind
            and event["payload"].get("action_id") == action_id]
    if rows and any(row != rows[0] for row in rows[1:]):
        raise RecoveryError("conflicting selected-test comparison receipts")
    return rows[0] if rows else None


def _read(store, reference):
    return store.read_bytes(Artifact.model_validate(reference))


def _mutation_chain(events, mutation_id):
    starts, completed = {}, []
    for event in events:
        payload = event["payload"]
        if event["event_type"] == "action_started" and payload.get("tool") in MUTATION_TOOLS:
            starts[payload["action_id"]] = payload
        elif event["event_type"] == "action_finished":
            result = payload["result"]
            if result["tool"] in MUTATION_TOOLS and result["status"] == "succeeded":
                start = starts.get(result["action_id"])
                if start is None or start["input_hash"] != result["input_hash"]:
                    raise RecoveryError("comparison mutation has no matching admission")
                completed.append((start, result))
    index = next((i for i, (start, _) in enumerate(completed)
                  if start["action_id"] == mutation_id), None)
    if index is None:
        raise ContractError("before_mutation requires a completed mutation in this run")
    return completed[index:]


def _python_command(check, script, marker):
    command = check.command
    executable = command[0].replace("\\", "/").rsplit("/", 1)[-1]
    if not re.fullmatch(r"python(?:3(?:\.\d+)?)?(?:\.exe)?", executable):
        raise ContractError("test comparison requires a registered Python pytest command")
    module = next((i for i in range(1, len(command) - 1)
                   if command[i:i + 2] == ["-m", "pytest"]), None)
    if module is None:
        return reporting_copy_command(command, script, marker, check.working_directory)
    invocation = repr((command[module + 2:], None, check.working_directory, marker))
    return [*command[:module], "-c", script + "\nmain(*" + invocation + ")"]


def _selected_observation(observation, targets):
    observation = copy.deepcopy(observation)
    if observation.get("status") != "COMPLETED":
        return observation
    nodes = []
    for test in observation.get("tests", []):
        _, separator, suffix = test["nodeid"].partition("::")
        nodes.append(test["path"] + separator + suffix)
    missing = [target for target in targets if not any(
        node == target or node.startswith(target + "::") or node.startswith(target + "[")
        for node in nodes)]
    if missing:
        observation.update(status="NOT_COLLECTED", missing_targets=missing)
    return observation


def _clone(gateway, root, commit):
    # Fresh identities avoid deleting/replacing partial preparation after a crash.
    manager = WorkspaceManager(repository_root() / "fixtures/repositories", root,
                               local_source=gateway.workspace)
    return manager.create("comparison_" + uuid.uuid4().hex,
                          gateway.public_task.repository.url, commit,
                          deadline=gateway.deadline)


def _prepare(gateway, selection, check, targets, identity, store):
    events = gateway.journal.events()
    summary = gateway.current_diff
    root = (gateway.journal.root / "test-comparisons" / gateway.journal.run_id).resolve()
    protected = (repository_root().resolve(), gateway.workspace.resolve())
    if any(root == path or root.is_relative_to(path) or path.is_relative_to(root)
           for path in protected):
        raise ContractError("comparison workspaces must be outside source repositories")
    root.mkdir(parents=True, exist_ok=True)
    commit = run_git(gateway.workspace, "rev-parse", "HEAD",
                     deadline=gateway.deadline).stdout.strip()
    patch = store.put_text(summary.patch).model_dump(mode="json")
    test_files = {}
    for target in targets:
        path = target.partition("::")[0]
        _, selected = gateway._tracked_path(path)
        test_files[path] = store.put_bytes(selected.read_bytes()).model_dump(mode="json")
    candidate = _clone(gateway, root, commit)
    baseline = _clone(gateway, root, commit)
    if summary.patch:
        WorkspaceManager.apply_patch(candidate, patch["path"], deadline=gateway.deadline)
    if WorkspaceManager.diff_summary(candidate, deadline=gateway.deadline).patch_hash != (
        summary.patch_hash
    ):
        raise RecoveryError("isolated candidate differs from selected current diff")
    request = selection.comparison
    baseline_hash = sha256_bytes(b"")
    if request.baseline == "before_mutation":
        chain = _mutation_chain(events, request.mutation_action_id)
        selected_start, _ = chain[0]
        mutation_paths = selected_start.get("mutation_target_paths") or [
            selected_start.get("mutation_target_path", "")]
        roots = [*gateway.public_task.constraints.additive_test_roots,
                 *(root for suite in gateway.public_task.test_suites for root in suite.test_roots)]
        if not any(path and not any(path.startswith(root + "/") for root in roots)
                   for path in mutation_paths):
            raise ContractError(
                "before_mutation must select an implementation edit, not a test edit")
        if summary.patch:
            WorkspaceManager.apply_patch(baseline, patch["path"], deadline=gateway.deadline)
        for start, result in reversed(chain):
            current = WorkspaceManager.diff_summary(baseline, deadline=gateway.deadline).patch_hash
            if current != result["output"].get("worktree_diff_hash"):
                raise RecoveryError(
                    "selected mutation lineage does not match the current full diff")
            delta = start.get("mutation_generated_patch")
            if not isinstance(delta, str):
                raise RecoveryError("selected mutation has no exact reversible patch")
            run_git(baseline, "apply", "--reverse", "--intent-to-add", "--whitespace=nowarn", "-",
                    input=delta.encode(), deadline=gateway.deadline)
            current = WorkspaceManager.diff_summary(baseline, deadline=gateway.deadline).patch_hash
            if current != start.get("baseline_diff_hash"):
                raise RecoveryError("selected mutation pre-state full diff identity differs")
        baseline_hash = selected_start["baseline_diff_hash"]
    # Freeze identical selected test bytes, even when the test was added after the edit.
    for workspace in (baseline, candidate):
        for path, reference in test_files.items():
            destination = workspace / path
            from patchloop.dev.file_transaction import FileChange, apply_changes, checked_target

            _, destination = checked_target(workspace, path)
            content = _read(store, reference)
            before = destination.read_bytes() if destination.is_file() else None
            if before != content:
                apply_changes(workspace, [FileChange(path, before, content)],
                              deadline=gateway.deadline)
    script = (Path(__file__).parents[1] / "sandbox/pytest_report.py").read_text(encoding="utf-8")
    phases = []
    for phase, workspace in (("baseline", baseline), ("candidate", candidate)):
        marker = "PATCHLOOP_PYTEST_" + sha256_json({**identity, "phase": phase})[7:31] + ":"
        instrumented = check.model_copy(update={"command": _python_command(check, script, marker)})
        phase_identity = {
            **identity, "phase": phase,
            "execution_diff_hash": WorkspaceManager.diff_summary(
                workspace, deadline=gateway.deadline).patch_hash,
            "check_hash": sha256_json(instrumented.model_dump(mode="json")),
            "test_file_hashes": {path: ref["content_hash"] for path, ref in test_files.items()},
        }
        child = "test-comparison-" + sha256_json(phase_identity)[7:47]
        phases.append({"action_id": child, "input_hash": sha256_json(phase_identity),
                       "identity": phase_identity, "workspace": str(workspace),
                       "marker": marker, "check": instrumented.model_dump(mode="json")})
    receipt = {"action_id": identity["action_id"], "identity": identity,
               "base_commit": commit, "baseline_diff_hash": baseline_hash,
               "candidate_diff_hash": summary.patch_hash, "candidate_patch": patch,
               "test_files": test_files, "phases": phases}
    gateway.journal.append(PREPARED, receipt)
    return receipt


def _phase(gateway, phase, store):
    events = gateway.journal.events()
    finished = _receipt(events, FINISHED, phase["action_id"])
    started = _receipt(events, STARTED, phase["action_id"])
    expected = {"action_id": phase["action_id"], "input_hash": phase["input_hash"],
                "identity": phase["identity"]}
    if started is not None and started != expected:
        raise RecoveryError("comparison child execution identity changed")
    if finished is not None:
        if started is None or any(finished.get(key) != value for key, value in expected.items()):
            raise RecoveryError("comparison child completion has no matching start")
        result = json.loads(_read(store, finished["result"]))
        if any(result.get(key) != value for key, value in expected.items()):
            raise RecoveryError("comparison child result identity changed")
        return result
    if started is not None:
        raise ComparisonExecutionUncertain(
            "selected-test comparison child outcome is uncertain; it will not be rerun",
            details={"execution_uncertain": True, "cleanup_failed": True,
                     "child_action_id": phase["action_id"]})
    from patchloop.contracts import RegisteredCheck

    workspace = Path(phase["workspace"])
    if WorkspaceManager.diff_summary(workspace, deadline=gateway.deadline).patch_hash != (
        phase["identity"]["execution_diff_hash"]
    ):
        raise RecoveryError("comparison workspace changed before dispatch")
    check = RegisteredCheck.model_validate(phase["check"])
    gateway.journal.append(STARTED, expected)
    kwargs = ({"deadline": gateway.deadline,
               "execution_identity": {"run_id": gateway.journal.run_id,
                                      "action_id": phase["action_id"]}}
              if getattr(gateway.sandbox, "supports_execution_deadline", False) else {})
    try:
        raw = asdict(gateway.sandbox.run_check(workspace, check, **kwargs))
    except Exception as exc:
        raise ComparisonExecutionUncertain(
            "selected-test comparison child returned no durable outcome; it will not be rerun",
            details={"execution_uncertain": True, "cleanup_failed": True,
                     "child_action_id": phase["action_id"],
                     "cause_type": type(exc).__name__}) from exc
    if WorkspaceManager.diff_summary(workspace, deadline=gateway.deadline).patch_hash != (
        phase["identity"]["execution_diff_hash"]
    ):
        raise RecoveryError("comparison workspace changed during execution")
    result = {**expected, "raw": raw, "observation": _observation(raw, phase["marker"])}
    reference = store.put_json(result).model_dump(mode="json")
    gateway.journal.append(FINISHED, {**expected, "result": reference})
    return result


def run(gateway, selection, check, targets, execution_identity):
    if not execution_identity:
        raise ContractError("test comparison requires a durable action identity")
    candidate_hash = gateway.current_diff_hash
    identity = {**execution_identity, "selection": selection.model_dump(mode="json"),
                "candidate_diff_hash": candidate_hash,
                "check_hash": sha256_json(check.model_dump(mode="json"))}
    events = gateway.journal.events()
    store = ArtifactStore(gateway.journal.root / "artifacts")
    complete = _receipt(events, COMPLETE, identity["action_id"])
    if complete is not None:
        if complete["identity"] != identity:
            raise RecoveryError("completed comparison input identity changed")
        return json.loads(_read(store, complete["result"]))
    prepared = _receipt(events, PREPARED, identity["action_id"])
    if prepared is None:
        prepared = _prepare(gateway, selection, check, targets, identity, store)
    elif prepared["identity"] != identity:
        raise RecoveryError("prepared comparison input identity changed")
    results = []
    for phase in prepared["phases"]:
        result = _phase(gateway, phase, store)
        results.append(result)
        if result["raw"].get("cleanup_failed") or result["raw"].get("deadline_exhausted"):
            raise ComparisonExecutionUncertain(
                "comparison execution cleanup or deadline failed; remaining phase was not started",
                details={"execution_uncertain": True, "cleanup_failed": True,
                         "child_action_id": phase["action_id"]})
    before, after = (_selected_observation(result["observation"], targets) for result in results)
    comparison = compare_selected_observations(before, after, check.id)
    raw = results[-1]["raw"]
    passed = after.get("status") == "COMPLETED" and raw["exit_code"] == 0
    stdout, clipped_stdout = output_tail(raw.get("stdout", ""), 12000)
    stderr, clipped_stderr = output_tail(raw.get("stderr", ""), 12000)
    output = {
        "check_id": check.id, "diff_hash": candidate_hash, "passed": passed,
        "failure_signature": None if passed else sha256_json(after),
        **{key: raw.get(key) for key in ("exit_code", "timed_out", "truncated",
                                        "deadline_exhausted", "cleanup_failed",
                                        "execution_policy")},
        "stdout": stdout, "stderr": stderr,
        "truncated": bool(raw.get("truncated")) or clipped_stdout or clipped_stderr,
        "suite_id": selection.suite_id, "targets": targets, "counts_toward_completion": False,
        "test_status": "PASS" if passed else "FAIL" if after.get("status") == "COMPLETED"
                       else "ERROR",
        "comparison": {
            **comparison, "baseline": selection.comparison.baseline,
            "mutation_action_id": selection.comparison.mutation_action_id,
            "base_commit": prepared["base_commit"],
            "baseline_diff_hash": prepared["baseline_diff_hash"],
            "candidate_diff_hash": candidate_hash,
            "test_file_hashes": {path: ref["content_hash"]
                                 for path, ref in prepared["test_files"].items()},
            "physical_execution_count": len(results), "total_execution_count": 2,
            "observations": {
                phase: {"action_id": result["action_id"],
                        "status": observation["status"],
                        **({"missing_targets": observation["missing_targets"]}
                           if "missing_targets" in observation else {}),
                        "execution_diff_hash": result["identity"]["execution_diff_hash"]}
                for phase, result, observation in zip(
                    ("baseline", "candidate"), results, (before, after), strict=True)},
        },
    }
    if gateway.current_diff_hash != candidate_hash:
        raise RecoveryError("live candidate changed during isolated test comparison")
    reference = store.put_json(output).model_dump(mode="json")
    gateway.journal.append(COMPLETE, {"action_id": identity["action_id"],
                                      "identity": identity, "result": reference})
    return copy.deepcopy(output)
