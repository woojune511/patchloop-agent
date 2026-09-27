"""Provider-free checkpoint continuation through the ordinary registered-tool loop.

Scripted SDK responses test restoration and execution, not model quality. No live
entry point or credential argument is provided. Run one branch per process.
"""

from __future__ import annotations

import copy
import json
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from diagnostics import mutation_advice_checkpoint as checkpoint
from diagnostics.decision_sampler import require
from diagnostics.declaration_checkpoint import Source, disjoint
from patchloop.agent.model import OpenAIResponsesAdapter
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact
from patchloop.deadline import ExecutionDeadline
from patchloop.dev import native_compaction, runner
from patchloop.dev.contracts import DevRunRequest
from patchloop.dev.conversation import history_metadata
from patchloop.dev.cost import DevCostLedger, pricing_for_model
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError
from patchloop.repository import WorkspaceManager
from patchloop.runtime import repository_root
from patchloop.sandbox import LocalSandbox
from patchloop.util import canonical_json, sha256_json


def _artifacts(value):
    if isinstance(value, dict):
        if {"artifact_id", "content_hash", "size_bytes", "media_type", "path"} <= value.keys():
            yield Artifact.model_validate(value)
        else:
            for child in value.values():
                yield from _artifacts(child)
    elif isinstance(value, list):
        for child in value:
            yield from _artifacts(child)


@contextmanager
def inherited_reads(branch):
    """Resolve exact inherited references against copied bytes, never rewrite history."""
    original = ArtifactStore.read_bytes

    def read(store, artifact):
        replacement = branch.references.get(artifact.path)
        if replacement is not None and store.root.resolve() == branch.store.root.resolve():
            require(
                artifact.model_dump(mode="json") == replacement[0],
                "inherited artifact metadata changed",
            )
            return original(store, Artifact.model_validate(replacement[1]))
        return original(store, artifact)

    with patch.object(ArtifactStore, "read_bytes", read):
        yield


