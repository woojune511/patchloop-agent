"""Capture one public helper replay and attach its bound feedback without rerunning it.

The capture is a real registered action when no probe sandbox is injected. Neither
entry point constructs a provider, counts tokens, or evaluates a candidate.
"""
from __future__ import annotations

import copy
import json
import math
from contextlib import contextmanager
from pathlib import Path
from time import monotonic
from unittest.mock import patch

from diagnostics.checkpoint_continuation import _artifacts, inherited_reads
from diagnostics.decision_sampler import require
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact
from patchloop.deadline import ExecutionDeadline
from patchloop.dev import probe_replay, runner
from patchloop.dev.contracts import DevToolResult, RequestedTool
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import DevToolGateway, validate_tool_batch
from patchloop.repository import WorkspaceManager
from patchloop.sandbox import LocalSandbox
from patchloop.util import canonical_json, sha256_bytes, sha256_json

SCHEMA = "checkpoint-helper-replay-v1"
ACTION_ID = "checkpoint_helper_replay"
TURN_ID = "checkpoint_helper_replay_batch"
STARTED = "checkpoint_helper_replay_started"
CAPTURED = "checkpoint_helper_replay_captured"
ATTACHED = "checkpoint_helper_replay_attached"


def _state(branch, target):
    events = branch.journal.events()
    marker = events[branch.inherited_events]
    require(marker["event_type"] == "observation_exposure_fork"
            and sha256_json(marker["payload"]) == branch.marker_hash,
            "checkpoint fork binding changed")
    require(not any(e["event_type"] in {STARTED, ATTACHED, "action_started",
                    "provider_call_started", "input_count_started", "terminal"}
                    for e in events[branch.inherited_events + 1:]),
            "replay requires an unused checkpoint branch")
    require(branch.journal.unresolved_provider_call() is None
            and branch.journal.unresolved_input_count() is None,
            "checkpoint has uncertain provider work")
    program = probe_replay.prepare({"replay_action_id": target}, events)
    summary = WorkspaceManager.diff_summary(branch.workspace)
    require(not summary.untracked_files, "checkpoint has untracked candidate files")
    envelope = branch.envelope
    configuration = {key: getattr(envelope, key) for key in (
        "runtime_hash", "model", "reasoning_effort", "max_output_tokens",
        "max_correction_output_tokens", "verification_policy", "probe_policy",
        "agent_policy", "context_policy", "completion_cost_policy",
        "evaluation_reserve_seconds", "probe_image_digest", "probe_profile_hash",
    )}
    configuration["limits"] = branch.request.limits.model_dump(mode="json")
    return {
        "parent": branch.source.record(),
        "parent_prefix_hash": marker["payload"]["parent_prefix_hash"],
        "candidate_diff_hash": summary.patch_hash,
        "target_action_id": target,
        "replayed_from": program["replayed_from"],
        "question_hash": sha256_bytes(program["question"].encode()),
        "source_hash": sha256_bytes(program["python_source"].encode()),
        "configuration": configuration,
        "original_active_elapsed_ms": branch.active_elapsed_ms,
    }


def _call(branch, target):
    annotations = ({"memory_update": None} if branch.request.agent_policy == "thin" else {
        "turn_decision": {"mode": "verify", "basis": "Replay the existing public helper.",
                          "evidence_goal": None, "memory_update": None, "plan_update": None},
    })
    return RequestedTool(name="run_probe", action_id=ACTION_ID, arguments={
        "replay_action_id": target, "question": None, "python_source": None,
        "purpose": None, "call_path": None,
    }, **annotations)


def _gateway(branch, deadline, probe_sandbox):
    request, envelope = branch.request, branch.envelope
    dependencies = (runner.load_dependencies(request.prepared_probe_dependencies,
                    branch.package.public, envelope.probe_dependencies)
                    if request.prepared_probe_dependencies is not None else None)
    if dependencies is not None:
        dependencies.verify(deadline=deadline)
    callers = runner.caller_sources_for_run(dependencies, request.caller_source_roots,
                                           branch.package.public)
    probe = probe_sandbox or runner.DockerProbeSandbox(dependencies=dependencies)
    require(probe.preflight(deadline=deadline) == {
        "image_digest": envelope.probe_image_digest, "profile_hash": envelope.probe_profile_hash,
    }, "replay probe environment differs from checkpoint")
    return DevToolGateway(
        workspace=branch.workspace, public_task=branch.package.public, sandbox=LocalSandbox(),
        journal=branch.journal, limits=request.limits, deadline=deadline, probe_sandbox=probe,
        probe_policy=request.probe_policy, retained_source_chars=request.retained_source_chars,
        reproduction_acquisition=request.reproduction_acquisition,
        verification_policy=request.verification_policy, agent_policy=request.agent_policy,
        history_search_policy=request.history_search_policy, dependency_sources=callers,
    )


