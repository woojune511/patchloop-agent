"""Single-use, provider-free completion protocol controls on the public CSV fixture.

This is a same-current-runtime ablation with fixed trusted decisions, not a model
experiment, historical baseline replay, Docker validation, or repair-accuracy test.
Only public task/source files are loaded; no isolated/private evaluator is invoked.
"""

from __future__ import annotations

import argparse
import importlib
import json
import socket
import subprocess
import sys
from contextlib import contextmanager, nullcontext
from pathlib import Path
from time import monotonic
from unittest.mock import patch

from patchloop.artifacts import ArtifactStore
from patchloop.deadline import ExecutionDeadline
from patchloop.dev import completion_reproduction, runner
from patchloop.dev.contracts import DevLimits, RequestedTool
from patchloop.dev.model import MOCK_MUTATIONS
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import DevToolGateway
from patchloop.repository import WorkspaceManager
from patchloop.runtime import repository_root
from patchloop.sandbox import LocalSandbox
from patchloop.task_loader import load_public_task
from patchloop.util import canonical_json, sha256_bytes, sha256_json

CONDITIONS = ("wrong_comment", "proper_repair", "no_original", "incomplete_current")
ARMS = ("OFF", "ON")
EXPECTATIONS = {
    "wrong_comment": {"OFF": "accepted", "ON": "rejected_refuted"},
    "proper_repair": {"OFF": "accepted", "ON": "accepted_cases_verified"},
    "no_original": {"OFF": "accepted", "ON": "accepted_unverified"},
    "incomplete_current": {"OFF": "accepted", "ON": "accepted_unverified"},
}
TEXT = 'h,v\n"first\nsecond",x\n'
EXPECTED = [["h", "v"], ["first\nsecond", "x"]]
REPORTED_FAILURE = [["h", "v"], ["first"], ['second"', "x"]]
NORMAL = "name,age\nAda,36"
NORMAL_EXPECTED = [["name", "age"], ["Ada", "36"]]
TOTAL_SECONDS = 180
SUBPROCESS_SECONDS = 10


def call(name, action, arguments, mode):
    return RequestedTool(name=name, action_id=action, arguments=arguments,
                         turn_decision={"mode": mode, "basis": "Frozen public protocol control.",
                                        "evidence_goal": "Read the fixed public edit target."
                                        if mode == "inspect" else None})


def original_case(task, *, normal=False):
    text, expected = (NORMAL, NORMAL_EXPECTED) if normal else (TEXT, EXPECTED)
    return call("run_probe", "normal" if normal else "original", {
        "question": "Does this fixed public parser input match the declared expected rows?",
        "python_source": f"record_observation(observed_target()({text!r}).value)",
        "replay_action_id": None,
        "purpose": {
            "kind": "original_requirement",
            "entrypoint": "mini_data_utils.csvlite.parse_rows",
            "input_conditions": "Normal two-column CSV." if normal else "Quoted embedded newline.",
            "environment_conditions": "Current workspace parser with normal import defaults.",
            "expected_json": canonical_json(expected),
            # The normal control declares an absent failure and must not acquire it.
            "reported_failure_json": canonical_json([] if normal else REPORTED_FAILURE),
        },
    }, "verify")


def mutation(condition):
    proper = MOCK_MUTATIONS["csv-quoted-newline"]
    if condition == "proper_repair":
        old, new = proper.old_text, proper.new_text
    elif condition == "incomplete_current":
        old = "    rows: list[list[str]] = []"
        # Trusted protocol control: generator return makes the selected invocation
        # incomplete/unserializable without changing the public normal-input checks.
        new = ('    if \'"first\\nsecond"\' in text:\n'
               '        return (row for row in [])\n' + old)
    else:
        old = "    rows: list[list[str]] = []"
        new = "    # Comment-only candidate deliberately leaves behavior unchanged.\n" + old
    return call("replace_text", "edit", {
        "path": proper.path, "old_text": old, "new_text": new, "occurrence": 1,
        "hypothesis": "Fixed protocol candidate; no model-generated repair hypothesis.",
        "expected_behavior": "Exercise the frozen completion case " + condition + ".",
        "causal_revision": None,
    }, "mutate")


