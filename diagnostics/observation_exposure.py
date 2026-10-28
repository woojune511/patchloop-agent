"""Current-runtime restoration and offline observation-exposure rehearsal.

Synthetic SDK/probe results exercise the ordinary runner, not agent quality. No
credential or live dispatch entry point exists here. The separate funded collector
reuses the restoration primitive. Use separate processes for concurrent branches.
"""

from __future__ import annotations

import copy
import json
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from diagnostics.checkpoint_continuation import ScriptedClient, _artifacts, inherited_reads
from diagnostics.checkpoint_envelope import read_checkpoint_envelope
from diagnostics.cleanup_information_checkpoint import restore_candidate
from diagnostics.decision_sampler import require
from diagnostics.declaration_checkpoint import Source, disjoint
from patchloop.agent.model import OpenAIResponsesAdapter
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact
from patchloop.deadline import ExecutionDeadline
from patchloop.dev import completion_reproduction, original_obligation, runner
from patchloop.dev.contracts import DevRunRequest
from patchloop.dev.cost import DevCostLedger, pricing_for_model
from patchloop.dev.dependency_sources import normalize_roots
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError
from patchloop.repository import WorkspaceManager
from patchloop.runtime import repository_root
from patchloop.sandbox import LocalSandbox
from patchloop.sandbox.probes import probe_execution_policy
from patchloop.util import canonical_json, raw_file_set_hash, sha256_bytes, sha256_json


def implementation_hash():
    root = repository_root()
    return raw_file_set_hash(
        root, sorted(p.relative_to(root).as_posix() for p in (root / "diagnostics").glob("*.py"))
    )


def project(value, arm):
    """Remove only verification catalogs, including serialized tool-output views."""
    require(arm in {"A", "B"}, "unknown exposure arm")
    if arm == "B":
        return copy.deepcopy(value)

    def walk(item, path=()):
        if isinstance(item, dict):
            result = {}
            for key, child in item.items():
                if path[-2:] == ("working_notes", "verification") and key == "observations":
                    continue
                native_text = (
                    key == "content" and item.get("role") in {"user", "system", "developer"}
                ) or (key == "output" and item.get("type") == "function_call_output")
                if native_text and isinstance(child, str):
                    try:
                        parsed = json.loads(child)
                    except ValueError:
                        parsed = None
                    if isinstance(parsed, (dict, list)):
                        updated = walk(parsed)
                        if updated != parsed:
                            result[key] = canonical_json(updated)
                            continue
                result[key] = walk(child, (*path, key))
            return result
        if isinstance(item, list):
            return [walk(child, path) for child in item]
        return item

    return walk(value)


@contextmanager
def exposure(arm):
    """Project canonical state and every assembled input, not just the first turn."""
    build_context, build_input = runner._build_context, runner._build_model_input

    def context(**kwargs):
        return canonical_json(project(json.loads(build_context(**kwargs)), arm))

    def model_input(**kwargs):
        return project(build_input(**kwargs), arm)

    with (
        patch.object(runner, "_build_context", context),
        patch.object(
            runner,
            "_build_model_input",
            model_input,
        ),
    ):
        yield


def fork(source: Source, cut_sequence: int, output: Path, arm: str, *, synthetic_cap_usd: Decimal,
         preserve_parent_configuration=False, after_tool_batch=False):
    return _fork(
        source,
        cut_sequence,
        output,
        arm,
        new_cap_usd=synthetic_cap_usd,
        mode="offline-scripted-only",
        env_file=output / "NO_CREDENTIAL_FILE",
        preserve_parent_configuration=preserve_parent_configuration,
        after_tool_batch=after_tool_batch,
    )