def restore(packet_path: Path, packet_hash: str, output: Path, arm: str):
    """Materialize a fresh baseline workspace and completed prefix; never replay probes."""
    require(arm in {"A", "B"}, "unknown checkpoint arm")
    checkpoint.validate(packet_path, packet_hash)
    packet = json.loads(packet_path.read_bytes())
    source = Source.from_record(packet["source"])
    output = output.resolve()
    disjoint(
        output, (repository_root(), source.root, packet_path.parent, source.public_path.parent)
    )
    loaded = checkpoint.load(source)
    historical = DevJournal(source.root, source.run_id)
    events, envelope = historical.events(), historical.load_envelope()
    start = next(
        e
        for e in events
        if e["event_type"] == "turn_started"
        and e["payload"]["turn_id"] == packet["checkpoint"]["source_turn_id"]
    )
    cutoff = max(
        e["sequence"]
        for e in events
        if e["event_type"] == "tool_batch_finished" and e["sequence"] < start["sequence"]
    )
    prefix = [e for e in events if e["sequence"] <= cutoff]
    bundle = json.loads(
        loaded.store.read_bytes(
            Artifact.model_validate(start["payload"]["prepared_input"]["artifact"])
        )
    )
    output.mkdir()
    store = ArtifactStore(output / "artifacts")
    references = {}
    pending = list(_artifacts([prefix, bundle]))
    while pending:
        ref = pending.pop()
        if ref.path in references:
            require(
                references[ref.path][0] == ref.model_dump(mode="json"),
                "ambiguous inherited artifact",
            )
            continue
        raw = loaded.store.read_bytes(ref)
        copied = store.put_bytes(raw, ref.media_type)
        references[ref.path] = (ref.model_dump(mode="json"), copied.model_dump(mode="json"))
        if ref.media_type.startswith("application/json"):
            pending.extend(_artifacts(json.loads(raw)))
    journal = DevJournal(output, source.run_id)
    with journal.path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write("".join(canonical_json(e) + "\n" for e in prefix))
    journal.write_envelope(envelope)
    fork = {
        "official": False,
        "mode": "offline-scripted",
        "arm": arm,
        "packet_hash": packet_hash,
        "source_journal_hash": source.journal_hash,
        "source_prefix_hash": prefix[-1]["event_hash"],
        "inherited_event_count": len(prefix),
        "historical_execution_is_not_new_execution": True,
        "active_elapsed_ms": start["payload"]["active_elapsed_ms"],
        "artifact_references": references,
    }
    journal.append("diagnostic_checkpoint_fork", fork)
    task_dir, package = runner._resolve_task_file(source.public_path)
    require(
        package.public_spec_hash == envelope.public_spec_hash
        and package.task_content_hash == envelope.task_content_hash,
        "task package changed since checkpoint",
    )
    manager = WorkspaceManager(
        repository_root() / "fixtures/repositories",
        output / "workspaces",
        prepared_source=Path(envelope.prepared_source_path)
        if envelope.prepared_source_path
        else None,
        prepared_source_hash=envelope.prepared_source_hash,
    )
    require(
        envelope.prepared_source_path is not None
        or package.public.repository.url.startswith("snapshot://"),
        "offline restoration requires a prepared source or local fixture",
    )
    workspace = manager.create(
        source.run_id,
        package.public.repository.url,
        package.public.repository.base_commit,
        deadline=ExecutionDeadline.from_remaining(120),
    )
    runner._validate_resumed_workspace(workspace, journal)
    request = DevRunRequest(
        provider="openai",
        task=source.public_path,
        model=envelope.model,
        reasoning_effort=envelope.reasoning_effort,
        max_output_tokens=envelope.max_output_tokens,
        env_file=output / "NO_CREDENTIAL_FILE",
        max_cost_usd=Decimal(envelope.max_cost_nanos) / 10**9,
        state_root=output,
        resume_run_id=source.run_id,
        limits=envelope.limits,
        prepared_source=manager.prepared_source,
        prepared_probe_dependencies=(
            Path(envelope.prepared_probe_dependencies_path)
            if envelope.prepared_probe_dependencies_path
            else None
        ),
        enable_probes=envelope.probe_image_digest is not None,
        **{
            k: getattr(envelope, k)
            for k in (
                "repair_recheck",
                "repair_inspection_policy",
                "planning_policy",
                "probe_policy",
                "context_policy",
                "segment_boundary_policy",
                "completion_cost_policy",
            )
        },
    )
    pricing = pricing_for_model(envelope.model)
    ledger = DevCostLedger(request.max_cost_usd, pricing)
    ledger.restore_settled_usage(
        journal.provider_usage(), base_spent_nanos=envelope.cost_start_nanos
    )
    counters = runner._restore_counters(journal)
    remaining = packet["checkpoint"]["remaining_budget"]
    require(
        ledger.remaining_nanos == remaining["cost"]["remaining"]
        and ledger.spent_nanos == remaining["cost"]["settled_usage"]
        and request.limits.max_model_calls - counters.model_calls == remaining["model_calls"]
        and request.limits.max_tool_actions - counters.tool_actions == remaining["tool_actions"],
        "restored allowances differ from checkpoint",
    )
    selected = copy.deepcopy(loaded.request if arm == "A" else checkpoint.project(loaded.request))
    bundle["request"] = selected
    turn = bundle["turn"]
    turn["model_input_artifact"] = native_compaction.put_json(store, selected["input"])
    turn["model_input_hash"] = turn["model_input_artifact"]["content_hash"]
    turn["native_history"] = history_metadata(selected["input"], context_policy="segmented-v1")
    canonical = json.loads(
        loaded.store.read_bytes(Artifact.model_validate(turn["context_artifact"]))
    )
    if arm == "B":
        canonical["completion_guidance"].update(next_action=None, message=checkpoint.FACTUAL)
    turn["context_artifact"] = native_compaction.put_json(store, canonical)
    turn["context_hash"] = turn["context_artifact"]["content_hash"]
    journal.append(
        "model_input_prepared",
        {
            "boundary_id": turn["turn_id"],
            "cursor": native_compaction.cursor(journal),
            "artifact": native_compaction.put_json(store, bundle),
            "request_hash": sha256_json(selected),
        },
    )
    branch = SimpleNamespace(
        root=output,
        store=store,
        journal=journal,
        references=references,
        envelope=envelope,
        request=request,
        package=package,
        task_dir=task_dir,
        ledger=ledger,
        pricing=pricing,
        packet=packet,
        selected=selected,
        original=loaded.request,
        inherited_events=len(prefix),
        initial_spent_nanos=ledger.spent_nanos,
    )
    with inherited_reads(branch):
        runner._validate_recorded_continuations(journal.events(), store)
        runner._load_active_model_input(turn, store, context_policy="segmented-v1")
    return branch


class ScriptedClient:
    """Finite synthetic SDK responses; counts and charges are simulated."""

    max_retries = 0

    def __init__(self, steps, *, input_tokens=100, failure=None):
        self.steps = copy.deepcopy(steps)
        self.input_tokens, self.failure = input_tokens, failure
        self.counted, self.created = [], []
        self.responses = SimpleNamespace(
            input_tokens=SimpleNamespace(count=self.count), create=self.create
        )

    def count(self, **request):
        self.counted.append(copy.deepcopy(request))
        if self.failure == "count":
            raise TimeoutError("synthetic count failure")
        return SimpleNamespace(input_tokens=self.input_tokens)

    def create(self, **request):
        self.created.append(copy.deepcopy(request))
        if self.failure == "transport":
            raise TimeoutError("synthetic transport failure")
        require(bool(self.steps), "offline script exhausted")
        number = len(self.created)
        calls = self.steps.pop(0)
        output = [
            SimpleNamespace(
                type="reasoning",
                id=f"offline_reasoning_{number}",
                encrypted_content=f"synthetic_cipher_{number}",
                summary=[],
                status="completed",
            )
        ]
        output.extend(
            SimpleNamespace(
                type="function_call",
                name=call["name"],
                call_id=call["action_id"],
                arguments=canonical_json(call["arguments"]),
            )
            for call in calls
        )
        return SimpleNamespace(
            id=f"offline_response_{number}",
            model=request["model"],
            status="completed",
            incomplete_details=None,
            output=output,
            usage=None
            if self.failure == "usage"
            else SimpleNamespace(
                input_tokens=self.input_tokens,
                input_tokens_details=SimpleNamespace(cached_tokens=0),
                output_tokens=20,
                output_tokens_details=SimpleNamespace(reasoning_tokens=1),
            ),
        )