class BoundedChecks(LocalSandbox):
    """Keep public check commands unchanged but cap each local check at ten seconds."""

    def run_check(self, workspace, check, *, deadline=None, execution_identity=None,
                  execution_targets=None):
        bounded = check.model_copy(update={
            "timeout_seconds": min(check.timeout_seconds, SUBPROCESS_SECONDS),
        })
        return super().run_check(workspace, bounded, deadline=deadline,
                                 execution_identity=execution_identity,
                                 execution_targets=execution_targets)


def trusted_probe():
    """Explicit test-helper import; never installed as the production probe backend."""
    tests = str(repository_root() / "tests")
    sys.path.insert(0, tests)
    try:
        return importlib.import_module("test_dev_probe_cases").ExecutingProbe()
    finally:
        sys.path.remove(tests)


@contextmanager
def local_only():
    """Block accidental network/provider and Docker launches in the control driver."""
    original_popen = subprocess.Popen

    def forbidden(*args, **kwargs):
        raise RuntimeError("This diagnostic permits no network access")

    def guarded(command=None, *args, **kwargs):
        selected = kwargs.get("args", command)
        executable = (selected[0] if isinstance(selected, (list, tuple))
                      else str(selected).split()[0])
        if Path(str(executable)).name.lower() in {"docker", "docker.exe"}:
            raise RuntimeError("This diagnostic permits no Docker execution")
        return original_popen(*args, **kwargs) if command is None else original_popen(
            command, *args, **kwargs)

    with patch.object(socket.socket, "connect", forbidden), patch.object(
        subprocess, "Popen", guarded,
    ):
        yield


def source_inventory(root):
    paths = sorted((root / "patchloop").rglob("*.py"))
    paths += [Path(__file__).resolve(), root / "tests/test_dev_probe_cases.py",
              root / "tests/test_dev_probes.py",
              root / "tasks/smoke/csv-quoted-newline/public.yaml"]
    paths += sorted((root / "fixtures/repositories/mini-data-utils").rglob("*.py"))
    return {path.relative_to(root).as_posix(): sha256_bytes(path.read_bytes()) for path in paths}


def protocol(root):
    return {
        "schema_version": "finish-reproduction-protocol-v1", "official": False,
        "question": "Does fixed original-case evidence affect submission while preserving "
                    "verified and explicitly unverified paths?",
        "design": "Same-current-runtime OFF/ON ablation; one deterministic control per cell.",
        "conditions": list(CONDITIONS), "arms": list(ARMS), "repeat_count": 1,
        "OFF": "Mock only completion_reproduction.review to empty-case state during finish; "
               "no automatic replay or original-case gate. Audit real evidence separately.",
        "ON": "Unmodified runner completion batch and gateway finish rule.",
        "decisions": "Fixed public reproduction(s), source read, fixed edit, helper, visible "
                     "checks, finish, duplicate identical finish to audit idempotency.",
        "expectations": EXPECTATIONS,
        "adoption_criterion": "All fixed protocol controls behave as declared; runtime "
                              "adoption/repair effectiveness is not evaluated by this diagnostic.",
        "stop": "Stop all cells on runtime hash drift, deadline, unexpected action failure, "
                "identity/idempotency error, or mismatch with a frozen control expectation.",
        "bounds": {"total_seconds": TOTAL_SECONDS, "subprocess_seconds": SUBPROCESS_SECONDS,
                   "model_calls": 0, "provider_calls": 0, "cost_usd": "0", "reruns": 0},
        "backend": "Trusted tests.test_dev_probe_cases.ExecutingProbe plus LocalSandbox; "
                   "real local subprocesses with simulated probe container identity. No Docker.",
        "limits": "Scripted decisions, development-exposed fixture, fixed deliberately bad "
                  "and proper candidates. No independent acceptance/evaluator, live model, "
                  "statistical trial, repair improvement, or causal cognitive claim.",
        "source_inventory": source_inventory(root),
    }