def _parent_reader(source, events):
    """Read exact inherited references from an already-forked parent's local CAS."""
    require((source.root / "artifacts/objects/sha256").is_dir(), "parent artifact store missing")
    store = ArtifactStore(source.root / "artifacts")
    fork_path = source.root / "fork.json"
    references = {}
    if fork_path.exists():
        saved = json.loads(fork_path.read_bytes())
        require(any(event["event_type"] == "observation_exposure_fork"
                    and event["payload"] == saved.get("marker") for event in events),
                "parent artifact lineage is not journal-bound")
        references = saved["references"]

    def read(ref):
        replacement = references.get(sha256_json(ref.model_dump(mode="json")))
        if replacement is not None:
            require(replacement[0] == ref.model_dump(mode="json")
                    and all(replacement[1].get(key) == getattr(ref, key)
                            for key in ("content_hash", "media_type", "size_bytes")),
                    "parent inherited artifact identity changed")
            ref = Artifact.model_validate(replacement[1])
        return store.read_bytes(ref)

    return read


def _settled_batch_state(prefix, old, package):
    """Derive bounded continuation state from durable receipts, not an older input."""
    view = SimpleNamespace(events=lambda: prefix)
    for started, finished, key in (
        ("tool_batch_started", "tool_batch_finished", "turn_id"),
        ("action_started", "action_finished", "action_id"),
        ("probe_execution_started", "probe_execution_finished", "action_id"),
    ):
        pending = set()
        for event in prefix:
            if event["event_type"] == started:
                pending.add(event["payload"][key])
            elif event["event_type"] == finished:
                pending.discard(event["payload"][key])
        require(not pending, "uncertain parent tool execution")
    latest = DevJournal.latest_tool_batch_results(view)
    require(latest and prefix[-1]["payload"].get("result_fingerprints") == [
        sha256_json(result.model_dump(mode="json")) for result in latest
    ], "settled batch result identity changed")
    require(all(result.tool not in {"finish_task", "stop_task"} for result in latest),
            "completed solver endpoints cannot continue")
    for event in prefix:
        if event["event_type"] != "action_finished":
            continue
        result = event["payload"]["result"]
        output = result.get("output", {})
        require(not any(output.get(key) for key in (
            "cleanup_failed", "timed_out", "deadline_exhausted",
        )) and result.get("error_code") not in {"RECOVERY_ERROR", "RESUME_CONTRACT_MISMATCH"}
                and output.get("probe_stage") != "dispatch_pending",
                "uncertain parent execution or cleanup")
    empty = original_obligation.EMPTY_DIFF
    review = completion_reproduction.review(
        prefix, empty, public_task=package.public, run_id=old.run_id,
    )
    obligation = original_obligation.review(
        prefix, package.public, review, acquisition=old.reproduction_acquisition,
        probe_available=old.probe_image_digest is not None,
    )
    require(obligation["stage"] == "acquired" and obligation["status"] == "refuted"
            and len(obligation["baseline_failure_case_ids"]) == 1,
            "one acquired original failure required")
    require(all(result.workspace_diff_hash == empty for result in latest)
            and not any(event["event_type"] == "action_finished"
                        and event["payload"]["result"]["tool"] == "replace_text"
                        and event["payload"]["result"]["status"] == "succeeded"
                        and event["payload"]["result"].get("error_code") is None
                        for event in prefix), "after-batch continuation requires unchanged base")
    counters = runner._restore_counters(view)
    active = DevJournal.latest_active_elapsed_ms(view)
    require(type(prefix[-1]["payload"].get("active_elapsed_ms")) is int
            and prefix[-1]["payload"]["active_elapsed_ms"] == active,
            "settled batch active time is missing or regressed")
    usage = DevJournal.provider_usage(view)
    require(all(type(row.get("cost_nanos")) is int and row["cost_nanos"] >= 0
                and not row.get("error_code") for row in usage), "uncertain parent billing")
    budget = {
        "model_calls": old.limits.max_model_calls - counters.model_calls,
        "tool_actions": old.limits.max_tool_actions - counters.tool_actions,
        "accepted_mutations": old.limits.max_accepted_mutations,
        "active_wall_time_seconds": int(old.limits.wall_time_seconds
                                        - old.evaluation_reserve_seconds - active / 1000),
        "total_active_wall_time_seconds": int(old.limits.wall_time_seconds - active / 1000),
        "evaluation_reserve_seconds": old.evaluation_reserve_seconds,
        "cost": {"settled_usage": old.cost_start_nanos + sum(row["cost_nanos"] for row in usage)},
    }
    require(all(budget[key] > 0 for key in (
        "model_calls", "tool_actions", "accepted_mutations", "active_wall_time_seconds",
    )), "settled checkpoint has no remaining repair allowance")
    return budget, active, latest, obligation