def _counters(branch):
    counters = runner._restore_counters(branch.journal)
    edits = sum(e["event_type"] == "action_finished"
                and e["payload"]["result"]["tool"] == "replace_text"
                and e["payload"]["result"]["status"] == "succeeded"
                and e["payload"]["result"].get("error_code") is None
                for e in branch.journal.events())
    return counters.model_calls, counters.tool_actions, edits


def _completed(events, binding, call):
    """Require the complete durable action, execution and batch receipt chain."""
    kinds = [e["event_type"] for e in events]
    for kind in ("tool_batch_started", "action_started", "probe_execution_started",
                 "probe_execution_finished", "action_finished", "tool_batch_finished"):
        require(kinds.count(kind) == 1, "replay is missing a unique execution receipt")
    require(not any(kind in {"provider_call_started", "provider_call_finished", "terminal"}
                    for kind in kinds), "replay contains unrelated execution")
    payload = {e["event_type"]: e["payload"] for e in events}
    start, finish = payload["action_started"], payload["action_finished"]["result"]
    require(start["action_id"] == finish["action_id"] == ACTION_ID
            and start["tool"] == finish["tool"] == "run_probe"
            and start["arguments"] == call.arguments
            and start["input_hash"] == finish["input_hash"]
            and start["baseline_diff_hash"] == finish["workspace_diff_hash"]
            == binding["candidate_diff_hash"], "replay action/input/candidate identity changed")
    require(finish["status"] == "succeeded" and finish.get("error_code") is None,
            "replay action did not complete")
    output = finish["output"]
    raw = payload["probe_execution_finished"]["output"]
    require(all(value.get("status") == "passed" and value.get("exit_code") == 0
                and value.get("execution_policy", {}).get("cleanup_status") == "confirmed"
                and not any(value.get(key) for key in (
                    "cleanup_failed", "timed_out", "deadline_exhausted", "truncated"))
                for value in (raw, output)), "replay execution or cleanup is incomplete")
    require(output["source_hash"] == binding["source_hash"]
            and sha256_bytes(output["question"].encode()) == binding["question_hash"]
            and start["probe_replay_request"]["replayed_from"] == binding["replayed_from"],
            "replay did not reuse the exact public program")
    for kind in ("probe_execution_started", "probe_execution_finished"):
        require(payload[kind]["action_id"] == ACTION_ID, "probe receipt belongs to another action")
    require(payload["tool_batch_started"]["tool_calls"] == [call.model_dump(mode="json")]
            and payload["tool_batch_finished"]["action_ids"] == [ACTION_ID]
            and payload["tool_batch_finished"]["result_fingerprints"] == [sha256_json(finish)],
            "replay batch result binding changed")
    return finish


def packet_result(packet):
    """Return the raw registered result, without interpreting helper output."""
    results = [e["payload"]["result"] for e in packet["events"]
               if e["event_type"] == "action_finished"]
    require(len(results) == 1 and results[0]["action_id"] == ACTION_ID,
            "replay packet has no unique action result")
    return copy.deepcopy(results[0])