def write_new(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n")


def run_cell(root, output, condition, arm, *, deadline, protocol_hash):
    started = monotonic()
    row_id = condition + "_" + arm.lower()
    journal = DevJournal(output / row_id, "run_dev_" + row_id.replace("_", ""))
    journal.append("local_control_frozen", {
        "protocol_hash": protocol_hash, "condition": condition, "arm": arm,
        "official": False, "independent_acceptance": "NOT_RUN",
    })
    task = load_public_task(root / "tasks/smoke/csv-quoted-newline/public.yaml")
    manager = WorkspaceManager(root / "fixtures/repositories", output / row_id / "workspaces")
    workspace = manager.create(row_id, task.repository.url, task.repository.base_commit,
                               deadline=ExecutionDeadline.from_remaining(
                                   min(SUBPROCESS_SECONDS, deadline.check())))
    backend = trusted_probe()
    gateway = DevToolGateway(workspace=workspace, public_task=task, journal=journal,
                             sandbox=BoundedChecks(), probe_sandbox=backend,
                             limits=DevLimits(max_tool_actions=30), deadline=deadline)
    counters = runner._RunCounters()

    def execute(request):
        # An operation cap also bounds every Git helper subprocess, not just the
        # trusted probe and public check. Cleanup remains the ordinary runner's.
        gateway.deadline = ExecutionDeadline.from_remaining(
            min(SUBPROCESS_SECONDS, deadline.check()))
        counters.tool_actions += 1
        result = gateway.execute(request)
        if result.status != "succeeded":
            raise RuntimeError(f"{row_id}: unexpected {request.name} failure: {result.message}")
        return result

    baseline = []
    if condition != "no_original":
        baseline.append(execute(original_case(task)))
        if baseline[-1].output["reproduction"]["comparison"] != "mismatched":
            raise RuntimeError("The frozen original case did not reproduce the baseline defect")
    if condition == "proper_repair":
        baseline.append(execute(original_case(task, normal=True)))
        if baseline[-1].output["reproduction"]["comparison"] != "matched":
            raise RuntimeError("The frozen normal-input baseline control did not match")
    execute(call("read_file", "source", {"path": "mini_data_utils/csvlite.py",
                                          "start_line": 1, "end_line": 80}, "inspect"))
    execute(mutation(condition))
    helper = execute(call("run_probe", "helper", {
        "question": "Does the unchanged simple-input helper work?",
        "python_source": "from mini_data_utils.csvlite import parse_rows\n"
                         f"assert parse_rows({NORMAL!r}) == {NORMAL_EXPECTED!r}",
        "replay_action_id": None, "purpose": {"kind": "helper"},
    }, "verify"))
    if helper.output["status"] != "passed":
        raise RuntimeError("The helper must pass before the completion intervention")
    checks = [execute(call("run_check", "check-" + check.id, {"check_id": check.id}, "verify"))
              for check in task.visible_checks]
    if not gateway.ready_to_submit():
        raise RuntimeError("The control failed the unchanged visible-check eligibility rule")
    real_review = completion_reproduction.review

    def audit():
        return real_review(journal.events(), gateway.current_diff_hash,
                           public_task=task, run_id=journal.run_id)

    before = audit()
    probes_before_finish = backend.calls
    finish = call("finish_task", "finish", {
        "assessment": "Fixed protocol decision: helper and visible checks passed; submit.",
    }, "finish")

    def disabled_review(events, current_diff, *, public_task=None, run_id):
        return real_review([], current_diff, public_task=public_task, run_id=run_id)

    ablation = patch.object(completion_reproduction, "review", disabled_review)
    with ablation if arm == "OFF" else nullcontext():
        gateway.deadline = ExecutionDeadline.from_remaining(
            min(SUBPROCESS_SECONDS, deadline.check()))
        counters.tool_actions += 1
        result = runner._execute_completion_batch(
            calls=[finish], journal=journal, gateway=gateway, counters=counters,
            active_elapsed_ms=lambda: int((monotonic() - started) * 1000),
        )[0]
        probes_after_finish = backend.calls
        replayed = runner._execute_completion_batch(
            calls=[finish], journal=journal, gateway=gateway, counters=counters,
            active_elapsed_ms=lambda: int((monotonic() - started) * 1000),
        )[0]
    if not replayed.replayed or backend.calls != probes_after_finish:
        raise RuntimeError("Duplicate finish repeated an execution or failed action replay")
    after = audit()
    verification = result.output.get("submission_verification", {})
    # Failed gateway results carry details separately; the independent current
    # projection above is the authoritative diagnostic view for both arms.
    observed = "accepted" if result.status == "succeeded" else "rejected"
    if arm == "ON":
        observed += "_" + after["status"]
    expected = EXPECTATIONS[condition][arm]
    row = {
        "row_id": row_id, "condition": condition, "arm": arm, "official": False,
        "expected": expected, "observed": observed, "control_pass": observed == expected,
        "finish_status": result.status, "finish_error": result.error_code,
        "completion_policy": "disabled_old_finish_rule" if arm == "OFF"
                             else completion_reproduction.POLICY,
        "returned_verification": verification, "real_evidence_before": before,
        "real_evidence_after": after, "independent_acceptance": "NOT_RUN",
        "candidate_patch_hash": gateway.current_diff_hash,
        "candidate_patch": gateway.current_diff.patch,
        "visible_check_passes": [bool(item.output["passed"]) for item in checks],
        "helper_status": helper.output["status"], "probe_executions": backend.calls,
        "completion_probe_executions": probes_after_finish - probes_before_finish,
        "duplicate_probe_executions": backend.calls - probes_after_finish,
        "duplicate_finish_replayed": replayed.replayed,
        "tool_actions": counters.tool_actions, "model_calls": 0, "provider_calls": 0,
        "duration_ms": round((monotonic() - started) * 1000),
        "journal": str(journal.path), "workspace": str(workspace),
    }
    artifact = ArtifactStore(journal.root / "artifacts").put_json(row)
    journal.append("local_control_finished", {
        "result": artifact.model_dump(mode="json"), "control_pass": row["control_pass"],
    })
    write_new(journal.root / "result.json", row)
    journal.events()  # Validate the complete persisted hash chain before returning.
    return row


def run(output):
    root, output = repository_root(), Path(output).resolve()
    if output.is_relative_to(root):
        raise ValueError("Generated experiment state must be outside the repository")
    output.mkdir(parents=True, exist_ok=False)
    started = monotonic()
    deadline = ExecutionDeadline.from_remaining(TOTAL_SECONDS)
    plan = protocol(root)
    plan["git_head"] = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True,
        timeout=SUBPROCESS_SECONDS,
    ).stdout.strip()
    plan_hash = sha256_json(plan)
    journal = DevJournal(output, "run_dev_finishreproductioncontrols")
    journal.append("protocol_frozen", {"protocol_hash": plan_hash, "protocol": plan})
    write_new(output / "protocol.json", plan)
    rows = []
    try:
        with local_only():
            for condition in CONDITIONS:
                for arm in ARMS:
                    deadline.check()
                    if source_inventory(root) != plan["source_inventory"]:
                        raise RuntimeError("Runtime/source drift after protocol freeze")
                    row = run_cell(root, output, condition, arm, deadline=deadline,
                                   protocol_hash=plan_hash)
                    rows.append(row)
                    journal.append("control_result", {"row_id": row["row_id"],
                                                        "control_pass": row["control_pass"],
                                                        "journal": row["journal"]})
                    if not row["control_pass"]:
                        raise RuntimeError("Frozen control expectation failed: " + row["row_id"])
            if source_inventory(root) != plan["source_inventory"]:
                raise RuntimeError("Runtime/source drift during the last control")
    except BaseException as exc:
        journal.append("experiment_stopped", {"type": type(exc).__name__, "message": str(exc),
                                               "completed_rows": len(rows)})
        raise
    summary = {
        "protocol_hash": plan_hash, "official": False, "claim_eligible": False,
        "status": "PROTOCOL_CONTROLS_PASS", "row_count": len(rows),
        "controls_passed": sum(row["control_pass"] for row in rows), "rows": rows,
        "duration_ms": round((monotonic() - started) * 1000), "cost_usd": "0",
        "model_calls": 0, "provider_calls": 0, "independent_acceptance": "NOT_RUN",
        "interpretation": "Completion protocol behavior only. Fixed candidate implementations "
                          "cannot show improved model repair performance or general accuracy.",
    }
    artifact = ArtifactStore(output / "artifacts").put_json(summary)
    journal.append("experiment_finished", {"result": artifact.model_dump(mode="json")})
    write_new(output / "result.json", summary)
    journal.events()
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="Fresh external state directory")
    args = parser.parse_args()
    result = run(args.output)
    print(json.dumps({key: result[key] for key in (
        "status", "row_count", "controls_passed", "duration_ms", "cost_usd",
    )}))


if __name__ == "__main__":
    main()
