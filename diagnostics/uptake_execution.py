"""Bounded continuation connector for the frozen SQLFluff B1/B2 uptake design.

The CLI only rehearses: synthetic SDK/probe receipts, no key, network or task
execution. The shared row executor uses the ordinary registered-tool runtime.
An actual paid invocation still requires separate exact-manifest authorization
and read-only model/price/environment readiness; a rehearsal is not that approval.
"""

from __future__ import annotations

import argparse
import ast
import copy
import json
import re
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path
from time import monotonic
from unittest.mock import patch

from diagnostics import observation_exposure as exposure
from diagnostics import uptake_checkpoint as checkpoint
from diagnostics.checkpoint_continuation import ScriptedClient, inherited_reads
from diagnostics.decision_sampler import require
from patchloop.agent.model import OpenAIResponsesAdapter
from patchloop.artifacts import ArtifactStore
from patchloop.deadline import ExecutionDeadline
from patchloop.dev import native_compaction, runner, segments
from patchloop.dev.cost import DevCostLedger, pricing_for_model
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError
from patchloop.repository import WorkspaceManager
from patchloop.runtime import git_commit, repository_root
from patchloop.sandbox import LocalSandbox
from patchloop.util import canonical_json, sha256_bytes, sha256_json


class BoundStop(BaseException):
    """Known pre-dispatch stop; never mistaken for a transport/count failure."""

    def __init__(self, reason, *, all_rows=False):
        self.reason, self.all_rows = reason, all_rows
        super().__init__(reason)


class Invocation:
    def __init__(self, journal, *, clock=monotonic, started=None):
        self.journal, self.clock = journal, clock
        self.started = clock() if started is None else started
        self.deadline = ExecutionDeadline(self.started + 2100, clock)
        self.counts = self.generations = 0
        self.ledger = DevCostLedger(Decimal("7.00"), pricing_for_model("gpt-5.4-2026-03-05"))
        self.stopped = False

    def check(self):
        if self.stopped or self.deadline.remaining_seconds() <= 0:
            raise BoundStop("invocation stopped or wall-time exhausted", all_rows=True)


class RowBudget(DevCostLedger):
    """Keep the historical ledger intact and charge only new settled usage."""

    def __init__(self, branch, group):
        super().__init__(branch.request.max_cost_usd, branch.pricing)
        self.spent_nanos = branch.initial_spent_nanos
        self.branch, self.group = branch, group
        self.counts = self.generations = 0
        self.pending = self.reservation = None

    def before_count(self):
        self.group.check()
        if self.group.counts >= 12 or self.group.generations >= 12:
            raise BoundStop("invocation call cap", all_rows=True)
        if self.counts >= 6 or self.generations >= 6:
            raise BoundStop("row call cap")

    def counted(self, request, operation):
        self.before_count()
        self.pending = None  # a failed/replaced count can never authorize a dispatch
        self.counts += 1
        self.group.counts += 1
        snapshot = copy.deepcopy(request)
        tokens = operation()
        require(type(tokens) is int and tokens >= 0, "invalid input count")
        self.pending = (snapshot, tokens)
        return tokens

    def admit(self, input_tokens, **kwargs):
        require(
            kwargs.get("desired_output_ceiling", 25000) == 25000, "fixed output ceiling changed"
        )
        if input_tokens > 60000:
            return None
        kwargs["minimum_output_ceiling"] = 25000
        row = super().admit(input_tokens, **kwargs)
        group = self.group.ledger.admit(input_tokens, **kwargs)
        if group is None:
            raise BoundStop("invocation cost cap", all_rows=True)
        self.reservation = row if row and group else None
        return self.reservation

    def dispatch(self, request, requested_input_tokens):
        self.group.check()
        pending, self.pending = self.pending, None
        require(
            pending is not None and pending == (request, requested_input_tokens),
            "dispatch differs from its fresh counted request",
        )
        require(
            request.get("max_output_tokens") == 25000
            and requested_input_tokens <= 60000
            and self.reservation is not None,
            "dispatch has no full-ceiling admission",
        )
        if self.group.generations >= 12:
            raise BoundStop("invocation generation cap", all_rows=True)
        if self.generations >= 6:
            raise BoundStop("row generation cap")
        self.generations += 1
        self.group.generations += 1

    def settle(self, **usage):
        # No cap/time check here: settle an already dispatched response even at the limit.
        require(self.reservation is not None, "settlement without admission")
        require(
            usage["input_tokens"] == self.reservation.input_tokens
            and 0 <= usage["cached_input_tokens"] <= usage["input_tokens"]
            and 0 <= usage["output_tokens"] <= self.reservation.output_ceiling,
            "reported usage exceeds counted/admitted tokens",
        )
        cost = super().settle(**usage)
        require(self.group.ledger.settle(**usage) == cost, "row/group pricing differs")
        self.group.journal.append(
            "uptake_new_usage",
            {
                "cell": self.branch.row["cell"],
                **usage,
                "provisional_cost_nanos": cost,
                "synthetic": self.branch.provider_free,
            },
        )
        require(
            cost <= self.reservation.reserved_cost_nanos
            and self.spent_nanos <= self.cap_nanos
            and self.group.ledger.spent_nanos <= self.group.ledger.cap_nanos,
            "usage exceeds admission; billing uncertain",
        )
        self.reservation = None
        return cost


