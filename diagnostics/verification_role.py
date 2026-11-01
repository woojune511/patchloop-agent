"""One shared runner with a bounded same-context or independent verification phase.

Only ``assigned`` installs this diagnostic. Native streams are views of the one
immutable journal; actions, counters, costs and workspace never become per-agent.
"""
from __future__ import annotations

import copy
import json
from contextlib import contextmanager
from dataclasses import replace
from unittest.mock import patch

from diagnostics.positive_verification_panel import require
from patchloop.contracts import Artifact
from patchloop.dev import evidence_focus, history_evidence, runner, tools, working_plan
from patchloop.dev.contracts import FinishIntent
from patchloop.dev.conversation import reconstruct_state
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError, RecoveryError
from patchloop.util import canonical_json, sha256_json

PHASE_EVENT = "verification_phase_started"
REPORT_TOOL = "finish_verification"
LIMITS = {
    "initial": {"model_calls": 28, "tool_actions": 60, "edits": 3, "cost_nanos": 480_000_000},
    "verify": {"model_calls": 6, "tool_actions": 20, "edits": 0, "cost_nanos": 200_000_000},
    "final": {"model_calls": 6, "tool_actions": 20, "edits": 1, "cost_nanos": 200_000_000},
}
QUESTION = "Does this candidate satisfy the original public caller, inputs and environment?"
INSTRUCTION = (
    "This mandatory phase verifies the frozen current candidate without editing. Establish "
    "the original public caller, input, environment and expected behavior from public evidence. "
    "Separate helper/regression coverage from that requirement and investigate a relevant "
    "countercondition. Expected values and scope declarations are unverified interpretations. "
    "Use registered tools within the shared run budget. Return finish_verification with a "
    "concise public report of scope, caller/setup/input, expected versus observed behavior, "
    "remaining counterconditions and the next useful check or fix. Label source inference. "
    "You may report uncertainty; this report neither submits nor certifies the task."
)
_BASE_GATEWAY = tools.DevToolGateway
_BASE_POLICY = runner._tool_policy
_BASE_VALIDATE = tools.validate_tool_batch
_BASE_MODEL_HASH = runner._model_hash
_ACTIVE = False


def contract():
    return {"comparison": "verification-role-v1", "phases": copy.deepcopy(LIMITS),
            "instruction_hash": sha256_json(INSTRUCTION), "report_chars": 1500,
            "references": 2, "context": "existing-segments-per-native-stream",
            "return_evidence": "selected-public-exchanges-v1",
            "cost": "single-ledger-per-call-admission-with-phase-reservations",
            "carry": "unused-resources-to-final-only", "resume": False}


def phased_events(events):
    """Derive scope from durable boundaries without altering hashed event payloads."""
    phase, stream = "initial", "repair"
    for event in events:
        if event["event_type"] == PHASE_EVENT:
            phase, stream = event["payload"]["phase"], event["payload"]["stream"]
        yield event, phase, stream


class JournalView(DevJournal):
    """A read projection only. Every write is appended to the original hash chain."""

    def __init__(self, parent, owner, *, stream=False):
        self.__dict__.update(parent.__dict__)
        self.parent, self.owner, self.stream = parent, owner, stream

    def events(self):
        return [e for e, phase, stream in phased_events(self.parent.events())
                if (not self.stream or stream == self.owner.stream)
                and (e["event_type"] not in {working_plan.EVENT, "attempt_card"}
                     or phase == self.owner.phase)
                # A counted, undispatched request from an earlier phase is not
                # reusable after the phase instruction/tool surface changes.
                and (e["event_type"] != "model_input_prepared" or phase == self.owner.phase)]

    def append(self, event_type, payload=None):
        return self.parent.append(event_type, payload)


def observed_result(value):
    """Remove owned interpretive envelopes, never keys inside observed JSON/source."""
    result = copy.deepcopy(value)
    for key in ("memory_update_result", "plan_update_result", "working_notes_after_batch"):
        result.pop(key, None)
    output = result.get("output", {})
    for key in ("inspection_intent", "inspection_intent_ref", "plan_review"):
        output.pop(key, None)
    mutation = output.get("mutation")
    if isinstance(mutation, dict):
        for key in history_evidence.MUTATION_ANNOTATIONS:
            mutation.pop(key, None)
    return result


