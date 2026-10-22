"""Frozen, provider-free acquisition controls; truthful delivery is enabled in both arms."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from time import monotonic

from diagnostics import finish_reproduction_experiment as local
from patchloop.artifacts import ArtifactStore
from patchloop.deadline import ExecutionDeadline
from patchloop.dev import original_obligation, runner
from patchloop.dev.contracts import DevLimits
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import DevToolGateway
from patchloop.repository import WorkspaceManager
from patchloop.runtime import repository_root
from patchloop.task_loader import load_public_task
from patchloop.util import sha256_bytes, sha256_json

CONDITIONS = ("helper_until_cap", "acquired_correct", "acquired_wrong", "baseline_matched_twice")
ARMS = ("none", original_obligation.ACQUISITION)


def inventory(root):
    return {
        **local.source_inventory(root),
        Path(__file__).resolve().relative_to(root).as_posix(): sha256_bytes(
            Path(__file__).read_bytes()),
        "tests/test_original_obligation.py": sha256_bytes(
            (root / "tests/test_original_obligation.py").read_bytes()),
    }


def protocol(root):
    return {
        "schema_version": "original-obligation-control-v1", "official": False,
        "question": "Does bounded pre-edit acquisition prevent helper-only early edits, "
                    "release within its cap, and preserve honest original-verification delivery?",
        "design": "One fixed script per condition and acquisition policy on the same runtime. "
                  "Truthful delivery and completion replay remain enabled in both arms.",
        "conditions": list(CONDITIONS), "arms": list(ARMS), "repeat_count": 1,
        "script": {
            "helper_until_cap": "Read, helper PASS, attempt comment edit, four more reads, "
                                "apply same comment edit only if earlier attempt rejected, "
                                "visible check, finish, duplicate finish.",
            "acquired_correct": "Original mismatch + normal control, read, fixed proper "
                                "CSV edit, visible check, finish, duplicate finish.",
            "acquired_wrong": "Original mismatch, read, comment edit, visible check, "
                              "finish, duplicate finish; final original remains refuted.",
            "baseline_matched_twice": "Two original-purpose normal-input matches, read, "
                                      "proper edit, visible check, finish, duplicate finish.",
        },
        "expected": {
            "helper_until_cap": "none admits early edit; bounded rejects it then releases "
                                "at six investigation actions; both deliver unverified.",
            "acquired_correct": "Both deliver cases_verified; original and normal replay match.",
            "acquired_wrong": "Both reject finish as refuted.",
            "baseline_matched_twice": "Both deliver unverified; baseline success never "
                                      "establishes the reported failure.",
        },
        "caps": {"original_attempts": 2, "investigation_actions": 6,
                 "total_seconds": 180, "local_operation_seconds": 10, "model_calls": 0,
                 "provider_calls": 0, "cost_usd": "0", "valid_run_retries": 0},
        "stop": "Stop all remaining rows on changed runtime/source hashes, deadline, "
                "unexpected action failure, or a frozen control expectation violation.",
        "backend": "Existing trusted ExecutingProbe and bounded LocalSandbox subprocesses; "
                   "probe container identity is simulated test metadata; no real Docker.",
        "limitations": "Development-exposed public CSV and fixed implementations. No model "
                       "decision, independent acceptance, general repair improvement, or "
                       "statistical estimate. Setup faults, crashes and protected-budget release "
                       "are covered by separate unit/integration tests, not these eight rows.",
        "source_inventory": inventory(root),
        "git_head": subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True,
                                   capture_output=True, text=True, timeout=10).stdout.strip(),
    }


def run_cell(root, output, condition, arm, *, deadline, protocol_hash):
    started = monotonic()
    row_id = condition + "_" + arm.replace("-", "")
    journal = DevJournal(output / row_id, "run_dev_" + row_id.replace("_", ""))
    journal.append("local_control_frozen", {
        "protocol_hash": protocol_hash, "condition": condition, "acquisition_policy": arm,
        "official": False, "independent_acceptance": "NOT_RUN",
    })
    task = load_public_task(root / "tasks/smoke/csv-quoted-newline/public.yaml")
    manager = WorkspaceManager(root / "fixtures/repositories", journal.root / "workspaces")
    workspace = manager.create(
        row_id, task.repository.url, task.repository.base_commit,
        deadline=ExecutionDeadline.from_remaining(min(10, deadline.check())),
    )
    backend = local.trusted_probe()
    gateway = DevToolGateway(
        workspace=workspace, public_task=task, sandbox=local.BoundedChecks(), journal=journal,
        limits=DevLimits(max_tool_actions=30), probe_sandbox=backend,
        reproduction_acquisition=arm, deadline=deadline,
    )
    counters = runner._RunCounters()
    states = []

    def state(label):
        current = gateway.completion_verification(diff_hash=gateway.current_diff_hash)
        states.append({"label": label, "completion": current})
        return current["original_obligation"]

    def execute(request, *, failure_expected=False):
        gateway.deadline = ExecutionDeadline.from_remaining(min(10, deadline.check()))
        counters.tool_actions += 1
        result = gateway.execute(request)
        if result.status != "succeeded" and not failure_expected:
            raise RuntimeError(f"{row_id}: unexpected {request.name}: {result.message}")
        state(request.action_id)
        return result

    def read(number):
        return execute(local.call("read_file", f"read-{number}", {
            "path": "mini_data_utils/csvlite.py", "start_line": 1, "end_line": 80,
        }, "inspect"))

    initial = state("initial")
    early_edit = None
    if condition == "helper_until_cap":
        read(1)
        helper = execute(local.call("run_probe", "helper", {
            "question": "Does the fixed helper normal input pass?",
            "python_source": "from mini_data_utils.csvlite import parse_rows\n"
                             f"assert parse_rows({local.NORMAL!r}) == {local.NORMAL_EXPECTED!r}",
            "replay_action_id": None, "purpose": {"kind": "helper"},
        }, "verify"))
        if helper.output["status"] != "passed":
            raise RuntimeError("Helper control must pass")
        early_edit = execute(local.mutation("wrong_comment"), failure_expected=True)
        if (early_edit.status == "failed") != (arm == original_obligation.ACQUISITION):
            raise RuntimeError("Early edit did not follow the frozen acquisition policy")
        for number in range(3, 7):
            read(number)
        released = state("after-six-investigations")
        if arm == original_obligation.ACQUISITION and (
            released["stage"] != "released" or released["investigation_actions"] != 6
            or released["reason"] != "investigation_action_limit"
        ):
            raise RuntimeError("Bounded acquisition did not release at its frozen action cap")
        if early_edit.status == "failed":
            execute(local.mutation("wrong_comment").model_copy(update={"action_id": "later-edit"}))
    else:
        if condition == "baseline_matched_twice":
            for index in range(2):
                result = execute(local.original_case(task, normal=True).model_copy(
                    update={"action_id": f"normal-{index}"}))
                if result.output["reproduction"]["comparison"] != "matched":
                    raise RuntimeError("Normal-input baseline did not match")
        else:
            result = execute(local.original_case(task))
            if result.output["reproduction"]["comparison"] != "mismatched":
                raise RuntimeError("Original defect was not reproduced")
            if condition == "acquired_correct":
                execute(local.original_case(task, normal=True))
        read(1)
        edit_kind = "wrong_comment" if condition == "acquired_wrong" else "proper_repair"
        execute(local.mutation(edit_kind))

    for check in task.visible_checks:
        result = execute(local.call("run_check", "check-" + check.id,
                                    {"check_id": check.id}, "verify"))
        if not result.output["passed"]:
            raise RuntimeError("The fixed candidate's visible checks must pass")
    before_finish = state("before-finish")
    probes_before = backend.calls
    finish = local.call("finish_task", "finish", {
        "assessment": "Frozen candidate submission after public visible checks.",
    }, "finish")
    gateway.deadline = ExecutionDeadline.from_remaining(min(10, deadline.check()))
    counters.tool_actions += 1
    result = runner._execute_completion_batch(
        calls=[finish], journal=journal, gateway=gateway, counters=counters,
        active_elapsed_ms=lambda: round((monotonic() - started) * 1000),
    )[0]
    probes_after = backend.calls
    repeated = runner._execute_completion_batch(
        calls=[finish], journal=journal, gateway=gateway, counters=counters,
        active_elapsed_ms=lambda: round((monotonic() - started) * 1000),
    )[0]
    after_finish = state("after-finish")
    if not repeated.replayed or backend.calls != probes_after:
        raise RuntimeError("Duplicate finish repeated a probe or failed idempotency")
    expected = ("rejected_refuted" if condition == "acquired_wrong" else "cases_verified_delivery"
                if condition == "acquired_correct" else "unverified_delivery")
    observed = (result.output.get("delivery_state") if result.status == "succeeded"
                else "rejected_" + after_finish["status"])
    row = {
        "row_id": row_id, "condition": condition, "acquisition_policy": arm, "official": False,
        "expected": expected, "observed": observed, "control_pass": expected == observed,
        "initial_obligation": initial, "before_finish": before_finish, "after_finish": after_finish,
        "early_edit_status": early_edit.status if early_edit else "NOT_APPLICABLE",
        "states": states, "finish_status": result.status,
        "finish_output": result.output, "candidate_patch_hash": gateway.current_diff_hash,
        "candidate_patch": gateway.current_diff.patch, "tool_actions": counters.tool_actions,
        "probe_executions": backend.calls, "automatic_replays": probes_after - probes_before,
        "duplicate_probe_executions": backend.calls - probes_after,
        "model_calls": 0, "provider_calls": 0, "independent_acceptance": "NOT_RUN",
        "duration_ms": round((monotonic() - started) * 1000), "journal": str(journal.path),
    }
    artifact = ArtifactStore(journal.root / "artifacts").put_json(row)
    journal.append("local_control_finished", {"result": artifact.model_dump(mode="json")})
    local.write_new(journal.root / "result.json", row)
    journal.events()
    return row


def run(output):
    root, output = repository_root(), Path(output).resolve()
    if output.is_relative_to(root):
        raise ValueError("Generated state must be outside the repository")
    output.mkdir(parents=True, exist_ok=False)
    started = monotonic()
    deadline = ExecutionDeadline.from_remaining(180)
    plan = protocol(root)
    protocol_hash = sha256_json(plan)
    journal = DevJournal(output, "run_dev_originalobligationcontrols")
    journal.append("protocol_frozen", {"protocol_hash": protocol_hash, "protocol": plan})
    local.write_new(output / "protocol.json", plan)
    rows = []
    try:
        with local.local_only():
            for condition in CONDITIONS:
                for arm in ARMS:
                    deadline.check()
                    if inventory(root) != plan["source_inventory"]:
                        raise RuntimeError("Source drift after freeze")
                    row = run_cell(root, output, condition, arm, deadline=deadline,
                                   protocol_hash=protocol_hash)
                    rows.append(row)
                    journal.append("control_result", {"row_id": row["row_id"],
                                                        "control_pass": row["control_pass"],
                                                        "journal": row["journal"]})
                    if not row["control_pass"]:
                        raise RuntimeError("Unexpected control outcome: " + row["row_id"])
            if inventory(root) != plan["source_inventory"]:
                raise RuntimeError("Source drift during final row")
    except BaseException as exc:
        journal.append("experiment_stopped", {"type": type(exc).__name__, "message": str(exc),
                                               "completed_rows": len(rows)})
        raise
    result = {
        "status": "PROTOCOL_CONTROLS_PASS", "official": False, "claim_eligible": False,
        "protocol_hash": protocol_hash, "rows": rows, "row_count": len(rows),
        "controls_passed": sum(row["control_pass"] for row in rows),
        "duration_ms": round((monotonic() - started) * 1000), "cost_usd": "0",
        "provider_calls": 0, "model_calls": 0, "independent_acceptance": "NOT_RUN",
        "interpretation": "Deterministic acquisition/verification protocol controls. "
                          "No live model repair-quality or generalization evidence.",
    }
    artifact = ArtifactStore(output / "artifacts").put_json(result)
    journal.append("experiment_finished", {"result": artifact.model_dump(mode="json")})
    local.write_new(output / "result.json", result)
    journal.events()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    result = run(parser.parse_args().output)
    print(json.dumps({key: result[key] for key in (
        "status", "controls_passed", "row_count", "duration_ms", "cost_usd",
    )}))


if __name__ == "__main__":
    main()