def public_expected(oracle_source):
    for node in ast.parse(oracle_source).body:
        if (
            isinstance(node, ast.Assign)
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == "EXPECTED"
        ):
            value = ast.literal_eval(node.value)
            require(isinstance(value, str), "public oracle expectation is not text")
            return value.splitlines()
    return None  # local fixture oracle; frozen SQLFluff oracle always has EXPECTED


def exposure_gate(row, result, expected_lines=None):
    """Read only the unchanged public program's explicit target observation.

    An assertion failure, including a later ancillary one, is not an all-pass veto.
    Whole-output truncation is not a veto if the complete required target record
    and setup checks survived. Missing/partial necessary evidence stops the row.
    """
    output = result.output
    if output.get("cleanup_failed"):
        raise BoundStop("probe cleanup uncertain", all_rows=True)
    if result.error_code in {"RECOVERY_ERROR", "RESUME_CONTRACT_MISMATCH"}:
        raise BoundStop("probe recovery integrity uncertain", all_rows=True)
    require(
        result.action_id == row["action_id"] and result.tool == "run_probe",
        "seed receipt action changed",
    )
    require(
        output.get("source_hash") == row["probe"]["content_hash"], "seed receipt source changed"
    )
    setup = output.get("setup_checks", {})
    labels = {r.get("label"): r for r in setup.get("checks", []) if r.get("matched")}
    required = {"current_class"} if row["cell"] == "B1" else {"rule_name", "patched_name"}
    if (
        setup.get("status") != "passed"
        or not required <= labels.keys()
        or output.get("status") not in {"passed", "failed"}
        or output.get("timed_out")
        or output.get("deadline_exhausted")
    ):
        return {"exposed": False, "reason": "invalid or incomplete setup/execution"}
    records = []
    for line in output.get("stdout", "").splitlines():
        try:
            item = ast.literal_eval(line)
        except (SyntaxError, ValueError):
            continue
        if isinstance(item, dict):
            records.append(item)
    key = "cte_line" if row["cell"] == "B1" else "cte_target_line"
    targets = [r[key] for r in records if key in r]
    if len(targets) != 1 or not isinstance(targets[0], str):
        return {"exposed": False, "reason": "required CTE observation missing or ambiguous"}
    target = targets[0]
    # Exact public issue target line, reviewed when the fixed programs were frozen.
    if target.strip() != "my_id," and row["cell"] == "B1":
        return {"exposed": False, "reason": "target line is not the public CTE target"}
    if row["cell"] == "B2":
        summaries = [r for r in records if "cte_target_line" in r]
        full = [r["cte_lines"] for r in records if "cte_lines" in r]
        if (
            len(full) != 1
            or not isinstance(full[0], list)
            or len(full[0]) < 3
            or full[0][2] != target
            or summaries[0].get("cte_leading_spaces") != len(target) - len(target.lstrip(" "))
        ):
            return {"exposed": False, "reason": "CTE observation is inconsistent or incomplete"}
        if expected_lines is not None:
            return {
                "exposed": full[0] != expected_lines,
                "target": target,
                "reason": "full CTE output compared with the frozen public expectation",
            }
    if row["cell"] == "B1" and target == "        my_id," and "path" in row["probe"]:
        # A CTE assertion can disconfirm preservation even when another line differs.
        # The later YAML assertion must never be mistaken for this assertion.
        source = ast.parse(checkpoint.read_bound(row["probe"]).decode())
        assertion = next(
            node
            for node in source.body
            if isinstance(node, ast.Assert)
            and isinstance(node.test, ast.Compare)
            and isinstance(node.test.left, ast.Name)
            and node.test.left.id == "cte_result"
        )
        frames = re.findall(r'File "([^"]+)", line (\d+)', output.get("stderr", ""))
        if (
            frames
            and frames[-1] == ("<patchloop-probe>", str(assertion.lineno))
            and re.search(r"^AssertionError(?::|$)", output.get("stderr", ""), re.M)
        ):
            return {
                "exposed": True,
                "target": target,
                "reason": "the frozen CTE equality assertion failed",
            }
    return {
        "exposed": target != "        my_id,",
        "target": target,
        "reason": "CTE target differs from public expectation"
        if target != "        my_id,"
        else "no disconfirming CTE observation",
    }