class UnexecutedProbe:
    """Preserve schema/environment identity; no historical or new probe execution."""

    def __init__(self, envelope, dependencies=None):
        self.envelope = envelope
        self.environment = dependencies.environment if dependencies else None

    def preflight(self, **kwargs):
        return {
            "image_digest": self.envelope.probe_image_digest,
            "profile_hash": self.envelope.probe_profile_hash,
        }

    def run_probe(self, *args, **kwargs):
        raise ContractError("offline continuation does not execute probes")


def rehearse(branch, client: ScriptedClient):
    """Run one offline branch with local checks and the ordinary isolated evaluator."""
    require(type(client) is ScriptedClient, "finite offline client required")
    require(
        not any(e["event_type"] == "diagnostic_rehearsal_started" for e in branch.journal.events()),
        "rehearsal cannot be retried",
    )
    branch.journal.append("diagnostic_rehearsal_started", {"mode": "offline-scripted"})
    original_prepare = native_compaction.prepared_input
    original_manifest = runner._manifest
    first = []

    def prepare(journal, store, turn, request, transition):
        if not first:
            normalized = copy.deepcopy(request)
            view = json.loads(normalized["input"][-1]["content"])
            old = json.loads(branch.original["input"][-1]["content"])
            view["state"]["remaining_budget"]["active_wall_time_seconds"] = old["state"][
                "remaining_budget"
            ]["active_wall_time_seconds"]
            normalized["input"][-1]["content"] = canonical_json(view)
            require(
                normalized == branch.original, "restored first state differs beyond elapsed time"
            )
            first.append(True)
        return original_prepare(journal, store, turn, request, transition)

    def offline_adapter(config, **kwargs):
        return OpenAIResponsesAdapter(config, api_key="offline-no-credential", client=client)

    def offline_manifest(**kwargs):
        # The adapter exercises OpenAI's wire grammar; evaluation really runs locally.
        kwargs["sandbox_backend"] = "local"
        manifest = original_manifest(**kwargs)
        local_identity = runner._sandbox_identity_hash(
            kwargs["request"].model_copy(update={"provider": "mock"}),
            kwargs["package"],
            kwargs.get("probe_dependencies"),
        )
        return manifest.model_copy(update={"sandbox_identity_hash": local_identity})

    def no_network(*args, **kwargs):
        raise ContractError("network is forbidden in offline continuation")

    with (
        inherited_reads(branch),
        patch("socket.socket.connect", no_network),
        patch.object(runner, "load_exact_openai_api_key", lambda _: "offline-no-credential"),
        patch.object(runner, "_live_source_preflight", lambda *a, **kw: None),
        patch.object(runner, "_live_sandbox_preflight", lambda *a, **kw: LocalSandbox()),
        patch.object(
            runner, "DockerProbeSandbox", lambda **kw: UnexecutedProbe(branch.envelope, **kw)
        ),
        patch.object(runner, "OpenAIResponsesAdapter", offline_adapter),
        patch.object(runner, "_manifest", offline_manifest),
        patch.object(native_compaction, "prepared_input", prepare),
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
    billing_known = (
        branch.journal.unresolved_provider_call() is None
        and runner._provider_usage_failure(branch.journal) is None
    )
    receipt = {
        "official": False,
        "mode": "offline-scripted",
        "live_model_calls": 0,
        "new_billed_cost_nanos": 0,
        "simulated_calls": len(client.created),
        "simulated_counts": len(client.counted),
        "source_settled_nanos": branch.initial_spent_nanos,
        "simulated_billing_known": billing_known,
        "simulated_new_cost_nanos": (
            branch.ledger.spent_nanos - branch.initial_spent_nanos if billing_known else None
        ),
        "result": result.public,
        "stop_remaining": result.stop_remaining,
        "first_state_restored": bool(first),
        "agent_efficacy": "NOT_RUN",
        "docker_safety": "NOT_RUN",
        "historical_probe_replayed": False,
    }
    branch.journal.append("diagnostic_rehearsal_finished", receipt)
    return receipt
