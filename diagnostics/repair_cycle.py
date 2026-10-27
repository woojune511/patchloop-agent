"""Public original-call feedback between edits, sharing completed receipts at finish."""
from __future__ import annotations

import copy
from pathlib import Path

from diagnostics import selection_observation as host
from diagnostics.repair_cycle_budget import DEFAULT_LIMITS, CycleLimits
from patchloop.artifacts import ArtifactStore
from patchloop.dev.contracts import DevLimits, DevToolResult, RequestedTool
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import DevToolGateway
from patchloop.repository import WorkspaceManager
from patchloop.runtime import repository_root
from patchloop.util import sha256_json


def public_observation(result):
    """Measured public fields only; auxiliary coverage never replaces the caller result."""
    output = result["output"]
    trace = output["reproduction"]["call_observation"]
    calls = [{key: copy.deepcopy(row.get(key)) for key in (
        "call_id", "outcome", "exit_code", "exception", "capture")}
             for row in trace["calls"]]
    line = output.get("public_execution")
    if isinstance(line, dict):
        line = {key: copy.deepcopy(line.get(key)) for key in (
            "schema_version", "status", "scope", "diff_hash", "diagnostic_only",
            "deleted_line_count", "omitted_file_count", "files")}
    return {"calls": calls,
            "exception_diagnostics": copy.deepcopy(output.get("exception_diagnostics")),
            "changed_line_observation": line,
            "coverage_limit": "Line entry in the launch thread across the original calls; "
                "not branch coverage or proof about a particular call or other threads."}


