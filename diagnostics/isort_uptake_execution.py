"""Single-use isort continuation; the CLI is strictly provider-free.

Only the first public state receives the already executed operator packet.
Registered runtime tools retain their normal restrictions. Public U review is
sealed before either terminal assessment; no assessment can start another turn.
"""

from __future__ import annotations

import argparse
import copy
import json
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path
from time import monotonic, sleep
from unittest.mock import patch

from diagnostics import isort_uptake_checkpoint as checkpoint
from diagnostics import observation_exposure as exposure
from diagnostics import uptake_execution as shared
from diagnostics.checkpoint_continuation import ScriptedClient, inherited_reads
from diagnostics.decision_sampler import require
from patchloop.agent.model import OpenAIResponsesAdapter
from patchloop.artifacts import ArtifactStore
from patchloop.deadline import ExecutionDeadline
from patchloop.dev import native_compaction, runner, segments
from patchloop.dev.conversation import history_metadata, reconstruct_state, validate_model_input
from patchloop.dev.cost import DevCostLedger, pricing_for_model
from patchloop.dev.state import DevJournal
from patchloop.repository import WorkspaceManager
from patchloop.runtime import git_commit, repository_root
from patchloop.util import canonical_json, sha256_bytes, sha256_json

BoundStop = shared.BoundStop


class Invocation(shared.Invocation):
    def __init__(self, journal, *, clock=monotonic, started=None):
        self.journal, self.clock = journal, clock
        self.started = clock() if started is None else started
        self.deadline = ExecutionDeadline(self.started + 720, clock)
        self.counts = self.generations = 0
        self.ledger = DevCostLedger(Decimal("3.50"), pricing_for_model("gpt-5.4-2026-03-05"))
        self.stopped = False


class RowBudget(shared.RowBudget):
    def before_count(self):
        self.group.check()
        if self.group.counts >= 6 or self.group.generations >= 6:
            raise BoundStop("invocation call cap")
        super().before_count()

    def dispatch(self, request, requested_input_tokens):
        if self.group.generations >= 6:
            raise BoundStop("invocation generation cap")
        # Six completed counts do not forbid dispatch of the sixth matching request.
        super().dispatch(request, requested_input_tokens)


def add_feedback(items, feedback):
    items = copy.deepcopy(items)
    view = json.loads(items[-1]["content"])
    require(view["kind"] == "harness_current_state", "missing current public state")
    require(checkpoint.FIELD not in view["state"], "operator packet already present")
    view["state"][checkpoint.FIELD] = copy.deepcopy(feedback)
    items[-1]["content"] = canonical_json(view)
    validate_model_input(
        items, history_metadata(items, context_policy="segmented-v1"), context_policy="segmented-v1"
    )
    return items


def verify_first_input(branch, request):
    def native(items):
        return [
            i
            for i in items
            if i.get("type") in {"reasoning", "function_call", "function_call_output"}
        ]

    require(
        native(request["input"]) == native(branch.selected["input"]),
        "first input lost or fabricated native continuation",
    )
    state = reconstruct_state(request["input"], context_policy="segmented-v1")
    require(
        state[checkpoint.FIELD] == branch.feedback, "first input lacks complete operator packet"
    )
    checkpoint.verify_feedback(branch.feedback, branch)