def verify_first_input(branch, request, seed_receipt):
    require(request["input"][-1] == branch.selected["input"][-1], "B instruction lost")

    def native(items):
        return [
            i
            for i in items
            if i.get("type") in {"reasoning", "function_call", "function_call_output"}
        ]

    prior, current = native(branch.selected["input"]), native(request["input"])
    require(current[: len(prior)] == prior, "first continuation lost the saved native prefix")
    tail = current[len(prior) :]
    saved = branch.saved.provider_continuation.output_order
    call = branch.saved.tool_calls[0]
    expected_reason = {
        "type": "reasoning",
        "id": saved[0].id,
        "encrypted_content": saved[0].encrypted_content,
        "summary": [],
        **({"status": saved[0].status} if saved[0].status else {}),
    }
    require(
        len(tail) == 3
        and tail[0] == expected_reason
        and tail[1]["type"] == "function_call"
        and tail[1]["call_id"] == call.action_id
        and tail[1]["name"] == call.name
        and json.loads(tail[1]["arguments"]) == branch.selected_call_arguments
        and tail[2]["type"] == "function_call_output"
        and tail[2]["call_id"] == seed_receipt.action_id,
        "saved ordered output changed",
    )
    delivered = json.loads(tail[2]["output"])
    projected = runner.project_probe_result(seed_receipt.model_dump(mode="json"))
    require(
        delivered["output"] == projected["output"]
        and delivered["observation"] == projected["observation"],
        "diagnostic output was rewritten",
    )


