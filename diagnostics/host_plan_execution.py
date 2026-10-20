"""Fixed O1 A/B continuation. CLI runs finite synthetic transport only."""

from __future__ import annotations

import copy
import json
from decimal import Decimal
from time import monotonic
from types import SimpleNamespace
from unittest.mock import patch

from diagnostics import host_plan_checkpoint as checkpoint
from diagnostics import observation_exposure as exposure
from diagnostics import uptake_execution as shared
from diagnostics.checkpoint_continuation import ScriptedClient, inherited_reads
from diagnostics.decision_sampler import require
from patchloop.agent.model import OpenAIResponsesAdapter
from patchloop.deadline import ExecutionDeadline, ExecutionDeadlineExceeded
from patchloop.dev import native_compaction, runner, segments
from patchloop.dev.conversation import CONVERSATION_INSTRUCTIONS
from patchloop.dev.cost import DevCostLedger, pricing_for_model
from patchloop.runtime import git_commit
from patchloop.util import canonical_json, sha256_json

BoundStop = shared.BoundStop


class Invocation(shared.Invocation):
    def __init__(self, journal, *, clock=monotonic, started=None):
        self.journal, self.clock = journal, clock
        self.started = clock() if started is None else started
        self.deadline = ExecutionDeadline(self.started + 4800, clock)
        self.counts = self.generations = 0
        self.ledger = DevCostLedger(Decimal("11.00"), pricing_for_model("gpt-5.4-2026-03-05"))
        self.stopped = False
        self.first_request = None


class RowBudget(shared.RowBudget):
    def before_count(self):
        self.group.check()
        if self.group.counts >= 20 or self.group.generations >= 20:
            raise BoundStop("invocation call cap", all_rows=True)
        if self.counts >= 10 or self.generations >= 10:
            raise BoundStop("row call cap")

    def dispatch(self, request, requested_input_tokens):
        self.group.check()
        pending, self.pending = self.pending, None
        require(
            pending is not None and pending == (request, requested_input_tokens),
            "dispatch differs from fresh counted request",
        )
        require(
            request.get("max_output_tokens") == 25000
            and requested_input_tokens <= 60000
            and self.reservation is not None,
            "dispatch has no full-ceiling admission",
        )
        if self.group.generations >= 20:
            raise BoundStop("invocation generation cap", all_rows=True)
        if self.generations >= 10:
            raise BoundStop("row generation cap")
        self.generations += 1
        self.group.generations += 1


def phase_deadline(branch, group, seconds):
    group.check()
    return ExecutionDeadline(
        min(group.clock() + seconds, branch.row_deadline.expires_at, group.deadline.expires_at),
        group.clock,
    )


def verify_delivery(branch, request):
    record = branch.deliveries.get(sha256_json(request["input"]))
    require(record is not None, "request lacks verified assembly")
    ordinary = checkpoint.read_bound(record["ordinary"])
    recovered = checkpoint.untreated(request, branch.plan["systems"])["input"]
    require(recovered == json.loads(ordinary), "non-treatment input changed")
    return record