def _fork(source, cut_sequence, output, arm, *, new_cap_usd, mode, env_file,
          preserve_parent_configuration=False, model_override=None, after_tool_batch=False,
          caller_source_roots=None):
    """Copy a settled prefix; bind current runtime without changing the parent."""
    require(
        model_override is None or preserve_parent_configuration,
        "model override requires preserved parent configuration",
    )
    require(caller_source_roots is None or preserve_parent_configuration,
            "caller source override requires preserved parent configuration")
    caller_override = (normalize_roots(caller_source_roots)
                       if caller_source_roots is not None else None)
    require(not after_tool_batch or preserve_parent_configuration,
            "after-batch continuation requires preserved parent configuration")
    require(arm in {"A", "B"}, "unknown exposure arm")
    require(mode in {"offline-scripted-only", "funded-observation"}, "unknown fork mode")
    require(
        new_cap_usd.is_finite() and new_cap_usd > 0,
        "positive finite new allowance required",
    )
    historical = DevJournal(source.root, source.run_id)
    for path, digest in (
        (historical.path, source.journal_hash),
        (historical.envelope_path, source.envelope_hash),
        (source.public_path, source.public_hash),
    ):
        require(sha256_bytes(path.read_bytes()) == digest, "source identity changed")
    events, old = historical.events(), read_checkpoint_envelope(source)
    caller_roots = (caller_override if caller_override is not None else
                    dict(old.caller_source_roots) if preserve_parent_configuration else {})
    require(
        old.provider == "openai"
        and old.split == "dev-train"
        and old.context_policy == "segmented-v1"
        and old.compaction_contract is None,
        "only dev-train segmented checkpoints without compaction are supported",
    )
    cut = next((e for e in events if e["sequence"] == cut_sequence), None)
    require(
        cut is not None and cut["event_type"] == (
            "tool_batch_finished" if after_tool_batch else "model_input_prepared"),
        "cut must be a settled tool batch" if after_tool_batch
        else "cut must precede a prepared model request",
    )
    prefix = [e for e in events if e["sequence"] < cut_sequence + int(after_tool_batch)]
    require(
        not any(e["event_type"] in {"diagnostic_candidate_seeded", "terminal"} for e in prefix),
        "seeded or terminal prefixes are not ordinary checkpoints",
    )
    view = SimpleNamespace(events=lambda: prefix)
    require(
        DevJournal.unresolved_provider_call(view) is None
        and DevJournal.unresolved_input_count(view) is None,
        "uncertain parent count or dispatch",
    )
    require(
        any(e["event_type"] == "tool_batch_finished" for e in prefix),
        "completed tool batch required",
    )
    task_dir, package = runner._resolve_task_file(source.public_path)
    require(
        package.public_spec_hash == old.public_spec_hash
        and package.task_content_hash == old.task_content_hash,
        "task identity changed",
    )
    latest, obligation = [], None
    if after_tool_batch:
        budget, active_elapsed_ms, latest, obligation = _settled_batch_state(prefix, old, package)
        expected_diff = original_obligation.EMPTY_DIFF
    else:
        read_parent = _parent_reader(source, prefix)
        bundle = json.loads(read_parent(Artifact.model_validate(cut["payload"]["artifact"])))
        context = json.loads(read_parent(
            Artifact.model_validate(bundle["turn"]["context_artifact"])))
        budget = context["remaining_budget"]
        active_elapsed_ms = int(bundle["turn"]["active_elapsed_ms"])
        expected_diff = context["current_diff"]["patch_hash"]
    read_parent = _parent_reader(source, prefix)
    output = output.resolve()
    disjoint(output, (repository_root(), source.root, task_dir))
    output.mkdir()
    store = ArtifactStore(output / "artifacts")
    references, pending = {}, list(_artifacts(prefix))
    while pending:
        ref = pending.pop()
        key = sha256_json(ref.model_dump(mode="json"))
        if key in references:
            continue
        data = read_parent(ref)
        copied = store.put_bytes(data, ref.media_type)
        references[key] = (ref.model_dump(mode="json"), copied.model_dump(mode="json"))
        if ref.media_type.startswith("application/json"):
            pending.extend(_artifacts(json.loads(data)))
    journal = DevJournal(output, source.run_id)
    with journal.path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write("".join(canonical_json(e) + "\n" for e in prefix))
    manager = WorkspaceManager(
        repository_root() / "fixtures/repositories",
        output / "workspaces",
        prepared_source=Path(old.prepared_source_path) if old.prepared_source_path else None,
        prepared_source_hash=old.prepared_source_hash,
    )
    require(
        manager.prepared_source is not None
        or package.public.repository.url.startswith("snapshot://"),
        "local source required",
    )
    workspace = manager.create(
        source.run_id,
        package.public.repository.url,
        package.public.repository.base_commit,
        deadline=ExecutionDeadline.from_remaining(120),
    )
    accepted = {
        e["payload"]["result"]["action_id"]
        for e in prefix
        if e["event_type"] == "action_finished"
        and e["payload"]["result"]["tool"] == "replace_text"
        and e["payload"]["result"]["status"] == "succeeded"
        and e["payload"]["result"].get("error_code") is None
    }
    for event in prefix:
        if event["event_type"] == "action_started" and event["payload"]["action_id"] in accepted:
            restore_candidate(workspace, event["payload"])
    require(
        WorkspaceManager.diff_summary(workspace).patch_hash
        == expected_diff,
        "candidate differs from checkpoint",
    )
    counters = runner._restore_counters(journal)
    require(
        old.limits.max_model_calls - counters.model_calls == budget["model_calls"]
        and old.limits.max_tool_actions - counters.tool_actions == budget["tool_actions"]
        and old.limits.max_accepted_mutations - len(accepted) == budget["accepted_mutations"],
        "restored action allowances differ",
    )
    model = model_override or (
        old.model if preserve_parent_configuration else "gpt-5.4-2026-03-05"
    )
    pricing = pricing_for_model(model)
    spent = budget["cost"]["settled_usage"]
    ledger = DevCostLedger(Decimal(spent) / 10**9 + new_cap_usd, pricing)
    ledger.restore_settled_usage(journal.provider_usage(), base_spent_nanos=old.cost_start_nanos)
    require(ledger.spent_nanos == spent, "historical billing differs")
    request = DevRunRequest(
        provider="openai",
        task=source.public_path,
        model=model,
        reasoning_effort=old.reasoning_effort if preserve_parent_configuration else "xhigh",
        max_output_tokens=old.max_output_tokens if preserve_parent_configuration else 25000,
        env_file=env_file,
        max_cost_usd=Decimal(ledger.cap_nanos) / 10**9,
        state_root=output,
        resume_run_id=source.run_id,
        limits=old.limits,
        prepared_source=manager.prepared_source,
        prepared_probe_dependencies=(
            Path(old.prepared_probe_dependencies_path)
            if old.prepared_probe_dependencies_path
            else None
        ),
        caller_source_roots=caller_roots,
        enable_probes=old.probe_image_digest is not None,
        probe_policy=old.probe_policy,
        repair_recheck=old.repair_recheck,
        repair_inspection_policy=old.repair_inspection_policy,
        planning_policy=old.planning_policy,
        context_policy=old.context_policy,
        segment_boundary_policy=old.segment_boundary_policy,
        completion_cost_policy=old.completion_cost_policy,
        **({key: getattr(old, key) for key in (
            "retained_source_chars", "evaluation_reserve_seconds", "probe_recheck",
            "max_correction_output_tokens", "reproduction_acquisition",
            "history_search_policy", "agent_policy",
        )} if preserve_parent_configuration else {}),
    )
    runtime_hash = runner._runtime_hash()
    model_hash = runner._model_hash(request, pricing)
    envelope = runner._run_envelope(
        request=request,
        task_dir=task_dir,
        package=package,
        run_id=source.run_id,
        runtime_hash=runtime_hash,
        model_hash=model_hash,
        cost_ledger=ledger,
        cost_start_nanos=old.cost_start_nanos,
        prepared_source_hash=old.prepared_source_hash,
        probe_dependencies=old.probe_dependencies,
    )
    journal.write_envelope(envelope)
    marker = {
        "mode": mode,
        "arm": arm,
        "parent": source.record(),
        "cut_sequence": cut_sequence,
        "parent_prefix_hash": prefix[-1]["event_hash"],
        "current_runtime_hash": runtime_hash,
        "diagnostic_implementation_hash": implementation_hash(),
        (
            "synthetic_new_cap_nanos" if mode == "offline-scripted-only" else "new_cap_nanos"
        ): ledger.cap_nanos - spent,
        "historical_funds_reopened": False,
        "inherited_events_are_not_new_execution": True,
        "historical_probe_receipts": [
            ref.model_dump(mode="json")
            for ref in runner._probe_evidence(view, store, source.run_id)
        ],
        "active_elapsed_ms": active_elapsed_ms,
    }
    if after_tool_batch:
        marker["after_tool_batch"] = True
        marker["remaining_budget"] = budget
        marker["baseline_failure_case_ids"] = obligation["baseline_failure_case_ids"]
    if preserve_parent_configuration:
        marker["preserve_parent_configuration"] = True
    if model_override is not None:
        marker["model_override"] = model_override
    if caller_override is not None:
        marker["caller_source_roots_override"] = caller_override
    journal.append("observation_exposure_fork", marker)
    branch = SimpleNamespace(
        root=output,
        store=store,
        journal=journal,
        references=references,
        source=source,
        arm=arm,
        request=request,
        envelope=envelope,
        package=package,
        task_dir=task_dir,
        ledger=ledger,
        pricing=pricing,
        workspace=workspace,
        inherited_events=len(prefix),
        marker_hash=sha256_json(marker),
        initial_spent_nanos=spent,
        after_tool_batch=after_tool_batch,
        remaining_budget=budget,
        active_elapsed_ms=active_elapsed_ms,
        latest_results=latest,
        original_obligation=obligation,
    )
    with inherited_reads(branch):
        runner._validate_recorded_continuations(journal.events(), store)
    (output / "fork.json").write_text(
        canonical_json({"marker": marker, "references": references}), encoding="utf-8"
    )
    return branch