def seal_review(branch, group, reviewer):
    """The callback performs semantic public-trace grading, never patch-only inference."""
    require(not hasattr(branch, "public_review"), "public review cannot be repeated")
    group.check()
    summary = WorkspaceManager.diff_summary(branch.workspace, deadline=group.deadline)
    public_types = {
        "action_started",
        "action_finished",
        "turn_decision_recorded",
        "working_notes_updated",
        "working_plan_updated",
    }
    events = [
        {
            "sequence": e["sequence"],
            "event_type": e["event_type"],
            "payload": {k: v for k, v in e["payload"].items() if k != "continuation_ref"},
        }
        for e in branch.journal.events()
        if e["event_type"] in public_types
    ]
    review = {
        "public_task": branch.package.public.model_dump(mode="json"),
        "operator_observation": branch.feedback,
        "public_events": events,
        "new_events_after": branch.inherited_events,
        "final_patch": summary.patch,
        "patch_hash": summary.patch_hash,
        "submitted": any(e["event_type"] == "submission_recorded" for e in branch.journal.events()),
        "terminal_assessments_present": False,
        "synthetic_transport": branch.provider_free,
    }
    ref = branch.store.put_json(review)
    branch.journal.append("isort_uptake_public_review", {"artifact": ref.model_dump(mode="json")})
    grade = reviewer(ref, review, group.deadline)
    group.check()
    require(grade["review_hash"] == ref.content_hash, "U review binding changed")
    require(
        grade["U"] in {"PASS", "FAIL", "NOT_OBSERVABLE"} and grade["reason"],
        "semantic public U grade required",
    )
    by_sequence = {e["sequence"]: e for e in events}
    citations = grade["public_event_sequences"]
    require(set(citations) <= by_sequence.keys(), "U citation is not a public event")
    if grade["U"] == "PASS":
        require(
            grade["observation_case_ids"]
            and set(grade["observation_case_ids"])
            <= {c["case_id"] for c in branch.feedback["cases"]},
            "U PASS needs specific public observation citations",
        )
        edits = [
            by_sequence[s]
            for s in citations
            if s > branch.inherited_events
            and by_sequence[s]["event_type"] == "action_finished"
            and checkpoint.accepted_edits([by_sequence[s]])
        ]
        explanations = [
            by_sequence[s]
            for s in citations
            if by_sequence[s]["event_type"]
            in {"action_started", "turn_decision_recorded", "working_notes_updated"}
        ]
        require(
            edits
            and explanations
            and min(e["sequence"] for e in explanations) <= max(e["sequence"] for e in edits),
            "U PASS lacks explanation/accepted-edit linkage",
        )
    elif grade["U"] == "FAIL":
        require(citations, "U FAIL requires public evidence, not a resource cutoff")
    branch.public_review, branch.u_grade = ref, grade
    branch.journal.append("isort_uptake_U_sealed", grade)
    return grade


def file_reviewer(directory):
    """Wait for one operator semantic grade in the same bounded invocation.

    No paid judge, resume, new model turn or automatic semantic classifier. The
    ready file binds the public packet; the grade must be atomically published.
    """

    def review(ref, packet, deadline):
        ready, grade = directory / "public-review-ready.json", directory / "public-grade.json"
        require(not ready.exists() and not grade.exists(), "public review already used")
        with ready.open("x", encoding="utf-8") as stream:
            stream.write(
                canonical_json(
                    {
                        "artifact": ref.model_dump(mode="json"),
                        "deadline_monotonic": deadline.expires_at,
                    }
                )
                + "\n"
            )
        while not grade.exists():
            if deadline.remaining_seconds() <= 0:
                raise BoundStop("public U review exceeded invocation time", all_rows=True)
            sleep(min(0.2, deadline.remaining_seconds()))
        return json.loads(grade.read_bytes())

    return review


def oracle_grade(receipt):
    """Exit zero alone is not the frozen program's behavioral verdict."""
    if any(
        receipt.get(k) for k in ("cleanup_failed", "deadline_exhausted", "timed_out", "truncated")
    ):
        return "ERROR"
    if receipt.get("setup_checks", {}).get("status") != "passed":
        return "ERROR"
    if receipt.get("exit_code") != 0 or receipt.get("status") != "passed":
        return "ERROR"
    try:
        rows = [json.loads(line) for line in receipt["stdout"].splitlines()]
        cases = rows[:-1]
        if (
            len(cases) != 4
            or {r["case_id"] for r in cases}
            != {"type_opening", "type_item", "plain_opening", "plain_item"}
            or rows[-1]
            != {"stage": "complete", "cases": 4, "all_passed": all(r["passed"] for r in cases)}
        ):
            return "ERROR"
        return "PASS" if rows[-1]["all_passed"] else "FAIL"
    except (KeyError, TypeError, ValueError):
        return "ERROR"