@contextmanager
def submitted_assessment(branch, group, oracle_source):
    """Assess only an actual submitted patch, outside solver input and action budget."""
    evaluate = runner.EvaluationEngine.evaluate
    used = []

    def assess(engine, task_dir, patch_path, manifest, **kwargs):
        require(not used, "submitted evaluation repeated")
        used.append(True)
        group.check()
        submitted = kwargs["submitted_patch_artifact"]
        require(
            sha256_bytes(Path(patch_path).read_bytes())
            == submitted.content_hash
            == WorkspaceManager.diff_summary(branch.workspace).patch_hash,
            "terminal public oracle and submitted diff differ",
        )
        branch.journal.append(
            "uptake_final_diff_sealed",
            {
                "patch_hash": submitted.content_hash,
                "oracle_source_hash": sha256_bytes(oracle_source.encode()),
                "solver_feedback": False,
            },
        )
        public_events = []
        for event in branch.journal.events():
            if event["event_type"] in {
                "action_started",
                "action_finished",
                "turn_decision_recorded",
                "working_notes_updated",
            }:
                public_events.append(
                    {
                        "sequence": event["sequence"],
                        "event_type": event["event_type"],
                        "payload": {
                            k: v for k, v in event["payload"].items() if k != "continuation_ref"
                        },
                    }
                )
        review = branch.store.put_json(
            {
                "public_task": branch.package.public.model_dump(mode="json"),
                "submitted_patch": submitted.model_dump(mode="json"),
                "public_events": public_events,
                "uptake_and_repair_review": "Review before opening private acceptance verdicts.",
            }
        )
        branch.journal.append(
            "uptake_public_review_packet",
            {"artifact": review.model_dump(mode="json"), "private_verdict_present": False},
        )
        dependencies = (
            runner.load_dependencies(
                branch.request.prepared_probe_dependencies,
                branch.package.public,
                branch.envelope.probe_dependencies,
            )
            if branch.request.prepared_probe_dependencies
            else None
        )
        probe = runner.DockerProbeSandbox(
            **({"dependencies": dependencies} if dependencies else {})
        )
        oracle_deadline = ExecutionDeadline(
            min(group.deadline.expires_at, group.clock() + 30), group.clock
        )
        require(
            probe.preflight(deadline=oracle_deadline)
            == {
                "image_digest": branch.envelope.probe_image_digest,
                "profile_hash": branch.envelope.probe_profile_hash,
            },
            "terminal probe identity changed",
        )
        receipt = probe.run_probe(
            branch.workspace,
            "Frozen public issue expectation on final diff.",
            oracle_source,
            deadline=oracle_deadline,
            execution_identity={
                "run_id": branch.journal.run_id,
                "action_id": "uptake_final_public_oracle",
                "input_hash": submitted.content_hash,
            },
        )
        require(
            WorkspaceManager.diff_summary(branch.workspace).patch_hash == submitted.content_hash,
            "terminal oracle mutated the candidate",
        )
        branch.journal.append(
            "uptake_terminal_public_oracle",
            {"patch_hash": submitted.content_hash, "receipt": receipt, "solver_feedback": False},
        )
        if receipt.get("cleanup_failed"):
            raise BoundStop("terminal oracle cleanup uncertain", all_rows=True)
        group.check()
        # Evaluation has its own 330s cap; it cannot borrow unused solver time.
        kwargs["deadline"] = ExecutionDeadline(
            min(group.clock() + 330, group.deadline.expires_at), group.clock
        )
        return evaluate(engine, task_dir, patch_path, manifest, **kwargs)

    with patch.object(runner.EvaluationEngine, "evaluate", assess):
        yield


