"""Rebuild the first post-search decision, retaining the original native continuation.

Only registered historical searches execute. No selected model action, project code,
provider, credential, Docker or evaluator is accessed by this module.
"""
from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import yaml

from diagnostics import decision_sampler as shared
from diagnostics import declaration_context as expansion
from diagnostics.segmented_input_audit import verify_turn
from patchloop.agent.model import OpenAIResponsesAdapter
from patchloop.contracts import Artifact, PublicTask
from patchloop.deadline import ExecutionDeadline
from patchloop.dev import runner, segments
from patchloop.dev.contracts import RequestedTool
from patchloop.dev.conversation import reconstruct_state
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import DevToolGateway, dev_tool_schemas
from patchloop.prepared_probe_dependencies import PreparedDependencies, read_descriptor
from patchloop.prepared_source import load_source
from patchloop.runtime import repository_root, runtime_content_hash
from patchloop.util import canonical_json, sha256_bytes, sha256_json

require = shared.require
DERIVED_CONTEXT = frozenset({
    "context_projection", "evidence_ledger", "latest_tool_results", "observed_source_index",
    "source_spans", "recent_attempt_result_next_question",
})


@dataclass(frozen=True)
class Source:
    root: Path
    run_id: str
    journal_hash: str
    envelope_hash: str
    public_path: Path
    public_hash: str

    def record(self):
        return {k: str(v) if isinstance(v, Path) else v for k, v in vars(self).items()}

    @classmethod
    def from_record(cls, record):
        return cls(**{k: Path(v) if k in {"root", "public_path"} else v
                      for k, v in record.items()})


class SourceStore:
    """Verify every inherited CAS read without creating or changing the source store."""

    def __init__(self, root):
        self.root, self.reads = root, {}

    def read_bytes(self, artifact):
        raw = shared.read_source_artifact(self.root, artifact.model_dump(mode="json"))
        self.reads[artifact.path] = artifact.content_hash
        return raw


def disjoint(root, protected):
    root = root.resolve()
    require(not root.exists() and root.parent.is_dir(), "fresh output root required")
    require(all(not root.is_relative_to(p.resolve()) and not p.resolve().is_relative_to(root)
                for p in protected), "output overlaps protected source")