@contextmanager
def submitted_assessment(branch, group, oracle_source, reviewer):
    evaluate = runner.EvaluationEngine.evaluate
    used = []

    def assess(engine, task_dir, patch_path, manifest, **kwargs):
        require(not used, "one submitted assessment only")
        used.append(True)
        group.check()
        submitted = kwargs["submitted_patch_artifact"]
        require(
            sha256_bytes(Path(patch_path).read_bytes())
            == submitted.content_hash
            == WorkspaceManager.diff_summary(branch.workspace, deadline=group.deadline).patch_hash,
            "submitted diff and terminal candidate differ",
        )
        try:
            seal_review(branch, group, reviewer)
        except Exception as exc:
            raise BoundStop(
                f"public U review uncertainty: {type(exc).__name__}: {exc}", all_rows=True
            ) from exc
        new_events = branch.journal.events()[branch.inherited_events :]
        checks = {}
        for event in new_events:
            if event["event_type"] == "action_finished":
                action = event["payload"]["result"]
                if action["tool"] == "run_check" and action["status"] == "succeeded":
                    checks[action["output"].get("check_id")] = action["output"]
        fresh_regression = all(
            checks.get(check.id, {}).get("passed") is True
            and checks[check.id].get("diff_hash") == submitted.content_hash
            for check in branch.package.public.visible_checks
        )
        new_change = (
            checkpoint.accepted_edits(new_events) > 0
            and submitted.content_hash != branch.feedback["observed_on_current_diff_hash"]
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
        deadline = ExecutionDeadline(
            min(group.deadline.expires_at, group.clock() + 30), group.clock
        )
        require(
            probe.preflight(deadline=deadline)
            == {
                "image_digest": branch.envelope.probe_image_digest,
                "profile_hash": branch.envelope.probe_profile_hash,
            },
            "terminal probe identity changed",
        )
        receipt = probe.run_probe(
            branch.workspace,
            "Frozen public comment-position expectation on submitted diff.",
            oracle_source,
            deadline=deadline,
            execution_identity={
                "run_id": branch.journal.run_id,
                "action_id": "uptake_final_public_oracle",
                "input_hash": submitted.content_hash,
            },
        )
        require(
            receipt.get("source_hash") == sha256_bytes(oracle_source.encode())
            and receipt.get("image_digest") == branch.envelope.probe_image_digest
            and receipt.get("profile_hash") == branch.envelope.probe_profile_hash,
            "terminal oracle receipt identity changed",
        )
        require(
            WorkspaceManager.diff_summary(branch.workspace, deadline=group.deadline).patch_hash
            == submitted.content_hash,
            "terminal public oracle mutated submitted candidate",
        )
        verdict = oracle_grade(receipt)
        branch.public_repair = (
            "ERROR"
            if verdict == "ERROR"
            else "PASS"
            if verdict == "PASS" and new_change and fresh_regression
            else "FAIL"
        )
        branch.journal.append(
            "isort_uptake_terminal_oracle",
            {
                "patch_hash": submitted.content_hash,
                "receipt": receipt,
                "public_behavior": verdict,
                "new_accepted_source_change": new_change,
                "fresh_final_diff_regression": fresh_regression,
                "P": branch.public_repair,
                "solver_feedback": False,
            },
        )
        if verdict == "ERROR":
            raise BoundStop(
                "terminal oracle infrastructure/setup/receipt uncertainty", all_rows=True
            )
        group.check()
        kwargs["deadline"] = ExecutionDeadline(
            min(group.clock() + 330, group.deadline.expires_at), group.clock
        )
        return evaluate(engine, task_dir, patch_path, manifest, **kwargs)

    with patch.object(runner.EvaluationEngine, "evaluate", assess):
        yield


def run_row(branch, group, oracle_source, *, reviewer, client=None):
    require(
        branch.provider_free == isinstance(client, ScriptedClient),
        "finite offline transport required",
    )
    require(
        not any(
            e["event_type"] == "isort_uptake_execution_started" for e in branch.journal.events()
        ),
        "row cannot be retried or resumed",
    )
    require(branch.envelope.runtime_hash == runner._runtime_hash(), "executing runtime changed")
    branch.journal.append(
        "isort_uptake_execution_started",
        {
            "row": "I1",
            "synthetic": branch.provider_free,
            "harness_git_commit": git_commit(),
        },
    )
    budget = RowBudget(branch, group)
    build, count, active, boundary = (
        runner._build_model_input,
        native_compaction.count_prepared,
        runner._run_one_active,
        segments.boundary_reason,
    )
    requests, dispatched = [], []

    def assemble(**kwargs):
        items = build(**kwargs)
        return add_feedback(items, branch.feedback) if not budget.generations else items

    def bounded_count(*args, **kwargs):
        budget.before_count()
        value = count(*args, **kwargs)
        if not budget.generations and value[1] > 60000:
            raise BoundStop("first continuation exceeds input-token bound")
        return value

    def bounded_active(**kwargs):
        kwargs["deadline"] = ExecutionDeadline(
            min(
                kwargs["deadline"].expires_at,
                branch.solver_deadline.expires_at,
                group.deadline.expires_at,
            ),
            group.clock,
        )
        kwargs["harness_git_commit"] = git_commit()
        return active(**kwargs)

    class Adapter(OpenAIResponsesAdapter):
        def __init__(self, config, **kwargs):
            super().__init__(config, **kwargs, **({"client": client} if client else {}))

        def count_input_tokens_v2(self, request, **kwargs):
            require(
                all(
                    request[k] == branch.selected[k]
                    for k in ("model", "reasoning", "service_tier", "max_output_tokens")
                ),
                "fixed continuation configuration changed",
            )
            if not budget.generations:
                verify_first_input(branch, request)
            requests.append(copy.deepcopy(request))
            method = super().count_input_tokens_v2
            return budget.counted(request, lambda: method(request, **kwargs))

        def execute_request(self, request, **kwargs):
            budget.dispatch(request, kwargs["requested_input_tokens"])
            if not dispatched:
                verify_first_input(branch, request)
                branch.journal.append(
                    "isort_uptake_first_dispatch_input",
                    {
                        "request_hash": sha256_json(request),
                        "synthetic": branch.provider_free,
                        "feedback_hash": sha256_json(branch.feedback),
                        "model_authored": False,
                    },
                )
            dispatched.append(sha256_json(request))
            return super().execute_request(request, **kwargs)

    result, reason, uncertain = None, None, False
    try:
        group.check()
        with (
            inherited_reads(branch),
            exposure.current_probe_receipts(branch),
            patch.object(runner, "_build_model_input", assemble),
            patch.object(native_compaction, "count_prepared", bounded_count),
            patch.object(
                segments,
                "boundary_reason",
                lambda *a, **k: boundary(*a, **k) if budget.generations else None,
            ),
            patch.object(runner, "_run_one_active", bounded_active),
            patch.object(runner, "OpenAIResponsesAdapter", Adapter),
            submitted_assessment(branch, group, oracle_source, reviewer),
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
        reason, uncertain = exc.reason, exc.all_rows
    except Exception as exc:
        reason, uncertain = f"connector uncertainty: {type(exc).__name__}: {exc}", True
    known = (
        runner._provider_usage_failure(branch.journal) is None
        and branch.journal.unresolved_input_count() is None
    )
    uncertain |= not known or group.deadline.remaining_seconds() <= 0
    if result:
        uncertain |= result.stop_remaining or result.public["terminal"] in {
            "PREFLIGHT_FAILED",
            "PROVIDER_CONTINUATION_ERROR",
            "EVALUATOR_ERROR",
            "TASK_FAILED",
        }
    if not uncertain and not hasattr(branch, "public_review"):
        try:
            seal_review(branch, group, reviewer)
        except (Exception, BoundStop) as exc:
            reason, uncertain = f"public review stopped: {type(exc).__name__}: {exc}", True
    group.stopped |= uncertain
    events = branch.journal.events()[branch.inherited_events :]
    receipt = {
        "row": "I1",
        "synthetic": branch.provider_free,
        "result": result.public if result else None,
        "stop_reason": reason,
        "new_counts": budget.counts,
        "new_generations": budget.generations,
        "new_tool_actions": runner._restore_counters(branch.journal).tool_actions
        - branch.parent_actions,
        "accepted_new_edits": checkpoint.accepted_edits(events),
        "billing_known": known,
        "stop_remaining": uncertain,
        "provisional_cost_nanos": budget.spent_nanos - branch.initial_spent_nanos
        if known
        else None,
        "provider_calls": 0 if branch.provider_free else budget.counts + budget.generations,
        "billed_cost_nanos": 0 if branch.provider_free else None,
        "first_input_verified": bool(dispatched),
        "D": "NOT_RUN"
        if branch.provider_free
        else ("PASS" if dispatched and known else "UNKNOWN" if dispatched else "UNEXPOSED"),
        "first_request_hash": dispatched[0] if dispatched else None,
        "U": branch.u_grade["U"] if hasattr(branch, "u_grade") else "NOT_RUN",
        "model_uptake": "NOT_RUN" if branch.provider_free else "SEE_PUBLIC_U_GRADE",
        "public_repair": getattr(branch, "public_repair", "NOT_RUN"),
        "public_review": branch.public_review.model_dump(mode="json")
        if hasattr(branch, "public_review")
        else None,
    }
    branch.journal.append("isort_uptake_row_finished", receipt)
    group.journal.append("isort_uptake_row_finished", receipt)
    return receipt


@contextmanager
def offline_environment(branch, client, *, fixture_evaluation=False, oracle_pass=True):
    # Reuse the existing network/key/real-task guards, only synthesize the new oracle format.
    branch.row["action_id"] = "isort_seed_must_never_execute"
    with shared.offline_environment(
        branch, client, {}, fixture_evaluation=fixture_evaluation
    ) as probes:
        probe_type = runner.DockerProbeSandbox
        original = probe_type.run_probe

        def run(probe, *args, **kwargs):
            require(
                kwargs["execution_identity"]["action_id"] == "uptake_final_public_oracle",
                "no seed or model probe execution in this rehearsal",
            )
            receipt = original(probe, *args, **kwargs)
            rows = [
                {"case_id": case, "passed": oracle_pass}
                for case in ("type_opening", "type_item", "plain_opening", "plain_item")
            ]
            receipt.update(
                stdout="\n".join(
                    json.dumps(r)
                    for r in [
                        *rows,
                        {
                            "stage": "complete",
                            "cases": 4,
                            "all_passed": oracle_pass,
                        },
                    ]
                ),
                setup_checks={"status": "passed"},
            )
            return receipt

        with patch.object(probe_type, "run_probe", run):
            yield probes


def inert_reviewer(ref, packet, deadline):
    return {
        "review_hash": ref.content_hash,
        "U": "NOT_OBSERVABLE",
        "reason": "Inert scripted transport; no model-uptake evidence.",
        "public_event_sequences": [],
        "observation_case_ids": [],
    }


def rehearse(output):
    started = monotonic()
    plan, source, feedback = checkpoint.load_design()
    output = output.resolve()
    exposure.disjoint(output, (repository_root(), source.root, checkpoint.DESIGN.parent))
    output.mkdir()
    journal, store = DevJournal(output, "run_dev_isortbridge"), ArtifactStore(output)
    group = Invocation(journal, started=started)
    journal.append(
        "isort_uptake_mock_started",
        {
            "design_hash": checkpoint.DESIGN_HASH,
            "diagnostic_implementation_hash": exposure.implementation_hash(),
            "runtime_hash": runner._runtime_hash(),
            "harness_git_commit": git_commit(),
        },
    )
    branch = checkpoint.restore_branch(
        source,
        plan["inheritance"]["prepared_cut_sequence"],
        feedback,
        output / "I1",
        started=started,
        deadline=group.deadline,
    )
    client = ScriptedClient(
        [
            [
                {
                    "name": "read_file",
                    "action_id": "synthetic_read",
                    "arguments": {
                        "path": "isort/parse.py",
                        "start_line": 1,
                        "end_line": 60,
                        "turn_decision": {
                            "mode": "inspect",
                            "basis": "Synthetic connector verification.",
                            "evidence_goal": "Read restored public source.",
                            "memory_update": None,
                            "plan_update": None,
                        },
                    },
                }
            ],
            [
                {
                    "name": "stop_task",
                    "action_id": "synthetic_stop",
                    "arguments": {
                        "reason_code": "insufficient_public_evidence",
                        "summary": "Provider-free connector rehearsal only.",
                        "turn_decision": {
                            "mode": "stop",
                            "basis": "Synthetic connector verification complete.",
                            "evidence_goal": None,
                            "memory_update": None,
                            "plan_update": None,
                        },
                    },
                }
            ],
        ]
    )
    with offline_environment(branch, client):
        row = run_row(
            branch,
            group,
            checkpoint.read_bound(plan["terminal_public_oracle"]).decode(),
            reviewer=inert_reviewer,
            client=client,
        )
    checkpoint.load_design()
    result = {
        "official": False,
        "provider_free": True,
        "paid_authorized": False,
        "design_hash": checkpoint.DESIGN_HASH,
        "row": row,
        "provider_calls": 0,
        "credential_reads": 0,
        "metadata_calls": 0,
        "billed_cost_nanos": 0,
        "actual_isort_probes": 0,
        "actual_isort_checks": 0,
        "actual_isort_acceptance": "NOT_RUN",
        "model_uptake": "NOT_RUN",
    }
    ref = store.put_json(result)
    journal.append("isort_uptake_mock_finished", {"result": ref.model_dump(mode="json")})
    with (output / "result.json").open("x", encoding="utf-8") as stream:
        stream.write(canonical_json(result) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    print(canonical_json(rehearse(parser.parse_args().output)))


if __name__ == "__main__":
    main()