def run_row(branch, group, oracle_source, *, client=None):
    """Single-use connector. Mock transports are supplied by offline_environment."""
    require(
        branch.provider_free == isinstance(client, ScriptedClient),
        "offline rows require a finite synthetic transport",
    )
    require(
        not any(e["event_type"] == "uptake_execution_started" for e in branch.journal.events()),
        "row cannot be retried or resumed",
    )
    require(branch.envelope.runtime_hash == runner._runtime_hash(), "executing runtime changed")
    branch.journal.append(
        "uptake_execution_started",
        {
            "cell": branch.row["cell"],
            "synthetic": branch.provider_free,
            "harness_git_commit": git_commit(),
            "saved_sample_is_not_new_billing": True,
        },
    )
    budget = RowBudget(branch, group)
    original_record, original_count = runner._record_tool_batch, native_compaction.count_prepared
    original_boundary = segments.boundary_reason
    active = runner._run_one_active
    gate, seed_results, requests = {}, [], []
    expected_lines = public_expected(oracle_source)
    require(
        branch.package.public.repository.url.startswith("snapshot://") or expected_lines,
        "frozen public oracle expectation missing",
    )
    branch.selected_call_arguments = json.loads(
        checkpoint.read_bound(branch.row["public_response"])
    )["tool_calls"][0]["arguments"]

    def record(**kwargs):
        value = original_record(**kwargs)
        if kwargs["turn_id"] == branch.seed_turn_id:
            require(
                not seed_results and len(kwargs["results"]) == 1,
                "seed probe did not execute exactly once",
            )
            seed_results.extend(kwargs["results"])
            gate.update(exposure_gate(branch.row, seed_results[0], expected_lines))
            branch.journal.append("uptake_exposure_gate", gate)
            if not gate["exposed"]:
                raise BoundStop("UNEXPOSED: " + gate["reason"])
        return value

    def count(*args, **kwargs):
        budget.before_count()  # before the runtime writes an input_count_started event
        value = original_count(*args, **kwargs)
        if budget.generations == 0 and value[1] > 60000:
            # The frozen first exchange cannot be replaced by a smaller handoff.
            # The completed count is still charged against the six-count limit.
            raise BoundStop("first continuation exceeds the input-token bound")
        return value

    def boundary(journal, binding):
        # The frozen first continuation must deliver the saved reasoning/call/result.
        # Treat the imported exchange as pending delivery before a result handoff.
        # Once a new decision consumes it, the original boundary policy resumes.
        decision = next(
            (
                e["payload"]
                for e in reversed(journal.events())
                if e["event_type"] == "turn_decision_recorded"
            ),
            None,
        )
        if decision and decision["turn_id"] == branch.seed_turn_id:
            return None
        return original_boundary(journal, binding)

    def bounded_active(**kwargs):
        kwargs["deadline"] = ExecutionDeadline(
            min(kwargs["deadline"].expires_at, group.deadline.expires_at), group.clock
        )
        kwargs["harness_git_commit"] = git_commit()
        return active(**kwargs)

    class Adapter(OpenAIResponsesAdapter):
        def __init__(self, config, **kwargs):
            super().__init__(config, **kwargs, **({"client": client} if client else {}))

        def count_input_tokens_v2(self, request, **kwargs):
            require(gate.get("exposed") is True, "count before usable diagnosis")
            require(
                request["model"] == branch.selected["model"]
                and request["reasoning"] == branch.selected["reasoning"]
                and request["service_tier"] == branch.selected["service_tier"]
                and request["input"][-1] == branch.selected["input"][-1],
                "fixed continuation conditions changed",
            )
            if budget.generations == 0:
                verify_first_input(branch, request, seed_results[0])
            requests.append(copy.deepcopy(request))
            method = super().count_input_tokens_v2
            return budget.counted(request, lambda: method(request, **kwargs))

        def execute_request(self, request, **kwargs):
            budget.dispatch(request, kwargs["requested_input_tokens"])
            return super().execute_request(request, **kwargs)

    result, reason, stop_all = None, None, False
    try:
        with (
            inherited_reads(branch),
            exposure.current_probe_receipts(branch),
            checkpoint.instruction_slot(branch.selected["input"][-1]),
            patch.object(runner, "_record_tool_batch", record),
            patch.object(native_compaction, "count_prepared", count),
            patch.object(segments, "boundary_reason", boundary),
            patch.object(runner, "_run_one_active", bounded_active),
            patch.object(runner, "OpenAIResponsesAdapter", Adapter),
            submitted_assessment(branch, group, oracle_source),
            branch.journal.execution_lock(),
        ):
            result = runner._run_one_locked(
                request=branch.request,
                task_dir=branch.task_dir,
                package=branch.package,
                state_root=branch.root,
                pricing=branch.pricing,
                cost_ledger=budget,
                runtime_hash=branch.envelope.runtime_hash,
                model_hash=branch.envelope.model_hash,
                run_id=branch.journal.run_id,
                journal=branch.journal,
                envelope=branch.envelope,
                resuming=True,
            )
    except BoundStop as exc:
        reason, stop_all = exc.reason, exc.all_rows
    except Exception as exc:
        reason, stop_all = f"connector uncertainty: {type(exc).__name__}: {exc}", True
    known = (
        runner._provider_usage_failure(branch.journal) is None
        and branch.journal.unresolved_input_count() is None
    )
    if result:
        terminal = result.public["terminal"]
        stop_all |= terminal in {
            "PREFLIGHT_FAILED",
            "PROVIDER_CONTINUATION_ERROR",
            "EVALUATOR_ERROR",
            "TASK_FAILED",
        }
        stop_all |= result.stop_remaining and terminal != "COST_CAP_REACHED"
    stop_all |= not known or group.deadline.remaining_seconds() <= 0
    group.stopped |= stop_all
    final_diff = {"status": "NOT_SEALED", "reason": "invocation deadline exhausted"}
    if group.deadline.remaining_seconds() > 0:
        try:
            summary = WorkspaceManager.diff_summary(
                branch.workspace,
                deadline=ExecutionDeadline(
                    min(group.clock() + 5, group.deadline.expires_at), group.clock
                ),
            )
            artifact = branch.store.put_text(summary.patch, "text/x-diff")
            require(artifact.content_hash == summary.patch_hash, "final diff identity changed")
            final_diff = {
                "status": "SEALED",
                "artifact": artifact.model_dump(mode="json"),
                "submission": any(
                    e["event_type"] == "submission_recorded" for e in branch.journal.events()
                ),
            }
        except Exception as exc:
            final_diff = {"status": "NOT_SEALED", "reason": type(exc).__name__}
            stop_all = group.stopped = True
    branch.journal.append("uptake_terminal_diff", final_diff)
    new_events = branch.journal.events()[branch.inherited_events :]
    receipt = {
        "cell": branch.row["cell"],
        "synthetic": branch.provider_free,
        "result": result.public if result else None,
        "stop_reason": reason,
        "exposure": gate or {"exposed": False, "reason": "seed not completed"},
        "new_counts": budget.counts,
        "new_generations": budget.generations,
        "new_tool_actions": runner._restore_counters(branch.journal).tool_actions
        - branch.parent_actions,
        "provisional_cost_nanos": budget.spent_nanos - branch.initial_spent_nanos
        if known
        else None,
        "billing_known": known,
        "final_diff": final_diff,
        "stop_remaining": stop_all,
        "provider_calls": 0 if branch.provider_free else budget.counts + budget.generations,
        "billed_cost_nanos": 0 if branch.provider_free else None,
        "first_request_hash": sha256_json(requests[0]) if requests else None,
        "first_input_verified": bool(requests and budget.counts),
        "accepted_new_edits": sum(
            e["event_type"] == "action_finished"
            and e["payload"]["result"]["tool"] == "replace_text"
            and e["payload"]["result"]["status"] == "succeeded"
            and not e["payload"]["result"].get("error_code")
            for e in new_events
        ),
        "uptake": "NOT_RUN" if branch.provider_free else "PENDING_PUBLIC_TRACE_REVIEW",
        "repair": "NOT_RUN" if branch.provider_free else "PENDING_PUBLIC_TRACE_REVIEW",
        "public_review_artifact": next(
            (
                e["payload"]["artifact"]
                for e in new_events
                if e["event_type"] == "uptake_public_review_packet"
            ),
            None,
        ),
    }
    branch.journal.append("uptake_row_finished", receipt)
    group.journal.append("uptake_row_finished", receipt)
    return receipt