@contextmanager
def current_probe_receipts(branch):
    """Keep parent receipts auditable without claiming they ran in this new environment."""
    original = runner._probe_evidence

    def package(journal, artifact_store, run_id):
        require(journal.path == branch.journal.path, "unexpected receipt journal")
        events = journal.events()
        marker = events[branch.inherited_events]
        require(
            marker["event_type"] == "observation_exposure_fork"
            and sha256_json(marker["payload"]) == branch.marker_hash
            and events[branch.inherited_events - 1]["event_hash"]
            == marker["payload"]["parent_prefix_hash"],
            "receipt lineage boundary changed",
        )
        historical = marker["payload"]["historical_probe_receipts"]
        for ref in historical:
            artifact_store.read_bytes(Artifact.model_validate(ref))
        current = original(
            SimpleNamespace(events=lambda: events[branch.inherited_events + 1 :]),
            artifact_store,
            run_id,
        )
        journal.append(
            "probe_receipt_lineage",
            {
                "parent": marker["payload"]["parent"],
                "parent_prefix_hash": marker["payload"]["parent_prefix_hash"],
                "historical_receipts": historical,
                "current_receipts": [ref.model_dump(mode="json") for ref in current],
                "historical_receipts_are_current_execution": False,
            },
        )
        return current

    with patch.object(runner, "_probe_evidence", package):
        yield