class OriginalCallRecheck:
    """One fresh baseline and at most one settled execution per current diff.

    The original model tool quota is separate. All host work shares the model
    deadline and a finite host-action allowance. Unfinished starts never dispatch
    again; a complete action receipt can be reused after a diagnostic restart.
    """

    def __init__(self, loaded, model_gateway, root, *, limits: CycleLimits = DEFAULT_LIMITS):
        self.loaded, self.model_gateway = loaded, model_gateway
        self.root, self.limits = Path(root), limits
        self.arguments = copy.deepcopy(loaded.original_arguments)
        self.argument_hash = sha256_json(self.arguments)
        self.journal = DevJournal(self.root, "run_dev_originalrecheck")
        self.base_journal = DevJournal(self.root / "base", "run_dev_originalrecheckbase")
        self.store = ArtifactStore(self.root / "artifacts")
        self.binding = {
            "arguments_hash": self.argument_hash,
            "public_task_hash": sha256_json(loaded.public.model_dump(mode="json")),
            "prepared_source_hash": host.SOURCE_HASH,
            "dependency_hash": host.DEPENDENCY_HASH,
            "probe_image": host.PROBE_IMAGE, "probe_profile": host.PROBE_PROFILE,
        }
        bound = [event["payload"] for event in self.journal.events()
                 if event["event_type"] == "original_recheck_bound"]
        host.require(not bound or bound == [self.binding], "original replay binding changed")
        if not bound:
            self.journal.append("original_recheck_bound", self.binding)

    def _call(self, diff_hash):
        identity = sha256_json({**self.binding, "candidate_diff_hash": diff_hash})[7:39]
        return RequestedTool(name="run_probe", action_id="original-recheck-" + identity,
                             arguments=copy.deepcopy(self.arguments))

    def _completed(self, journal, diff_hash):
        events = journal.events()
        finished = {event["payload"]["action_id"] for event in events
                    if event["event_type"] == "action_finished"}
        host.require(all(event["payload"]["action_id"] in finished for event in events
                         if event["event_type"] == "action_started"),
                     "original replay has an unfinished action; no automatic retry")
        call = self._call(diff_hash)
        result = journal.action_result(call.action_id,
            sha256_json({"tool": call.name, "arguments": call.arguments}))
        if result is not None:
            host.require(result.workspace_diff_hash == diff_hash,
                         "original replay receipt belongs to another diff")
            # action_result marks its returned copy replayed. Keep the original
            # settled receipt bytes stable when sharing evidence with final checks.
            raw = next(event["payload"]["result"] for event in events
                       if event["event_type"] == "action_finished"
                       and event["payload"]["action_id"] == call.action_id)
            result = DevToolResult.model_validate(raw)
        return result

    @property
    def host_actions(self):
        return sum(event["event_type"] == "action_started"
                   for journal in (self.journal, self.base_journal)
                   for event in journal.events())

    def needed_actions(self, *, for_new_diff=False):
        base = self._completed(self.base_journal, host.EMPTY_DIFF)
        current_hash = self.model_gateway.current_diff_hash
        current = self._completed(self.journal, current_hash)
        if not for_new_diff and (current_hash == host.EMPTY_DIFF and base is not None
                                 or current is not None):
            return 0
        return int(base is None) + int(for_new_diff or current_hash != host.EMPTY_DIFF)

    def needed_original_seconds(self, *, for_new_diff=False):
        return self.needed_actions(for_new_diff=for_new_diff) * self.limits.original_recheck_seconds

    def _gateway(self, workspace, journal):
        original = self.model_gateway
        return DevToolGateway(workspace=workspace, public_task=self.loaded.public,
            sandbox=original.sandbox, probe_sandbox=original.probe_sandbox,
            journal=journal, deadline=original.deadline,
            limits=DevLimits(max_tool_actions=self.limits.host_original_actions))

    def _baseline_gateway(self):
        workspace = WorkspaceManager(repository_root() / "fixtures/repositories",
            self.root / "workspaces", prepared_source=host.SOURCE,
            prepared_source_hash=host.SOURCE_HASH).create("original-base",
                self.loaded.public.repository.url, self.loaded.public.repository.base_commit,
                deadline=self.model_gateway.deadline)
        host.require(WorkspaceManager.diff_summary(workspace).patch_hash == host.EMPTY_DIFF,
                     "original replay baseline is not clean")
        return self._gateway(workspace, self.base_journal)

    def _execute(self, gateway, diff_hash):
        host.require(self.host_actions < self.limits.host_original_actions,
                     "original replay host-action allowance exhausted")
        host.require(gateway.current_diff_hash == diff_hash,
                     "original replay candidate changed before dispatch")
        result = gateway.execute(self._call(diff_hash))
        host.require(gateway.current_diff_hash == diff_hash
                     and result.workspace_diff_hash == diff_hash,
                     "original replay changed the candidate")
        abort, reason = host.loop.runner._batch_execution_abort([result])
        host.require(abort is None, "original replay execution aborted: " + str(reason))
        return result

    def current_receipts(self):
        """Return only complete public receipts for this exact current diff, or None."""
        base = self._completed(self.base_journal, host.EMPTY_DIFF)
        current_hash = self.model_gateway.current_diff_hash
        current = (base if current_hash == host.EMPTY_DIFF else
                   self._completed(self.journal, current_hash))
        if base is None or current is None:
            return None
        pair = tuple(result.model_dump(mode="json") for result in (base, current))
        host.original_summary(*pair)  # Incomplete captures never become reusable evidence.
        return pair

    def check(self):
        before = self.model_gateway.current_diff_hash
        self.model_gateway.deadline.check()
        base = self._completed(self.base_journal, host.EMPTY_DIFF)
        if base is None:
            base = self._execute(self._baseline_gateway(), host.EMPTY_DIFF)
        host.original_summary(base.model_dump(mode="json"), base.model_dump(mode="json"))
        current = (base if before == host.EMPTY_DIFF else self._completed(self.journal, before))
        reused = current is not None
        if current is None:
            current = self._execute(self._gateway(self.model_gateway.workspace, self.journal),
                                    before)
        host.require(self.model_gateway.current_diff_hash == before,
                     "candidate changed during original replay")
        pair = tuple(result.model_dump(mode="json") for result in (base, current))
        comparison = host.original_summary(*pair)
        feedback = {
            "schema": "original-call-feedback-v1", "candidate_diff_hash": before,
            "arguments_hash": self.argument_hash,
            "status": "supported" if comparison["supported"] else "failed",
            "comparison": comparison, "observed": public_observation(pair[1]),
            "base_receipt": self.store.put_json(pair[0]).model_dump(mode="json"),
            "candidate_receipt": self.store.put_json(pair[1]).model_dump(mode="json"),
            "candidate_receipt_reused": reused, "task_acceptance": "NOT_ASSESSED",
        }
        self.journal.append("original_recheck_feedback", feedback)
        return feedback