def run_roster(rows, group, prepare, execute):
    """Preserve both denominators; ordinary settled row failure does not censor B2."""
    require([r["cell"] for r in rows] == ["B1", "B2"], "fixed B1/B2 roster required")
    results = []
    for row in rows:
        if group.stopped:
            receipt = {"cell": row["cell"], "status": "NOT_RUN", "reason": "prior global stop"}
            group.journal.append("uptake_row_not_run", receipt)
            results.append(receipt)
            continue
        try:
            group.check()
            branch = prepare(row)
            receipt = execute(branch)
        except BoundStop as exc:
            group.stopped |= exc.all_rows
            receipt = {
                "cell": row["cell"],
                "status": "STOPPED",
                "reason": exc.reason,
                "stop_remaining": exc.all_rows,
            }
            group.journal.append("uptake_row_preparation_stopped", receipt)
        except Exception as exc:
            group.stopped = True
            receipt = {
                "cell": row["cell"],
                "status": "ERROR",
                "stop_remaining": True,
                "reason": f"preparation uncertainty: {type(exc).__name__}: {exc}",
            }
            group.journal.append("uptake_row_preparation_stopped", receipt)
        group.stopped |= receipt.get("stop_remaining", False)
        results.append(receipt)
    return results


def synthetic_observation(row, *, disconfirm=True, expected_lines=None):
    """Explicit test data, not a replay of an executed B probe."""
    target = "     my_id," if disconfirm else "        my_id,"
    data = (
        {"cte_line": target, "yaml_lines": ["SYNTHETIC"]}
        if row["cell"] == "B1"
        else {"cte_target_line": target, "cte_leading_spaces": len(target) - len(target.lstrip())}
    )
    lines = ["SYNTHETIC_ONLY_NO_TASK_EXECUTION"]
    if row["cell"] == "B2":
        cte_lines = list(expected_lines or ["WITH example AS (", "    SELECT", target])
        cte_lines[2] = target
        lines.append(repr({"cte_lines": cte_lines}))
    lines.append(repr(data))
    labels = ["current_class"] if row["cell"] == "B1" else ["rule_name", "patched_name"]
    return {
        "stdout": "\n".join(lines) + "\n",
        "stderr": "AssertionError: synthetic ancillary",
        "truncated": False,
        "setup_checks": {
            "status": "passed",
            "checks": [{"label": label, "matched": True} for label in labels],
        },
    }