def run_row(branch, group, *, reviewer, client=None):
    from diagnostics import host_plan_review as review

    require(
        branch.provider_free == isinstance(client, ScriptedClient),
        "finite offline transport required",
    )
    require(
        not any(e["event_type"] == "host_plan_execution_started" for e in branch.journal.events()),
        "row cannot retry or resume",
    )
    require(branch.envelope.runtime_hash == runner._runtime_hash(), "executing runtime changed")
    branch.journal.append(
        "host_plan_execution_started",
        {
            "row": branch.row["cell"],
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
    context = runner._build_context
    validate_binding = segments.validate_input_binding
    suffix = "\n" + CONVERSATION_INSTRUCTIONS + "\n" + segments.INSTRUCTIONS
    system = branch.plan["systems"][branch.arm]
    require(system.endswith(suffix), "historical conversation instructions changed")

    def bounded_context(**kwargs):
        value = json.loads(context(**kwargs))
        value["remaining_budget"]["active_wall_time_seconds"] = min(
            value["remaining_budget"]["active_wall_time_seconds"],
            int(branch.solver_deadline.remaining_seconds()),
        )
        return canonical_json(value)

    def treatment_binding(items, metadata, store):
        # Existing historical segment bytes remain immutable. Validate its exact
        # prefix/native continuation after undoing only this experiment's prompt.
        base = segments.load_binding(metadata["binding"], store)["base"]
        if (
            items[0].get("content") == branch.plan["systems"]["B"]
            and base[0].get("content") == branch.plan["systems"]["A"]
        ):
            projected = checkpoint.untreated({"input": items}, branch.plan["systems"])["input"]
            previous = metadata["previous_input_artifact"]

            def read(ref):
                data = store.read_bytes(ref)  # Verify the original CAS bytes first.
                if previous is not None and ref.content_hash == previous["content_hash"]:
                    value = checkpoint.untreated(
                        {"input": json.loads(data)}, branch.plan["systems"]
                    )
                    return canonical_json(value["input"]).encode()
                return data

            return validate_binding(projected, metadata, SimpleNamespace(read_bytes=read))
        return validate_binding(items, metadata, store)

    def assemble(**kwargs):
        items = build(**kwargs)
        # The historical full prompt, not today's default, is the common baseline.
        ordinary = copy.deepcopy(items)
        ordinary[0] = {"role": "system", "content": branch.plan["systems"]["A"]}
        delivered = copy.deepcopy(ordinary)
        delivered[0]["content"] = branch.plan["systems"][branch.arm]
        branch.deliveries[sha256_json(delivered)] = {
            "ordinary": branch.store.put_json(ordinary).model_dump(mode="json"),
            "delivered": branch.store.put_json(delivered).model_dump(mode="json"),
            "current_runtime_ordinary": branch.store.put_json(items).model_dump(mode="json"),
            "parity": "PASS",
        }
        return delivered

    def bounded_count(*args, **kwargs):
        budget.before_count()
        result = count(*args, **kwargs)
        if result[1] > 60000:
            raise BoundStop("continuation exceeds input-token bound")
        return result

    def bounded_active(**kwargs):
        kwargs["deadline"] = ExecutionDeadline(
            min(
                kwargs["deadline"].expires_at,
                branch.solver_deadline.expires_at,
                branch.row_deadline.expires_at,
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
                "fixed model settings changed",
            )
            verify_delivery(branch, request)
            if not budget.generations:
                checkpoint.verify_first(branch, request)
                if hasattr(branch, "expected_first"):
                    checkpoint.first_parity(branch.expected_first, request, branch.plan["systems"])
                if group.first_request is not None:
                    branch.first_parity = checkpoint.first_parity(
                        group.first_request, request, branch.plan["systems"]
                    )
            tokens = budget.counted(
                request, lambda: super(Adapter, self).count_input_tokens_v2(request, **kwargs)
            )
            branch.journal.append(
                "host_plan_counted",
                {
                    "request_hash": sha256_json(request),
                    "tokens": tokens,
                    "synthetic": branch.provider_free,
                },
            )
            return tokens

        def execute_request(self, request, **kwargs):
            delivery = verify_delivery(branch, request)
            budget.dispatch(request, kwargs["requested_input_tokens"])
            if not branch.dispatched:
                checkpoint.verify_first(branch, request)
                if group.first_request is None:
                    group.first_request = copy.deepcopy(request)
                branch.first_parity = checkpoint.first_parity(
                    group.first_request, request, branch.plan["systems"]
                )
            record = {
                **delivery,
                "request": branch.store.put_json(request).model_dump(mode="json"),
                "request_hash": sha256_json(request),
                "generation": budget.generations,
                "synthetic": branch.provider_free,
            }
            branch.dispatched.append(record)
            branch.journal.append("host_plan_dispatched", record)
            return super().execute_request(request, **kwargs)

    result, reason, uncertain = None, None, False
    try:
        group.check()
        with (
            inherited_reads(branch),
            exposure.current_probe_receipts(branch),
            patch.object(runner.thin_policy, "system_prompt", lambda *a: system[: -len(suffix)]),
            patch.object(runner, "_build_context", bounded_context),
            patch.object(segments, "validate_input_binding", treatment_binding),
            patch.object(runner, "_build_model_input", assemble),
            patch.object(native_compaction, "count_prepared", bounded_count),
            patch.object(
                segments,
                "boundary_reason",
                lambda *a, **k: boundary(*a, **k) if budget.generations else None,
            ),
            patch.object(runner, "_run_one_active", bounded_active),
            patch.object(runner, "OpenAIResponsesAdapter", Adapter),
            review.submitted_assessment(branch, group, reviewer),
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
        uncertain |= result.stop_remaining and result.public["terminal"] != "COST_CAP_REACHED"
        uncertain |= result.public["terminal"] in {
            "PREFLIGHT_FAILED",
            "PROVIDER_CONTINUATION_ERROR",
            "EVALUATOR_ERROR",
            "TASK_FAILED",
        }
    if not uncertain and not hasattr(branch, "review_started"):
        try:
            review.seal_review(branch, group, reviewer)
        except ExecutionDeadlineExceeded:
            reason = "public review or row time cap"
            uncertain = group.deadline.remaining_seconds() <= 0
        except (Exception, BoundStop) as exc:
            reason, uncertain = f"public review stopped: {type(exc).__name__}: {exc}", True
    group.stopped |= uncertain
    events = branch.journal.events()[branch.inherited_events :]
    receipt = {
        "row": branch.row["cell"],
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
        "first_request": branch.store.put_json(branch.first_request).model_dump(mode="json")
        if hasattr(branch, "first_request")
        else None,
        "first_input_parity": getattr(branch, "first_parity", None),
        **{axis: getattr(branch, "grade", {}).get(axis, "NOT_RUN") for axis in ("E", "U", "R")},
        "P": getattr(branch, "public_repair", "NOT_RUN"),
        "terminal_public_executions": getattr(branch, "public_attempts", 0),
        "isolated_evaluation_executions": getattr(branch, "isolated_attempts", 0),
        "isolated_assessment": getattr(branch, "isolated_assessment", None),
        "public_review": branch.public_review.model_dump(mode="json")
        if hasattr(branch, "public_review")
        else None,
        "model_uptake": "NOT_RUN" if branch.provider_free else "SEE_PUBLIC_U_GRADE",
    }
    branch.journal.append("host_plan_row_finished", receipt)
    group.journal.append("host_plan_row_finished", receipt)
    return receipt


def run_roster(group, prepare, execute):
    rows = []
    for arm in ("A", "B"):
        if group.stopped:
            row = {"row": "O1-" + arm, "status": "NOT_RUN", "reason": "prior global stop"}
        else:
            before_counts = (group.counts, group.generations)
            try:
                group.check()
                row = execute(prepare(arm))
            except ExecutionDeadlineExceeded:
                group.stopped |= group.deadline.remaining_seconds() <= 0
                row = {
                    "row": "O1-" + arm,
                    "status": "STOPPED",
                    "reason": "preparation/row time cap",
                    "stop_remaining": group.stopped,
                    "billing_known": (group.counts, group.generations) == before_counts,
                }
            except BoundStop as exc:
                group.stopped |= exc.all_rows
                row = {
                    "row": "O1-" + arm,
                    "status": "STOPPED",
                    "reason": exc.reason,
                    "stop_remaining": exc.all_rows,
                }
            except Exception as exc:
                group.stopped = True
                row = {
                    "row": "O1-" + arm,
                    "status": "ERROR",
                    "reason": str(exc),
                    "stop_remaining": True,
                }
        group.stopped |= row.get("stop_remaining", False)
        rows.append(row)
        group.journal.append("host_plan_roster_row_closed", row)
    return rows