def load(source: Source):
    path = source.root / "runs" / f"{source.run_id}.jsonl"
    envelope_path = path.with_suffix(".envelope.json")
    for p, digest in ((path, source.journal_hash), (envelope_path, source.envelope_hash),
                      (source.public_path, source.public_hash)):
        require(p.is_file() and sha256_bytes(p.read_bytes()) == digest, "source identity changed")
    journal = DevJournal(source.root, source.run_id)
    events, envelope = journal.events(), journal.load_envelope()
    require(envelope.runtime_hash == runtime_content_hash(), "source runtime changed")
    require(envelope.provider == "openai" and envelope.context_policy == segments.POLICY,
            "an OpenAI segmented checkpoint is required")
    require(envelope.probe_policy == "none" and envelope.compaction_contract is None
            and envelope.repair_inspection_policy == "protected-v1"
            and envelope.completion_cost_policy == "per-call-v1"
            and envelope.segment_boundary_policy == segments.DEFAULT_BOUNDARY_POLICY,
            "unsupported checkpoint policy")
    public = PublicTask.model_validate(yaml.safe_load(
        source.public_path.read_text(encoding="utf-8")))
    require(public.split == "dev-train" and public.task_id == envelope.task_id
            and public.task_version == envelope.task_version, "public task identity changed")
    starts = [e for e in events if e["event_type"] == "turn_started"]
    require(len(starts) >= 2, "first post-search decision is absent")
    start = starts[1]
    prefix = [e for e in events if e["sequence"] < start["sequence"]]
    prefix_view = SimpleNamespace(events=lambda: prefix)
    require(DevJournal.unresolved_provider_call(prefix_view) is None
            and DevJournal.unresolved_input_count(prefix_view) is None,
            "uncertain source dispatch or count")
    usage = [e["payload"] for e in prefix if e["event_type"] == "provider_call_finished"]
    require(len(usage) == 1 and type(usage[0].get("cost_nanos")) is int
            and usage[0]["cost_nanos"] >= 0 and not usage[0].get("error_code"),
            "uncertain source billing")
    decisions = [e for e in prefix if e["event_type"] == "turn_decision_recorded"]
    batches = [e for e in prefix if e["event_type"] == "tool_batch_finished"]
    require(len(decisions) == len(batches) == 1, "one completed initial batch required")
    decision, batch = decisions[0]["payload"], batches[0]["payload"]
    calls = [RequestedTool.model_validate(c) for c in decision["tool_calls"]]
    require(1 <= len(calls) <= 4 and all(c.name == "search_files" for c in calls)
            and not decision.get("error_code") and not decision.get("incomplete_reason")
            and decision["turn_id"] == batch["turn_id"] == starts[0]["payload"]["turn_id"],
            "only a valid first search batch can be replayed")
    finished = [e for e in prefix if e["event_type"] == "action_finished"]
    require(len(finished) == len(calls)
            and {e["payload"]["action_id"] for e in finished} == {c.action_id for c in calls}
            and batch["action_ids"] == [c.action_id for c in calls]
            and all(e["payload"]["result"]["status"] == "succeeded" for e in finished),
            "incomplete or failed source searches")
    store = SourceStore(source.root)
    verified = verify_turn(start, events, store)
    require(verified["verified"], "source input projection mismatch")
    runner._validate_recorded_continuations(prefix, store)
    context = json.loads(store.read_bytes(
        Artifact.model_validate(start["payload"]["context_artifact"])))
    require(context["public_task"] == public.model_dump(mode="json")
            and not context["current_diff"]["patch"]
            and not context["current_diff"]["untracked_files"], "initial public state mismatch")
    boundary = start["payload"]["prepared_input"]
    bundle = json.loads(store.read_bytes(Artifact.model_validate(boundary["artifact"])))
    request = bundle["request"]
    counted = next(e for e in prefix if e["event_type"] == "input_count_finished"
                   and e["payload"].get("count_id") == start["payload"]["selected_count_id"])
    dispatch = next(e for e in events if e["event_type"] == "provider_call_started"
                    and e["payload"]["turn_id"] == start["payload"]["turn_id"])
    require(counted["sequence"] < start["sequence"] < dispatch["sequence"]
            and sha256_json(request) == boundary["request_hash"]
            == counted["payload"]["request_hash"] == dispatch["payload"]["request_hash"]
            == start["payload"]["counted_request_hash"]
            and counted["payload"]["input_tokens"] == dispatch["payload"]["input_tokens"],
            "counted/dispatched checkpoint identity changed")
    require(request["max_output_tokens"] == shared.OUTPUT_CEILING
            and request["model"] == envelope.model
            and request["reasoning"] == {"effort": envelope.reasoning_effort},
            "checkpoint model settings changed")
    probe_environment = None
    if envelope.prepared_probe_dependencies_path is not None:
        dep_path = Path(envelope.prepared_probe_dependencies_path)
        descriptor, identity = read_descriptor(dep_path)
        require(identity == envelope.probe_dependencies, "dependency descriptor changed")
        # Schema metadata only: no wheel installation, imports or Docker preflight.
        from patchloop import probe_project_files

        probe_environment = PreparedDependencies(
            dep_path, identity, public.repository.url, public.repository.base_commit,
            tuple(probe_project_files.records(descriptor)),
        ).environment
    schemas = dev_tool_schemas(
        finish_enabled="finish_task" in start["payload"]["available_tool_names"],
        check_ids=context["remaining_visible_check_ids"],
        allowed_tools=start["payload"]["available_tool_names"],
        read_paths=start["payload"]["targeted_read_paths"],
        planning_policy=envelope.planning_policy,
        probe_policy=envelope.probe_policy, probe_environment=probe_environment,
    )
    ordered = OpenAIResponsesAdapter.request_payload(
        SimpleNamespace(config=shared.model_config(envelope.reasoning_effort, envelope.model)),
        request["input"], schemas, system_prompt=runner.DEV_SYSTEM_PROMPT,
    )
    ordered.update(parallel_tool_calls=True, tool_choice="required")
    require(ordered == request, "current schema/prompt/request builder differs")
    require(envelope.prepared_source_path is not None, "prepared source is required")
    return SimpleNamespace(source=source, events=events, prefix=prefix, envelope=envelope,
                           public=public, store=store, context=context, request=ordered,
                           start=start, calls=calls, finished=finished, batch=batch,
                           historical_count=counted["payload"]["input_tokens"])