@contextmanager
def host_handoff(branch, packet):
    """Keep a host replay out of provider history while delivering its current state.

Only the inherited fresh completion segment is supported. The original native
exchange still validates its actual model-requested results. Once the model makes
a new decision, normal exchange and segment-cursor behavior resume unchanged.
"""
    original_exchange, original_cursor = runner._build_latest_exchange, runner.segments.cursor
    raw_result = packet_result(packet)

    def inherited(events):
        decision = next((e for e in reversed(events)
                         if e["event_type"] == "turn_decision_recorded"), None)
        attached = any(e["event_type"] == ATTACHED
                       and e["payload"]["packet_hash"] == packet["packet_hash"] for e in events)
        return decision if attached and decision and decision["sequence"] <= (
            branch.inherited_events) else None

    def cursor(events):
        if inherited(events) is None:
            return original_cursor(events)
        return original_cursor([e for e in events if not (
            e["sequence"] > branch.inherited_events and (
                (e["event_type"] == "action_finished"
                 and e["payload"]["result"]["action_id"] == ACTION_ID)
                or (e["event_type"] == "tool_batch_finished"
                    and e["payload"]["turn_id"] == TURN_ID)))])

    def exchange(**kwargs):
        if kwargs["journal"].path != branch.journal.path:
            return original_exchange(**kwargs)
        events = branch.journal.events()
        decision = inherited(events)
        latest = kwargs["latest_tool_results"]
        if decision is None or [r.action_id for r in latest] != [ACTION_ID]:
            return original_exchange(**kwargs)
        require(latest[0].model_dump(mode="json") == raw_result,
                "host replay result differs from captured feedback")
        require(runner.completion_context.active(json.loads(kwargs["context"])),
                "host replay handoff requires compact completion context")
        binding, _ = runner.segments.active(
            branch.journal, branch.store,
            boundary_policy=branch.request.segment_boundary_policy,
            agent_policy=branch.request.agent_policy,
        )
        require(runner.segments.is_fresh(branch.journal, binding),
                "host replay handoff requires the inherited fresh completion segment")
        ids = [call["action_id"] for call in decision["payload"]["tool_calls"]]
        results = {e["payload"]["result"]["action_id"]: e["payload"]["result"]
                   for e in events[:branch.inherited_events]
                   if e["event_type"] == "action_finished"}
        require(all(key in results for key in ids), "inherited model result is missing")
        return original_exchange(**{**kwargs, "latest_tool_results": [
            DevToolResult.model_validate(results[key]) for key in ids]})

    with patch.object(runner.segments, "cursor", cursor), \
            patch.object(runner, "_build_latest_exchange", exchange):
        yield


def _artifact_inventory(branch, events):
    found, pending = {}, list(_artifacts(events))
    with inherited_reads(branch):
        while pending:
            reference = pending.pop()
            key = sha256_json(reference.model_dump(mode="json"))
            if key in found:
                continue
            raw = branch.store.read_bytes(reference)
            stored = branch.store.put_bytes(raw, reference.media_type)
            found[key] = {"reference": reference.model_dump(mode="json"),
                          "stored": stored.model_dump(mode="json")}
            if reference.media_type.startswith("application/json"):
                pending.extend(_artifacts(json.loads(raw)))
    return list(found.values())


def capture(branch, target_action_id, *, probe_sandbox=None):
    """Execute exactly one original helper on the current candidate; never call a model."""
    with branch.journal.execution_lock(), inherited_reads(branch):
        binding = _state(branch, target_action_id)
        require(branch.request.enable_probes and branch.request.probe_policy == "none",
                "checkpoint replay requires enabled ordinary probes")
        before = _counters(branch)
        started = monotonic()
        remaining = (branch.request.limits.wall_time_seconds
                     - branch.request.evaluation_reserve_seconds - branch.active_elapsed_ms / 1000)
        require(remaining > 0, "checkpoint has no solver time remaining")
        deadline = ExecutionDeadline.from_remaining(remaining)
        marker = branch.journal.append(STARTED, {"binding": binding})
        gateway = _gateway(branch, deadline, probe_sandbox)
        call = _call(branch, target_action_id)
        counters = runner._restore_counters(branch.journal)
        request = branch.request
        policy = runner._tool_policy(
            gateway, counters, request.limits,
            repair_inspection_policy=request.repair_inspection_policy,
            repair_recheck=request.repair_recheck, cost_ledger=branch.ledger,
            completion_cost_policy=request.completion_cost_policy,
            desired_output_ceiling=request.max_output_tokens,
            max_correction_output_tokens=request.max_correction_output_tokens,
            remaining_seconds=max(0, remaining - (monotonic() - started)),
        )
        validate_tool_batch([call], allowed_tools=policy.allowed_tools,
                            agent_policy=request.agent_policy,
                            path_diagnosis_pending=policy.workflow_gate == "needs_path_diagnosis",
                            original_acquisition_pending=policy.workflow_gate in {
                                "needs_original_reproduction",
                                "needs_original_argument_correction"},
                            repair_test_comparison_pending=(
                                policy.workflow_gate == "needs_test_comparison"))
        require(policy.completion_possible and runner._batch_fits_tool_budget(
            [call], counters, request.limits, policy), "replay exceeds ordinary tool admission")
        branch.journal.append("tool_batch_started", {
            "turn_id": TURN_ID, "tool_calls": [call.model_dump(mode="json")],
            "active_elapsed_ms": branch.active_elapsed_ms,
        })
        result = gateway.execute(call)
        elapsed = math.ceil((monotonic() - started) * 1000)
        runner._record_tool_batch(journal=branch.journal, gateway=gateway, turn_id=TURN_ID,
            calls=[call], results=[result], active_elapsed_ms=branch.active_elapsed_ms + elapsed)
        events = branch.journal.events()[marker["sequence"]:]
        _completed(events, binding, call)
        require(_counters(branch) == (before[0], before[1] + 1, before[2]),
                "replay changed response, action or edit accounting")
        require(WorkspaceManager.diff_summary(branch.workspace).patch_hash
                == binding["candidate_diff_hash"], "replay changed candidate")
        packet = {"schema": SCHEMA, "capture_root": str(branch.root),
                  "run_id": branch.journal.run_id, "binding": binding,
                  "call": call.model_dump(mode="json"), "events": events, "elapsed_ms": elapsed,
                  "artifacts": _artifact_inventory(branch, events),
                  "interpretation": "Completed public helper output; not repair correctness."}
        artifact = branch.store.put_json(packet)
        receipt = branch.journal.append(CAPTURED, {
            "packet_hash": sha256_json(packet), "artifact": artifact.model_dump(mode="json"),
        })
        return {**packet, "packet_hash": sha256_json(packet),
                "capture_receipt_hash": receipt["event_hash"]}