@contextmanager
def offline_environment(branch, client, observation, *, fixture_evaluation=False):
    require(isinstance(client, ScriptedClient), "finite offline client required")
    fixture = branch.package.public.repository.url.startswith("snapshot://")
    for batch in client.steps:
        for call in batch:
            require(
                fixture
                or call["name"]
                not in {"replace_text", "run_check", "finish_task", "run_tests", "run_probe"},
                "remote-task execution is outside a provider-free rehearsal",
            )
    probes = []
    original_probe = runner.DockerProbeSandbox

    class Probe(exposure.SyntheticProbe):
        def __init__(self, **kwargs):
            super().__init__(
                branch.envelope,
                {branch.row["action_id"]: "failed", "uptake_final_public_oracle": "passed"},
                **kwargs,
            )
            probes.append(self)
            # Dependency-aware profile, read without Docker/preflight/network.
            self.profile = original_probe(**kwargs).current_profile()
            require(
                sha256_json(self.profile) == branch.envelope.probe_profile_hash,
                "synthetic probe would mask a profile mismatch",
            )

        def run_probe(self, *args, **kwargs):
            output = super().run_probe(*args, **kwargs)
            policy = exposure.probe_execution_policy(
                effective_timeout_seconds=30,
                row_deadline_limited=False,
                cleanup_status="confirmed",
                profile=self.profile,
            )
            output.update(execution_policy=policy, execution_policy_hash=sha256_json(policy))
            if kwargs["execution_identity"]["action_id"] == branch.row["action_id"]:
                output.update(copy.deepcopy(observation))
            return output

    def forbidden(*args, **kwargs):
        raise ContractError("network forbidden in uptake rehearsal")

    original_manifest = runner._manifest

    def manifest(**kwargs):
        require(fixture and fixture_evaluation, "real-task evaluation forbidden in rehearsal")
        kwargs["sandbox_backend"] = "local"
        value = original_manifest(**kwargs)
        identity = runner._sandbox_identity_hash(
            kwargs["request"].model_copy(update={"provider": "mock"}),
            kwargs["package"],
            kwargs.get("probe_dependencies"),
        )
        return value.model_copy(update={"sandbox_identity_hash": identity})

    with (
        patch("socket.socket.connect", forbidden),
        patch("socket.create_connection", forbidden),
        patch.object(runner, "load_exact_openai_api_key", lambda _: "offline-unused"),
        patch.object(runner, "_live_source_preflight", lambda *a, **k: None),
        patch.object(runner, "_live_sandbox_preflight", lambda *a, **k: LocalSandbox()),
        patch.object(runner, "DockerProbeSandbox", Probe),
        patch.object(runner, "_manifest", manifest),
    ):
        yield probes