def rebuild(loaded, output: Path):
    """Recompute source-dependent state through the ordinary gateway and input builder."""
    source, envelope = loaded.source, loaded.envelope
    manifest = Path(envelope.prepared_source_path)
    disjoint(output, (repository_root(), source.root, manifest.parent, source.public_path.parent))
    deadline = ExecutionDeadline.from_remaining(120)
    _, workspace = load_source(manifest, loaded.public.repository.url,
                               loaded.public.repository.base_commit,
                               expected_hash=envelope.prepared_source_hash, deadline=deadline)
    output.mkdir()
    requests, contexts, receipts = {}, {}, {}
    first_finish = loaded.finished[0]["sequence"]
    # Preserve all prior inputs, decisions, plan, notes and admitted search identities.
    inherited = loaded.events[:first_finish - 1]
    original_results = {e["payload"]["action_id"]: e["payload"]["result"]
                        for e in loaded.finished}
    calls = {c.action_id: c for c in loaded.calls}

    class Expanded(DevToolGateway):
        def _search_files(self, query, path_glob="**/*"):
            original = super()._search_files(query, path_glob)
            expanded, receipt = expansion.expand_search_result(
                original, lambda p: self._tracked_path(p)[1].read_bytes())
            receipts.setdefault("expansions", []).append(receipt)
            return expanded

    for arm, cls in (("A", DevToolGateway), ("B", Expanded)):
        journal = DevJournal(output / arm, source.run_id)
        with journal.path.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write("".join(canonical_json(e) + "\n" for e in inherited))
        journal.append("diagnostic_checkpoint_fork", {
            "official": False, "arm": arm, "source_journal_hash": source.journal_hash,
            "source_prefix_hash": inherited[-1]["event_hash"],
            "inherited_events_are_not_new_execution": True,
            "only_historical_searches_execute": True,
        })
        gateway = cls(workspace=workspace, public_task=loaded.public, sandbox=None,
                      journal=journal, limits=envelope.limits, deadline=deadline,
                      probe_sandbox=SimpleNamespace() if envelope.probe_image_digest else None)
        results = {}
        # Recorded completion order owns evidence ordering, not thread scheduling today.
        for event in loaded.finished:
            action_id = event["payload"]["action_id"]
            result = gateway.execute(calls[action_id])
            require(result.status == "succeeded", "replayed search failed")
            if arm == "A":
                require(result.model_dump(mode="json") == original_results[action_id],
                        "baseline search result differs from source")
            results[action_id] = result
        latest = [results[c.action_id] for c in loaded.calls]
        runner._record_tool_batch(journal=journal, gateway=gateway,
                                  turn_id=loaded.batch["turn_id"], calls=loaded.calls,
                                  results=latest,
                                  active_elapsed_ms=loaded.batch["active_elapsed_ms"])
        counters = runner._restore_counters(journal)
        projection = gateway.prepare_context_projection(latest_results=latest)
        snapshot = gateway.state_snapshot(projection=projection)
        policy = runner._tool_policy(gateway, counters, envelope.limits, snapshot=snapshot)
        context = json.loads(runner._build_context(
            package=SimpleNamespace(public=loaded.public), gateway=gateway, journal=journal,
            correction=None, latest_tool_results=latest, counters=counters,
            elapsed_seconds=(envelope.limits.wall_time_seconds
                             - loaded.context["remaining_budget"]["active_wall_time_seconds"]),
            limits=envelope.limits, policy=policy, snapshot=snapshot, projection=projection,
            tool_policy_transition=runner._tool_policy_transition(journal, policy),
            repair_recheck=envelope.repair_recheck, planning_policy=envelope.planning_policy,
        ))
        context["remaining_budget"]["cost"] = copy.deepcopy(
            loaded.context["remaining_budget"]["cost"])
        if arm == "A":
            different = [k for k in set(context) | set(loaded.context)
                         if context.get(k) != loaded.context.get(k)]
            require(not different, "baseline canonical state differs: " + ", ".join(different))
        contexts[arm] = context
        items = runner._build_model_input(
            journal=journal, artifact_store=loaded.store, context=canonical_json(context),
            latest_tool_results=latest, context_policy=segments.POLICY,
            planning_policy=envelope.planning_policy,
        )
        # CAS retains body strings exactly but canonicalizes item dictionary keys.
        # Keep that saved item order in both arms; only schema order is rebuilt by
        # the pinned runtime. This is not a claim about uncaptured HTTP wire bytes.
        saved_items = loaded.request["input"]
        require(len(items) == len(saved_items)
                and all(set(a) == set(b) for a, b in zip(items, saved_items, strict=True)),
                "native item shape changed")
        items = [{key: item[key] for key in old}
                 for item, old in zip(items, saved_items, strict=True)]
        requests[arm] = {**loaded.request, "input": items}
        if arm == "A":
            require(requests[arm] == loaded.request, "baseline native request differs")
        state = reconstruct_state(items, context_policy=segments.POLICY)
        require(state.get("working_plan") == reconstruct_state(
            loaded.request["input"], context_policy=segments.POLICY).get("working_plan"),
            "first plan changed")
    changed = [k for k in set(contexts["A"]) | set(contexts["B"])
               if contexts["A"].get(k) != contexts["B"].get(k)]
    require(set(changed) <= DERIVED_CONTEXT, "intervention changed unrelated state")
    for kind in ("reasoning", "function_call"):
        rows = [[i for i in requests[a]["input"] if i.get("type") == kind] for a in ("A", "B")]
        require(rows[0] == rows[1], "original continuation or calls changed")
    require(requests["A"]["input"][:3] == requests["B"]["input"][:3], "native seed changed")
    require(requests["A"] != requests["B"],
            "no declaration context intervention at this checkpoint")
    for path, digest in loaded.store.reads.items():
        require(sha256_bytes(Path(path).read_bytes()) == digest, "inherited artifact changed")
    require(sha256_bytes((source.root / "runs" / f"{source.run_id}.jsonl").read_bytes())
            == source.journal_hash, "historical journal changed")
    _, _ = load_source(manifest, loaded.public.repository.url, loaded.public.repository.base_commit,
                       expected_hash=envelope.prepared_source_hash, deadline=deadline)
    return requests, {"changed_context_fields": sorted(changed), **receipts,
                      "inherited_artifacts": dict(loaded.store.reads),
                      "original_request_exact": True, "native_reasoning_unchanged": True,
                      "first_plan_unchanged": True, "replayed_searches": 2 * len(loaded.calls)}