class SyntheticProbe:
    def __init__(self, envelope, outcomes, dependencies=None):
        self.envelope, self.outcomes = envelope, dict(outcomes)
        self.environment = dependencies.environment if dependencies else None
        self.calls = []

    def preflight(self, **_):
        return {
            "image_digest": self.envelope.probe_image_digest,
            "profile_hash": self.envelope.probe_profile_hash,
        }

    def run_probe(self, workspace, question, python_source, *, deadline, execution_identity):
        action_id = execution_identity["action_id"]
        require(action_id in self.outcomes, "no synthetic probe outcome declared")
        status = self.outcomes[action_id]
        require(status in {"passed", "failed"}, "invalid synthetic probe outcome")
        self.calls.append(action_id)
        policy = probe_execution_policy(
            effective_timeout_seconds=30, row_deadline_limited=False, cleanup_status="confirmed"
        )
        return {
            "status": status,
            "source_hash": sha256_bytes(python_source.encode()),
            "snapshot_hash": sha256_json({"synthetic": True}),
            **self.preflight(),
            "exit_code": int(status == "failed"),
            "stdout": "SYNTHETIC_PROBE_ONLY",
            "stderr": "",
            "timed_out": False,
            "cleanup_failed": False,
            "deadline_exhausted": False,
            "execution_policy": policy,
            "execution_policy_hash": sha256_json(policy),
        }