def rehearse(output):
    started = monotonic()
    plan, source, selected = checkpoint.load_design()
    output = output.resolve()
    exposure.disjoint(output, (repository_root(), source.root, checkpoint.DESIGN.parent))
    output.mkdir()  # unique evidence root; never overwrite/retry a row
    journal, store = DevJournal(output, "run_dev_uptakebridge"), ArtifactStore(output)
    group = Invocation(journal, started=started)
    journal.append(
        "uptake_mock_started",
        {
            "design_hash": checkpoint.DESIGN_HASH,
            "diagnostic_implementation_hash": exposure.implementation_hash(),
            "paid_authorized": False,
        },
    )

    def prepare(row):
        saved, usage = checkpoint.saved_turn(row, selected)
        return checkpoint.restore_branch(
            source,
            plan["inheritance"]["prepared_cut_sequence"],
            selected,
            saved,
            usage,
            row,
            output / row["cell"],
        )

    def execute(branch):
        oracle = checkpoint.read_bound(plan["terminal_public_oracle"]).decode()
        steps = [
            [
                {
                    "name": "read_file",
                    "action_id": "synthetic_read",
                    "arguments": {
                        "path": "src/sqlfluff/rules/L036.py",
                        "start_line": 1,
                        "end_line": 80,
                        "memory_update": None,
                    },
                }
            ],
            [
                {
                    "name": "stop_task",
                    "action_id": "synthetic_stop",
                    "arguments": {
                        "reason_code": "insufficient_public_evidence",
                        "summary": "Synthetic connector verification only.",
                        "memory_update": None,
                    },
                }
            ],
        ]
        client = ScriptedClient(steps)
        with offline_environment(
            branch,
            client,
            synthetic_observation(branch.row, expected_lines=public_expected(oracle)),
        ):
            return run_row(
                branch,
                group,
                oracle,
                client=client,
            )

    rows = run_roster(plan["rows"], group, prepare, execute)
    checkpoint.load_design()  # frozen inputs/history/runtime still byte-identical
    result = {
        "official": False,
        "provider_free": True,
        "design_hash": checkpoint.DESIGN_HASH,
        "rows": rows,
        "provider_calls": 0,
        "credential_reads": 0,
        "metadata_calls": 0,
        "billed_cost_nanos": 0,
        "actual_sqlfluff_probes": 0,
        "actual_task_acceptance": "NOT_RUN",
        "model_uptake": "NOT_RUN",
        "paid_authorized": False,
        "provisional_synthetic_cost_nanos": group.ledger.spent_nanos,
    }
    ref = store.put_json(result)
    journal.append("uptake_mock_finished", {"result": ref.model_dump(mode="json")})
    (output / "result.json").write_text(canonical_json(result) + "\n", encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    print(canonical_json(rehearse(args.output)))


if __name__ == "__main__":
    main()