def attach(branch, packet):
    """Attach a settled capture once, with its raw payloads and original resource charge."""
    packet = copy.deepcopy(packet)
    digest, receipt_hash = packet.pop("packet_hash"), packet.pop("capture_receipt_hash")
    require(packet.get("schema") == SCHEMA and sha256_json(packet) == digest,
            "replay packet hash changed")
    captured = DevJournal(Path(packet["capture_root"]), packet["run_id"])
    receipt = next((e for e in captured.events() if e["event_hash"] == receipt_hash), None)
    require(receipt is not None and receipt["event_type"] == CAPTURED
            and receipt["payload"]["packet_hash"] == digest,
            "capture receipt is missing or changed")
    source_store = ArtifactStore(Path(packet["capture_root"]) / "artifacts")
    require(json.loads(source_store.read_bytes(Artifact.model_validate(
        receipt["payload"]["artifact"]))) == packet, "immutable replay packet differs")
    with branch.journal.execution_lock(), inherited_reads(branch):
        binding = _state(branch, packet["binding"]["target_action_id"])
        require(binding == packet["binding"], "checkpoint candidate/prefix/program binding differs")
        elapsed = packet["elapsed_ms"]
        require(type(elapsed) is int and elapsed >= 0, "invalid replay elapsed time")
        call = _call(branch, binding["target_action_id"])
        require(call.model_dump(mode="json") == packet["call"], "replay call changed")
        result = _completed(packet["events"], binding, call)
        end = packet["events"][-1]
        require(end["event_type"] == "tool_batch_finished"
                and end["payload"]["active_elapsed_ms"] == branch.active_elapsed_ms + elapsed,
                "replay active-time accounting differs")
        before = _counters(branch)
        require(before[1] < branch.request.limits.max_tool_actions
                and branch.active_elapsed_ms + elapsed < 1000 * (
                    branch.request.limits.wall_time_seconds
                    - branch.request.evaluation_reserve_seconds),
                "replay exceeds checkpoint resources")
        copies = []
        for item in packet["artifacts"]:
            original = Artifact.model_validate(item["reference"])
            stored = Artifact.model_validate(item["stored"])
            raw = source_store.read_bytes(stored)
            require(sha256_bytes(raw) == original.content_hash and len(raw) == original.size_bytes,
                    "replay artifact bytes changed")
            copies.append((original, branch.store.put_bytes(raw, original.media_type)))
        for original, copied in copies:
            key = sha256_json(original.model_dump(mode="json"))
            branch.references[key] = (original.model_dump(mode="json"),
                                      copied.model_dump(mode="json"))
        fork_path = branch.root / "fork.json"
        fork = json.loads(fork_path.read_bytes())
        fork["references"] = branch.references
        fork_path.write_text(canonical_json(fork), encoding="utf-8")
        branch.journal.append(ATTACHED, {"packet_hash": digest,
            "capture_receipt_hash": receipt_hash, "execution_is_reused": True})
        for event in packet["events"]:
            branch.journal.append(event["event_type"], event["payload"])
        require(_counters(branch) == (before[0], before[1] + 1, before[2]),
                "attached replay changed response, action or edit accounting")
        require(branch.journal.latest_tool_batch_results()[0].model_dump(mode="json") == result,
                "attached raw result changed")
        return {"packet_hash": digest, "tool_actions": 1, "model_calls": 0,
                "accepted_mutations": 0, "elapsed_ms": elapsed, "target_executions": 0}