class ObservationHistory(history_evidence.EvidenceHistory):
    """Exact-ID pages use the same observation mask as keyword search."""

    def __init__(self, owner):
        super().__init__()
        self.owner = owner

    def search(self, query, *, current_diff_hash, offset=None):
        if self.owner.phase != "verify":
            return super().search(query, current_diff_hash=current_diff_hash, offset=offset)
        index = history_evidence.EvidenceHistory()
        aliases = {}
        for identifier, record in self.records.items():
            if record["kind"] == "public_tool_exchange":
                body = history_evidence.separate(record["body"])["observed"]
                body["result"] = observed_result(body["result"])
            elif record["kind"] == "supplied_public_observation":
                # SnapshotRules already excludes mutable plans, notes and phase
                # state. Preserve actual public supplied inputs/observations.
                body = record["body"]
            else:
                continue
            aliases[identifier] = index._add(
                record["kind"], body,
                {**record["origin"], "original_record_id": identifier},
                record["observed_diff_hash"],
            )
        result = index.search(aliases.get(query, query), current_diff_hash=current_diff_hash,
                              offset=offset)
        result["projection"] = "observations-only; authored interpretation fields excluded"
        return result


class VerificationRun:
    def __init__(self, gateway, arm):
        self.gateway, self.journal, self.arm = gateway, gateway.journal, arm
        self.phase, self.stream = "initial", "repair"
        self.entry = None
        self.report = None
        self.pinned_diff = None
        self.input_journal = JournalView(self.journal, self, stream=True)
        self.plan_journal = JournalView(self.journal, self)
        self.gateway._public_history = ObservationHistory(self)

    def bind(self, *, request, counters, ledger, store, resuming):
        require(not resuming and not any(e["event_type"] == PHASE_EVENT
                                        for e in self.journal.events()),
                "verification comparison does not resume or replace rows")
        require(request.repeat == 1 and request.context_policy == "segmented-v1"
                and request.segment_boundary_policy == "result-or-size-v1"
                and request.completion_cost_policy == "per-call-v1"
                and request.agent_policy == "current", "comparison policy binding changed")
        require(request.limits.max_model_calls == 40
                and request.limits.max_tool_actions == 100
                and request.limits.max_accepted_mutations == 4,
                "comparison total resource limits changed")
        if ledger is not None:
            require(ledger.cap_nanos == 880_000_000, "comparison row cap changed")
        self.request, self.counters, self.ledger, self.store = request, counters, ledger, store
        self.row_cost_start = ledger.spent_nanos if ledger else 0
        self._start("initial", "initialization")

    def usage(self):
        return {"model_calls": self.counters.model_calls,
                "tool_actions": self.counters.tool_actions,
                "edits": self.gateway.accepted_mutations,
                "cost_nanos": ((self.ledger.spent_nanos - self.row_cost_start)
                               if self.ledger else 0)}

    def spent(self):
        return {key: value - self.entry[key] for key, value in self.usage().items()}

    def remaining(self):
        if self.phase == "final":
            totals = {"model_calls": 40, "tool_actions": 100, "edits": 4,
                      "cost_nanos": 880_000_000}
            return {k: max(0, v - self.usage()[k]) for k, v in totals.items()}
        return {k: max(0, v - self.spent()[k]) for k, v in LIMITS[self.phase].items()}

    def _safe(self):
        events = self.journal.events()
        if self.journal.unresolved_provider_call() is not None:
            raise RecoveryError("cannot switch phase with unsettled provider dispatch")
        starts = {e["payload"]["action_id"] for e in events if e["event_type"] == "action_started"}
        ends = {e["payload"]["action_id"] for e in events if e["event_type"] == "action_finished"}
        if starts - ends:
            raise RecoveryError("cannot switch phase with an unresolved action")
        decision = next((e for e in reversed(events)
                         if e["event_type"] == "turn_decision_recorded"), None)
        if decision is None:
            return
        turn = decision["payload"]["turn_id"]
        if any(e["event_type"] == "tool_batch_finished" and e["payload"]["turn_id"] == turn
               for e in events):
            return
        rejected = any(e["event_type"] == "protocol_correction"
                       and e["payload"]["turn_id"] == turn
                       and e["sequence"] > decision["sequence"] for e in events)
        started = any(e["event_type"] == "tool_batch_started"
                      and e["payload"]["turn_id"] == turn for e in events)
        if not rejected or started:
            raise RecoveryError("cannot switch phase with an unfinished batch")

    def _start(self, phase, reason):
        self._safe()
        if phase == "verify":
            archived = self.store.put_json({
                "notes": self.gateway.working_notes(),
                "question_bodies": self.gateway._working_question_bodies,
            })
            self.gateway._restore_working_notes_state({
                "findings": [], "source_bodies_by_note_id": {}, "lifecycle": None,
                "open_question": QUESTION, "question_bodies": [],
            })
            self.gateway._verification_state["items"] = []
            self.pinned_diff = self.gateway.current_diff_hash
        else:
            archived = None
        self.phase = phase
        self.stream = "verifier" if self.arm == "B" and phase == "verify" else "repair"
        self.entry = self.usage()
        event = self.journal.append(PHASE_EVENT, {
            "phase": phase, "stream": self.stream, "arm": self.arm, "reason": reason,
            "usage": self.entry, "diff_hash": self.gateway.current_diff_hash,
            "candidate_present": bool(self.gateway.current_diff.patch),
            "archived_notes": archived.model_dump(mode="json") if archived else None,
            "contract_hash": sha256_json(contract()),
            "remaining_wall_seconds": (self.gateway.deadline.remaining_seconds()
                                       if self.gateway.deadline else None),
        })
        self.phase_sequence = event["sequence"]

    def before_turn(self):
        if self.phase != "final" and any(
                self.spent()[key] > limit for key, limit in LIMITS[self.phase].items()):
            raise RecoveryError("verification phase resource envelope exceeded")
        if self.phase == "verify" and self.gateway.current_diff_hash != self.pinned_diff:
            raise RecoveryError("read-only verification candidate changed")
        if self.phase == "final":
            return
        if self.phase == "verify":
            reports = [e["payload"]["result"] for e in self.journal.events()
                       if e["event_type"] == "action_finished"
                       and e["payload"]["result"]["tool"] == REPORT_TOOL
                       and e["payload"]["result"]["status"] == "succeeded"]
            if reports:
                self.report = reports[-1]
                self._start("final", "report_completed")
                return
        remaining = self.remaining()
        exhausted = any(remaining[k] == 0 for k in ("model_calls", "tool_actions", "cost_nanos"))
        if self.phase == "initial":
            exhausted |= remaining["edits"] == 0
            if exhausted or self.gateway.ready_to_submit():
                self._start("verify", "initial_envelope" if exhausted else "candidate_ready")
        elif exhausted:
            self._incomplete("verification_envelope")

    def _incomplete(self, reason):
        self._safe()
        self.report = {"status": "VERIFICATION_INCOMPLETE", "workspace_diff_hash": self.pinned_diff,
                       "output": {"reason": reason, "assessment": None}}
        self.journal.append("verification_incomplete", copy.deepcopy(self.report))
        self._start("final", reason)

    def policy(self, policy):
        if self.entry is None:
            return policy
        names = set(policy.allowed_tools)
        if self.phase != "final":
            names.discard("finish_task")
        if self.phase == "verify":
            names.discard("replace_text")
            names.add(REPORT_TOOL)
        remaining = self.remaining()
        return replace(policy, allowed_tools=frozenset(names), max_parallel_reads=min(
            policy.max_parallel_reads, max(1, remaining["tool_actions"])))

    def cost_reserve(self):
        if self.ledger is None or self.phase == "final":
            return 0
        return max(0, self.ledger.remaining_nanos - self.remaining()["cost_nanos"])

    def cost_limited(self, input_tokens):
        if self.phase == "final":
            return False
        self.journal.append("verification_phase_cost_limit", {
            "phase": self.phase, "input_tokens": input_tokens, "remaining": self.remaining(),
        })
        if self.phase == "initial":
            self._start("verify", "initial_cost_envelope")
        else:
            self._incomplete("verification_cost_envelope")
        return True

    def context(self, context):
        value = json.loads(context)
        value["recent_attempt_result_next_question"] = runner._cards(
            self.plan_journal, runner._pending_protocol_correction(self.journal))
        if self.phase == "verify":
            for key in ("last_failed_mutation", "last_successful_mutation", "commitment_signal",
                        "current_public_failure"):
                value.pop(key, None)
            for row in value.get("evidence_ledger", {}).get("recent_inspection_outcomes", []):
                row.pop("evidence_goal", None)
            value["latest_tool_results"] = [observed_result(r)
                                             for r in value["latest_tool_results"]]
            notes = value["working_notes"]
            notes.pop("last_update_result", None)
            notes.pop("last_update_diagnostics", None)
            value["completion_guidance"] = {"stage": "verification", "next_action":
                "Use available public checks or finish_verification with a bounded report."}
        if self.request.planning_policy != "none":
            value["working_plan"] = working_plan.project(
                self.plan_journal.events(), diff_hash=self.gateway.current_diff_hash,
                gate=value["workflow_gate"], policy=self.request.planning_policy,
                public_issue=value.get("public_task", {}).get("issue"))
        value["verification_phase"] = {
            "phase": self.phase, "remaining": self.remaining(),
            "instruction": INSTRUCTION if self.phase == "verify" else (
                "Repair within the initial envelope; verification follows before submission."
                if self.phase == "initial" else
                "Use the verification report as evidence, not completion permission. "
                "An edit makes its verdict historical; verify the new candidate "
                "before submission."),
            "reviewed_diff_hash": self.pinned_diff,
            "report": copy.deepcopy(self.report),
            "report_currency": ("current" if self.pinned_diff == self.gateway.current_diff_hash
                                else "historical") if self.report else None,
        }
        return canonical_json(value)

    def schemas(self, schemas):
        if self.phase != "verify":
            return schemas
        schema, = tools.dev_tool_schemas(finish_enabled=True, allowed_tools={"finish_task"},
                                         planning_policy=self.request.planning_policy)
        schema["name"] = REPORT_TOOL
        schema["description"] = INSTRUCTION
        schema["parameters"]["properties"]["assessment"]["description"] = (
            "Scope, caller/setup/input, expected/observed result, counterconditions and next step. "
            "Uncertainty is allowed. Public assessment, not a task submission.")
        return [*schemas, schema]

    def public_evidence(self, state):
        """Quote only the current pair's observations excluded by the native view."""
        if self.arm != "B" or self.phase != "final":
            return []
        events = [e for e, phase, _ in phased_events(self.journal.events()) if phase == "verify"]
        exchanges = evidence_focus.optional_exchanges(
            state.get("working_notes", {}).get("open_question"), events,
            diff_hash=state["current_diff"]["patch_hash"],
        )
        for item in exchanges:
            if item["type"] == "function_call_output":
                item["output"] = canonical_json(observed_result(json.loads(item["output"])))
        return exchanges

    def dispatched(self, turn):
        artifact = Artifact.model_validate(turn["model_input_artifact"])
        items = json.loads(self.store.read_bytes(artifact))
        state = reconstruct_state(items, context_policy="segmented-v1")
        actual = state.get("verification_phase")
        if not actual or actual["phase"] != self.phase or actual["report"] != self.report:
            raise RecoveryError("phase/report was not delivered in the actual model input")
        self.journal.append("verification_phase_dispatched", {
            "phase": self.phase, "stream": self.stream, "turn_id": turn["turn_id"],
            "input_hash": turn["model_input_hash"], "report_hash": sha256_json(self.report),
            "source_projection_hash": turn["source_projection_hash"],
        })