def rehearse(branch, client: ScriptedClient, *, probe_outcomes=None):
    """Single-use synthetic execution. Remote-task mutations/checks/finish are forbidden."""
    require(type(client) is ScriptedClient, "finite offline client required")
    require(branch.envelope.runtime_hash == runner._runtime_hash(), "fork runtime changed")
    current = branch.journal.events()[branch.inherited_events:]
    require(current[0]["event_type"] == "observation_exposure_fork", "fork boundary changed")
    marker = current[0]["payload"]
    require(sha256_json(marker) == branch.marker_hash, "fork binding changed")
    require(marker["mode"] == "offline-scripted-only", "funded branch is not a rehearsal")
    require(
        marker["diagnostic_implementation_hash"] == implementation_hash(),
        "diagnostic implementation changed",
    )
    require(
        not any(
            e["event_type"] == "observation_rehearsal_started" for e in current
        ),
        "rehearsal cannot be retried",
    )
    for batch in client.steps:
        for call in batch:
            require(call["name"] != "finish_task", "offline fork does not evaluate submissions")
            require(
                branch.package.public.repository.url.startswith("snapshot://")
                or call["name"] not in {"replace_text", "run_check"},
                "real-task repair/check execution is outside synthetic rehearsal",
            )
    branch.journal.append("observation_rehearsal_started", {"arm": branch.arm, "provider_calls": 0})
    probes = []

    def make_probe(**kwargs):
        obj = SyntheticProbe(branch.envelope, probe_outcomes or {}, **kwargs)
        probes.append(obj)
        return obj

    def offline_adapter(config, **_):
        return OpenAIResponsesAdapter(config, api_key="offline-unused", client=client)

    def no_network(*_, **__):
        raise ContractError("network forbidden in offline fork")

    with (
        inherited_reads(branch),
        exposure(branch.arm),
        patch("socket.socket.connect", no_network),
        patch.object(runner, "load_exact_openai_api_key", lambda _: "offline-unused"),
        patch.object(runner, "_live_source_preflight", lambda *a, **k: None),
        patch.object(runner, "_live_sandbox_preflight", lambda *a, **k: LocalSandbox()),
        patch.object(runner, "DockerProbeSandbox", make_probe),
        patch.object(runner, "OpenAIResponsesAdapter", offline_adapter),
        branch.journal.execution_lock(),
    ):
        result = runner._run_one_locked(
            request=branch.request,
            task_dir=branch.task_dir,
            package=branch.package,
            state_root=branch.root,
            pricing=branch.pricing,
            cost_ledger=branch.ledger,
            runtime_hash=branch.envelope.runtime_hash,
            model_hash=branch.envelope.model_hash,
            run_id=branch.journal.run_id,
            journal=branch.journal,
            envelope=branch.envelope,
            resuming=True,
        )
    receipt = {
        "result": result.public,
        "stop_remaining": result.stop_remaining,
        "synthetic_counts": len(client.counted),
        "synthetic_dispatches": len(client.created),
        "synthetic_probe_calls": [c for obj in probes for c in obj.calls],
        "provider_calls": 0,
        "billed_cost_nanos": 0,
        "agent_efficacy": "NOT_RUN",
    }
    branch.journal.append("observation_rehearsal_finished", receipt)
    return receipt
