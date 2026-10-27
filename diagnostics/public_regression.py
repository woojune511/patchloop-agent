"""Run registered public checks between edits and reuse exact settled receipts."""

from __future__ import annotations

import copy
from pathlib import Path

from patchloop.artifacts import ArtifactStore
from patchloop.dev.check_feedback import check_failure_diagnostics, output_tail
from patchloop.dev.contracts import DevLimits, DevToolResult, RequestedTool
from patchloop.dev.runner import _batch_execution_abort
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import DevToolGateway
from patchloop.errors import ContractError
from patchloop.util import sha256_json

STDOUT_CHARS = 8_000
STDERR_CHARS = 2_000


def require(condition, message):
    if not condition:
        raise ContractError(message)


def _environment_hash(loaded):
    environment = getattr(loaded, "environment", None)
    return (None if environment is None
            else sha256_json(environment.model_dump(mode="json")))


class PublicRegressionRecheck:
    """At most ``max_passes`` distinct diffs; no retry of uncertain execution.

    A failed assertion is a completed observation. Missing or uncertain receipts
    abort the controller, including after reconstruction or a different edit.
    """

    def __init__(self, loaded, model_gateway, root, *, max_passes=2):
        require(type(max_passes) is int and max_passes > 0,
                "public regression requires a positive pass allowance")
        self.loaded, self.model_gateway = loaded, model_gateway
        self.root, self.max_passes = Path(root), max_passes
        self.public = loaded.public.model_copy(deep=True)
        self.checks = tuple(self.public.visible_checks)
        require(bool(self.checks), "public regression requires registered visible checks")
        self.by_id = {check.id: check for check in self.checks}
        self.binding = {
            "public_task_hash": sha256_json(self.public.model_dump(mode="json")),
            "checks_hash": sha256_json([check.model_dump(mode="json") for check in self.checks]),
            "environment_hash": _environment_hash(loaded),
            "max_passes": max_passes,
        }
        self.journal = DevJournal(self.root, "run_dev_publicregression")
        self.store = ArtifactStore(self.root / "artifacts")
        bindings = [event["payload"] for event in self.journal.events()
                    if event["event_type"] == "public_regression_bound"]
        require(not bindings or bindings == [self.binding], "public regression binding changed")
        if not bindings:
            self.journal.append("public_regression_bound", self.binding)

    def _call(self, diff_hash, check_id):
        identity = sha256_json({**self.binding, "candidate_diff_hash": diff_hash,
                                "check_id": check_id})[7:39]
        return RequestedTool(name="run_check", action_id="public-regression-" + identity,
                             arguments={"check_id": check_id})

    @staticmethod
    def _input_hash(call):
        return sha256_json({"tool": call.name, "arguments": call.arguments})

    def _validate_result(self, result, diff_hash, check):
        call = self._call(diff_hash, check.id)
        output = result.output
        require(result.tool == call.name and result.action_id == call.action_id
                and result.input_hash == self._input_hash(call)
                and result.workspace_diff_hash == diff_hash
                and output.get("check_id") == check.id and output.get("diff_hash") == diff_hash,
                "public regression receipt identity or diff changed")
        abort, reason = _batch_execution_abort([result])
        require(abort is None, "public regression execution aborted: " + str(reason))
        require(result.status == "succeeded" and result.error_code is None
                and all(output.get(key) is False for key in (
                    "timed_out", "cleanup_failed", "deadline_exhausted"))
                and type(output.get("truncated")) is bool
                and type(output.get("exit_code")) is int and output["exit_code"] >= 0
                and type(output.get("passed")) is bool
                and all(isinstance(output.get(key), str) for key in ("stdout", "stderr")),
                "public regression receipt is incomplete or execution is uncertain")
        policy = output.get("execution_policy")
        require(not isinstance(policy, dict)
                or policy.get("cleanup_status", "confirmed") == "confirmed",
                "public regression cleanup is unconfirmed")
        require(output["exit_code"] not in check.infrastructure_exit_codes,
                "public regression infrastructure exit is uncertain")
        require(output["passed"] == (output["exit_code"] in check.expected_exit_codes),
                "public regression verdict differs from its registered exit contract")

    def _receipts(self):
        require(sha256_json(self.loaded.public.model_dump(mode="json"))
                == self.binding["public_task_hash"]
                and _environment_hash(self.loaded) == self.binding["environment_hash"],
                "public regression task/check/environment configuration changed")
        events = self.journal.events()
        starts = [event["payload"] for event in events if event["event_type"] == "action_started"]
        finished = {event["payload"]["action_id"]: event["payload"]["result"]
                    for event in events if event["event_type"] == "action_finished"}
        require(all(row["action_id"] in finished for row in starts),
                "public regression has an unfinished action; no automatic retry")
        require(set(finished) == {row["action_id"] for row in starts},
                "public regression receipt lacks its action start")
        receipts, diffs = {}, set()
        for started in starts:
            diff = started.get("baseline_diff_hash")
            check_id = started.get("arguments", {}).get("check_id")
            require(isinstance(diff, str) and bool(diff) and check_id in self.by_id,
                    "public regression action binding is incomplete")
            call = self._call(diff, check_id)
            require(started.get("tool") == call.name and started["action_id"] == call.action_id
                    and started.get("arguments") == call.arguments
                    and started.get("input_hash") == self._input_hash(call),
                    "public regression action identity changed")
            # action_result also checks conflicting starts/results. Return the original
            # durable bytes, not its replay-marked presentation copy.
            self.journal.action_result(call.action_id, self._input_hash(call))
            result = DevToolResult.model_validate(finished[call.action_id])
            self._validate_result(result, diff, self.by_id[check_id])
            receipts[(diff, check_id)] = result.model_dump(mode="json")
            diffs.add(diff)
        require(len(diffs) <= self.max_passes, "public regression pass allowance exhausted")
        return receipts, diffs

    @property
    def host_actions(self):
        return sum(event["event_type"] == "action_started" for event in self.journal.events())

    def needed_seconds(self, *, for_new_diff=False):
        receipts, _ = self._receipts()
        diff = self.model_gateway.current_diff_hash
        return sum(check.timeout_seconds + 5 for check in self.checks
                   if for_new_diff or (diff, check.id) not in receipts)

    def _gateway(self):
        original = self.model_gateway
        return DevToolGateway(workspace=original.workspace, public_task=self.public,
            sandbox=original.sandbox, journal=self.journal, deadline=original.deadline,
            limits=DevLimits(max_tool_actions=self.max_passes * len(self.checks)))

    def current_receipts(self):
        diff = self.model_gateway.current_diff_hash
        receipts, _ = self._receipts()
        if any((diff, check.id) not in receipts for check in self.checks):
            return None
        require(self.model_gateway.current_diff_hash == diff,
                "candidate changed while reading public regression receipts")
        return tuple(copy.deepcopy(receipts[(diff, check.id)]) for check in self.checks)

    def check(self):
        diff = self.model_gateway.current_diff_hash
        receipts, diffs = self._receipts()
        missing = [check for check in self.checks if (diff, check.id) not in receipts]
        reused = not missing
        if missing:
            require(diff in diffs or len(diffs) < self.max_passes,
                    "public regression pass allowance exhausted")
            self.model_gateway.deadline.check()
            gateway = self._gateway()
            for check in missing:
                require(gateway.current_diff_hash == diff
                        and self.model_gateway.current_diff_hash == diff,
                        "public regression candidate changed before dispatch")
                result = gateway.execute(self._call(diff, check.id))
                require(gateway.current_diff_hash == diff
                        and self.model_gateway.current_diff_hash == diff,
                        "public regression changed the candidate")
                self._validate_result(result, diff, check)
                receipts[(diff, check.id)] = result.model_dump(mode="json")
        require(self.model_gateway.current_diff_hash == diff,
                "candidate changed during public regression")
        checks, references = [], []
        for check in self.checks:
            raw = receipts[(diff, check.id)]
            output = raw["output"]
            exception, summary = check_failure_diagnostics(output["stdout"], output["stderr"])
            failure = output.get("public_check_failure")
            public_failure = ({key: copy.deepcopy(failure.get(key)) for key in (
                "check_id", "diff_hash", "failure_signature", "exception_type", "failure_summary",
                "mapping_status", "public_location")} if isinstance(failure, dict) else None)
            stdout, stdout_omitted = output_tail(output["stdout"], STDOUT_CHARS)
            stderr, stderr_omitted = output_tail(output["stderr"], STDERR_CHARS)
            checks.append({"check_id": check.id, "passed": output["passed"],
                "exit_code": output["exit_code"],
                "exception_type": exception if not output["passed"] else None,
                "failure_summary": summary if not output["passed"] else None,
                "public_check_failure": public_failure if not output["passed"] else None,
                "stdout_tail": stdout, "stderr_tail": stderr,
                "output_truncated": output["truncated"],
                "stdout_omitted": stdout_omitted, "stderr_omitted": stderr_omitted})
            references.append(self.store.put_json(raw).model_dump(mode="json"))
        feedback = {"schema": "public-regression-feedback-v1", "candidate_diff_hash": diff,
            "checks_hash": self.binding["checks_hash"],
            "status": "passed" if all(check["passed"] for check in checks) else "failed",
            "checks": checks, "receipts": references, "receipts_reused": reused,
            "task_acceptance": "NOT_ASSESSED"}
        self.journal.append("public_regression_feedback", feedback)
        return feedback