class VerificationGateway(_BASE_GATEWAY):
    def __init__(self, *, arm, **kwargs):
        super().__init__(**kwargs)
        self.run_extension = VerificationRun(self, arm)

    def execute(self, call):
        phase = self.run_extension.phase
        if phase == "verify" and call.name in {"replace_text", "finish_task"}:
            raise ContractError("verification is read-only and cannot submit")
        if phase != "final" and call.name == "finish_task":
            raise ContractError("submission follows the mandatory verification phase")
        if phase != "verify" and call.name == REPORT_TOOL:
            raise ContractError("verification report is unavailable in this phase")
        return super().execute(call)

    def _perform(self, name, arguments):
        if name != REPORT_TOOL:
            return super()._perform(name, arguments)
        assessment = FinishIntent.model_validate(arguments).assessment
        if self.current_diff_hash != self.run_extension.pinned_diff:
            raise RecoveryError("verification candidate changed before report")
        question = self.working_notes().get("open_question")
        references = (copy.deepcopy(question["evidence"]) if evidence_focus.priority_status(
            question, self.current_diff_hash) == "eligible" else [])
        require(len(references) <= 2, "verification must share two reference slots")
        return {"assessment": assessment, "reviewed_diff_hash": self.current_diff_hash,
                "references": references, "interpretation_status": "model_authored_unverified",
                "repair_success": "not_assessed"}


