"""Offline-only current-runtime forks and persistent observation exposure.

Synthetic SDK/probe results exercise the ordinary runner, not agent quality. No
credential or live dispatch entry point exists. Use separate processes for branches.
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
from diagnostics.cleanup_information_checkpoint import restore_candidate
from diagnostics.decision_sampler import require
from diagnostics.declaration_checkpoint import Source, disjoint
from patchloop.agent.model import OpenAIResponsesAdapter
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact
from patchloop.deadline import ExecutionDeadline
from patchloop.dev import runner
from patchloop.dev.contracts import DevRunRequest
from patchloop.dev.cost import DevCostLedger, pricing_for_model
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


def fork(source: Source, cut_sequence: int, output: Path, arm: str, *, synthetic_cap_usd: Decimal):
    """Copy a settled prefix; bind current runtime without changing the parent."""
    require(arm in {"A", "B"}, "unknown exposure arm")
    require(
        synthetic_cap_usd.is_finite() and synthetic_cap_usd > 0,
        "positive finite synthetic allowance required",
    )
    historical = DevJournal(source.root, source.run_id)
    for path, digest in (
        (historical.path, source.journal_hash),
        (historical.envelope_path, source.envelope_hash),
        (source.public_path, source.public_hash),
    ):
        require(sha256_bytes(path.read_bytes()) == digest, "source identity changed")
    events, old = historical.events(), historical.load_envelope()
    require(
        old.provider == "openai"
        and old.split == "dev-train"
        and old.context_policy == "segmented-v1"
        and old.compaction_contract is None,
        "only dev-train segmented checkpoints without compaction are supported",
    )
    cut = next((e for e in events if e["sequence"] == cut_sequence), None)
    require(
        cut is not None and cut["event_type"] == "model_input_prepared",
        "cut must precede a prepared model request",
    )
    prefix = [e for e in events if e["sequence"] < cut_sequence]
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
    parent_store = ArtifactStore(source.root / "artifacts")
    bundle = json.loads(
        parent_store.read_bytes(Artifact.model_validate(cut["payload"]["artifact"]))
    )
    context = json.loads(
        parent_store.read_bytes(Artifact.model_validate(bundle["turn"]["context_artifact"]))
    )
    budget = context["remaining_budget"]
    task_dir, package = runner._resolve_task_file(source.public_path)
    require(
        package.public_spec_hash == old.public_spec_hash
        and package.task_content_hash == old.task_content_hash,
        "task identity changed",
    )
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
        data = parent_store.read_bytes(ref)
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
        == context["current_diff"]["patch_hash"],
        "candidate differs from checkpoint",
    )
    counters = runner._restore_counters(journal)
    require(
        old.limits.max_model_calls - counters.model_calls == budget["model_calls"]
        and old.limits.max_tool_actions - counters.tool_actions == budget["tool_actions"]
        and old.limits.max_accepted_mutations - len(accepted) == budget["accepted_mutations"],
        "restored action allowances differ",
    )
    pricing = pricing_for_model("gpt-5.4-2026-03-05")
    spent = budget["cost"]["settled_usage"]
    ledger = DevCostLedger(Decimal(spent) / 10**9 + synthetic_cap_usd, pricing)
    ledger.restore_settled_usage(journal.provider_usage(), base_spent_nanos=old.cost_start_nanos)
    require(ledger.spent_nanos == spent, "historical billing differs")
    request = DevRunRequest(
        provider="openai",
        task=source.public_path,
        model="gpt-5.4-2026-03-05",
        reasoning_effort="xhigh",
        max_output_tokens=25000,
        env_file=output / "NO_CREDENTIAL_FILE",
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
        enable_probes=old.probe_image_digest is not None,
        probe_policy=old.probe_policy,
        repair_recheck=old.repair_recheck,
        repair_inspection_policy=old.repair_inspection_policy,
        planning_policy=old.planning_policy,
        context_policy=old.context_policy,
        segment_boundary_policy=old.segment_boundary_policy,
        completion_cost_policy=old.completion_cost_policy,
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
        "mode": "offline-scripted-only",
        "arm": arm,
        "parent": source.record(),
        "cut_sequence": cut_sequence,
        "parent_prefix_hash": prefix[-1]["event_hash"],
        "current_runtime_hash": runtime_hash,
        "diagnostic_implementation_hash": implementation_hash(),
        "synthetic_new_cap_nanos": ledger.cap_nanos - spent,
        "historical_funds_reopened": False,
        "inherited_events_are_not_new_execution": True,
        "active_elapsed_ms": int(bundle["turn"]["active_elapsed_ms"]),
    }
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
    )
    with inherited_reads(branch):
        runner._validate_recorded_continuations(journal.events(), store)
    (output / "fork.json").write_text(
        canonical_json({"marker": marker, "references": references}), encoding="utf-8"
    )
    return branch


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
    marker = next(
        e["payload"]
        for e in branch.journal.events()
        if e["event_type"] == "observation_exposure_fork"
    )
    require(sha256_json(marker) == branch.marker_hash, "fork binding changed")
    require(
        marker["diagnostic_implementation_hash"] == implementation_hash(),
        "diagnostic implementation changed",
    )
    require(
        not any(
            e["event_type"] == "observation_rehearsal_started" for e in branch.journal.events()
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