def _validate(calls, **kwargs):
    if not any(c.name == REPORT_TOOL for c in calls):
        return _BASE_VALIDATE(calls, **kwargs)
    allowed = kwargs.get("allowed_tools")
    if allowed is not None and REPORT_TOOL not in allowed:
        raise ContractError("verification report unavailable at the current gate")
    # Reuse the exact finish-family annotation/batch grammar without changing the
    # executable call, action identity, recorded name, or the default tool surface.
    if allowed is not None:
        kwargs["allowed_tools"] = (set(allowed) - {REPORT_TOOL}) | {"finish_task"}
    return _BASE_VALIDATE([c.model_copy(update={"name": "finish_task"})
                           if c.name == REPORT_TOOL else c for c in calls], **kwargs)


def _policy(gateway, *args, **kwargs):
    policy = _BASE_POLICY(gateway, *args, **kwargs)
    extension = getattr(gateway, "run_extension", None)
    return extension.policy(policy) if extension else policy


def _schemas(**kwargs):
    if kwargs.get("allowed_tools") is not None:
        kwargs["allowed_tools"] = set(kwargs["allowed_tools"]) - {REPORT_TOOL}
    return tools.dev_tool_schemas(**kwargs)


@contextmanager
def assigned(arm):
    global _ACTIVE
    require(arm in {"A", "B"} and not _ACTIVE, "one verification arm per process required")
    _ACTIVE = True
    try:
        # Keep isinstance checks in the core policy valid.
        class Gateway(VerificationGateway):
            def __init__(self, **kwargs):
                super().__init__(arm=arm, **kwargs)

        def model_hash(request, pricing):
            return sha256_json({"base": _BASE_MODEL_HASH(request, pricing),
                                "verification_role": contract(), "arm": arm})

        with (patch.object(runner, "DevToolGateway", Gateway),
              patch.object(runner, "dev_tool_schemas", _schemas),
              patch.object(runner, "_tool_policy", _policy),
              patch.object(runner, "_model_hash", model_hash),
              patch.object(runner, "validate_tool_batch", _validate),
              patch.object(tools, "validate_tool_batch", _validate)):
            yield
    finally:
        _ACTIVE = False


def initialize_worker_a(stop, admission):
    _initialize_worker(stop, admission, "A")


def initialize_worker_b(stop, admission):
    _initialize_worker(stop, admission, "B")


def _initialize_worker(stop, admission, arm):
    from diagnostics.parallel_dev_batch import initialize_worker

    initialize_worker(stop, admission)
    global _WORKER_SCOPE
    _WORKER_SCOPE = assigned(arm)
    _WORKER_SCOPE.__enter__()
