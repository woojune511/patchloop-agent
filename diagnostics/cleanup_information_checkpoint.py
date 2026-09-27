"""First failed-check continuation with later raw observations of that same candidate."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import yaml

from diagnostics import caller_information
from diagnostics.decision_sampler import require
from diagnostics.declaration_checkpoint import Source, SourceStore, disjoint
from diagnostics.segmented_input_audit import verify_turn
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact, PublicTask
from patchloop.dev import runner
from patchloop.dev.state import DevJournal
from patchloop.repository import WorkspaceManager
from patchloop.runtime import repository_root, runtime_content_hash
from patchloop.util import canonical_json, sha256_bytes, sha256_json

SCHEMA = "cleanup-information-checkpoint-v1"


class ForkStore(SourceStore):
    """Read exact copied references from the source fork, never arbitrary old paths."""

    def __init__(self, root, events):
        super().__init__(root)
        self.references = {}
        for event in events:
            if event["event_type"] == "diagnostic_checkpoint_fork":
                self.references.update(event["payload"]["artifact_references"])

    def read_bytes(self, artifact):
        replacement = self.references.get(sha256_json(artifact.model_dump(mode="json")))
        if replacement is None:
            replacement = self.references.get(artifact.path)
        if replacement is not None:
            require(artifact.model_dump(mode="json") == replacement[0],
                    "inherited artifact metadata changed")
            copied = Artifact.model_validate(replacement[1])
            require((copied.content_hash, copied.size_bytes, copied.media_type)
                    == (artifact.content_hash, artifact.size_bytes, artifact.media_type),
                    "inherited artifact content changed")
            raw = super().read_bytes(copied)
            self.reads[artifact.path] = artifact.content_hash
            return raw
        return super().read_bytes(artifact)


def load(source: Source):
    """Select the first failed check's next input after one accepted mutation.

    Read only public records and native encrypted continuation artifacts. Future
    dispatch metadata binds A's identity, but future decisions never enter the pair.
    """
    path = source.root / "runs" / f"{source.run_id}.jsonl"
    for p, digest in ((path, source.journal_hash),
                      (path.with_suffix(".envelope.json"), source.envelope_hash),
                      (source.public_path, source.public_hash)):
        require(p.is_file() and sha256_bytes(p.read_bytes()) == digest, "source identity changed")
    journal = DevJournal(source.root, source.run_id)
    events, envelope = journal.events(), journal.load_envelope()
    require(envelope.runtime_hash == runtime_content_hash(), "source runtime changed")
    require(envelope.provider == "openai" and envelope.context_policy == "segmented-v1",
            "OpenAI segmented checkpoint required")
    public = PublicTask.model_validate(yaml.safe_load(
        source.public_path.read_text(encoding="utf-8")))
    require(public.split == "dev-train" and public.task_id == envelope.task_id
            and public.task_version == envelope.task_version, "public task identity changed")
    forks = [e for e in events if e["event_type"] == "diagnostic_checkpoint_fork"]
    require(len(forks) == 1, "one source fork required")
    actions = [e for e in events if e["sequence"] > forks[0]["sequence"]
               and e["event_type"] == "action_started"]
    require([e["payload"]["tool"] for e in actions[:2]] == ["replace_text", "run_check"],
            "first repair and check required")
    mutation, check = [e["payload"] for e in actions[:2]]
    accepted = next(e["payload"]["result"] for e in events
                    if e["event_type"] == "action_finished"
                    and e["payload"]["action_id"] == mutation["action_id"])
    require(accepted["error_code"] is None
            and accepted["input_hash"] == mutation["input_hash"]
            and accepted["output"]["mutation"]["diff_hash"]
            == mutation["mutation_expected_worktree_diff_hash"], "first mutation not accepted")
    finished = next(e for e in events if e["event_type"] == "action_finished"
                    and e["payload"]["action_id"] == check["action_id"])
    result = finished["payload"]["result"]
    require(result["error_code"] is None and result["output"]["passed"] is False
            and not result["output"]["cleanup_failed"]
            and result["output"]["diff_hash"] == mutation["mutation_expected_worktree_diff_hash"],
            "completed first failed check required")
    start = next(e for e in events if e["event_type"] == "turn_started"
                 and e["sequence"] > finished["sequence"])
    prefix = [e for e in events if e["sequence"] < start["sequence"]]
    require(len([e for e in prefix if e["event_type"] == "action_started"
                 and e["payload"]["tool"] == "replace_text"]) == 1,
            "exactly one historical mutation required")
    prefix_view = SimpleNamespace(events=lambda: prefix)
    require(DevJournal.unresolved_provider_call(prefix_view) is None
            and DevJournal.unresolved_input_count(prefix_view) is None,
            "uncertain source dispatch or count")
    usage = [e["payload"] for e in prefix if e["event_type"] == "provider_call_finished"]
    require(bool(usage) and all(type(u.get("cost_nanos")) is int and u["cost_nanos"] >= 0
                               and not u.get("error_code") for u in usage),
            "uncertain source billing")
    store = ForkStore(source.root, prefix)
    runner._validate_recorded_continuations(prefix, store)
    boundary = start["payload"]["prepared_input"]
    request = json.loads(store.read_bytes(Artifact.model_validate(boundary["artifact"])))[
        "request"]
    verified = verify_turn(start, events, store, actual_input=request["input"])
    counts = [e for e in prefix if e["event_type"] == "input_count_finished"
              and e["payload"].get("count_id") == start["payload"]["selected_count_id"]]
    dispatches = [e for e in events if e["event_type"] == "provider_call_started"
                  and e["payload"]["turn_id"] == start["payload"]["turn_id"]]
    require(len(counts) == len(dispatches) == 1, "unique count/dispatch binding required")
    count, dispatch = counts[0], dispatches[0]
    require(count["sequence"] < start["sequence"] < dispatch["sequence"]
            and sha256_json(request) == boundary["request_hash"]
            == count["payload"]["request_hash"] == dispatch["payload"]["request_hash"]
            == start["payload"]["counted_request_hash"]
            and count["payload"]["input_tokens"] == dispatch["payload"]["input_tokens"],
            "counted/dispatched checkpoint identity changed")
    require(request["model"] == envelope.model
            and request["reasoning"] == {"effort": envelope.reasoning_effort}
            and request["max_output_tokens"] == 25_000, "checkpoint model settings changed")
    state = json.loads(request["input"][-1]["content"])["state"]
    # Public task resides in the immutable seed in segmented inputs.
    context = json.loads(store.read_bytes(Artifact.model_validate(
        start["payload"]["context_artifact"])))
    require(context["public_task"] == public.model_dump(mode="json"), "public source mismatch")
    require(state["current_diff"]["patch_hash"] == mutation["mutation_expected_worktree_diff_hash"],
            "failed candidate differs from checkpoint")
    return SimpleNamespace(request=request, store=store, source=source, mutation=mutation, receipt={
        "source_turn_id": start["payload"]["turn_id"],
        "source_check_action_id": check["action_id"],
        "source_prefix_hash": prefix[-1]["event_hash"],
        "source_projection": verified, "historical_input_tokens": count["payload"]["input_tokens"],
        "historical_cost_nanos_before_boundary": sum(u["cost_nanos"] for u in usage),
        "remaining_budget": state["remaining_budget"],
    })



def restore_candidate(workspace, mutation):
    target = (workspace / mutation["mutation_target_path"]).resolve()
    require(target.is_relative_to(workspace.resolve()), "mutation target outside workspace")
    before = target.read_bytes()
    require(sha256_bytes(before) == mutation["mutation_preimage_file_hash"],
            "candidate preimage changed")
    args, newline = mutation["arguments"], mutation["mutation_preimage_newline"]
    old, new = (args[key].replace("\n", newline).encode() for key in ("old_text", "new_text"))
    require(before.count(old) == 1, "candidate anchor is not unique")
    after = before.replace(old, new, 1)
    require(sha256_bytes(after) == mutation["mutation_expected_postimage_file_hash"],
            "candidate postimage changed")
    target.write_bytes(after)
    require(WorkspaceManager.diff_summary(workspace).patch_hash
            == mutation["mutation_expected_worktree_diff_hash"], "candidate diff changed")


def observation(packet):
    """Allowlist only B1 original-candidate measurements, never rescue/other patches."""
    descriptor = packet["evidence"]
    path = Path(descriptor["path"])
    require(sha256_bytes(path.read_bytes()) == descriptor["hash"], "probe result changed")
    journal = DevJournal(path.parent, "run_dev_cleanupprobe")
    require(sha256_bytes(journal.path.read_bytes()) == descriptor["journal_hash"],
            "probe journal changed")
    events = journal.events()
    store = SourceStore(path.parent)
    result = json.loads(path.read_bytes())
    def read(ref):
        return store.read_bytes(Artifact.model_validate(ref))
    require(json.loads(read(events[-1]["payload"]["artifact"])) == result,
            "probe result binding changed")
    prepared = events[0]["payload"]
    loaded = load(Source.from_record(packet["source"]))
    envelope = DevJournal(loaded.source.root, loaded.source.run_id).load_envelope()
    require(prepared["remove_caller_cancel"] is False
            and result["remove_caller_cancel"] is False
            and prepared["mutations"]["B1"] == loaded.mutation
            and prepared["runtime_hash"] == envelope.runtime_hash,
            "observation is not the exact original first candidate")
    programs = {flag: read(ref).decode() for flag, ref in prepared["programs"].items()}
    program_path = Path(__file__).parent / "probes/anyio_cleanup_trace.py"
    require(programs == {str(flag): f"TRACE = {flag!r}\n" + program_path.read_text()
                         for flag in (False, True)}, "probe program changed")
    rows = [row for row in result["rows"] if row["row"] == "B1"]
    require([row["trace"] for row in rows] == [False, True], "two B1 observations required")
    selected = []
    for row in rows:
        receipt = json.loads(read(row["receipt"]))
        require(row["diff_hash"] == loaded.mutation["mutation_expected_worktree_diff_hash"]
                and receipt["source_hash"] == sha256_bytes(programs[str(row["trace"])].encode())
                and json.loads(receipt["stdout"]) == row["observation"]
                and receipt["status"] == "passed" and receipt["exit_code"] == 0
                and not any(receipt[k] for k in
                            ("cleanup_failed", "timed_out", "truncated", "deadline_exhausted"))
                and receipt["image_digest"] == envelope.probe_image_digest
                and receipt["profile_hash"] == envelope.probe_profile_hash
                and receipt["execution_policy"]["dependencies"]
                == envelope.probe_dependencies.model_dump(mode="json"),
                "probe receipt identity or execution differs")
        selected.append({"trace_enabled": row["trace"], "program": programs[str(row["trace"])],
                         "stdout": receipt["stdout"], "stderr": receipt["stderr"]})
    plain, traced = (row["observation"] for row in rows)
    require(plain["events"] == traced["events"] and plain["outcome"] == traced["outcome"]
            and plain["records"] == [r for r in traced["records"] if r["at"] != "source_line"],
            "traced and untraced boundary observations differ")
    return {"origin": "later_operator_measurement", "candidate_diff_hash": rows[0]["diff_hash"],
            "scope": "Same first candidate and pinned environment. Two operator executions.",
            "interpretation": "Source-line records occur before the line executes. "
            "diagnostic_watchdog_exit denotes the program's watchdog exit, not completed cleanup.",
            "measurements": selected}


def implementation_hashes():
    names = ("diagnostics/cleanup_information_checkpoint.py", ".agent/cleanup-information.md",
             "diagnostics/probes/anyio_cleanup_trace.py", "diagnostics/anyio_cleanup_probe.py")
    return {name: sha256_bytes((repository_root() / name).read_bytes()) for name in names}


def prepare(source, evidence, output):
    disjoint(output.resolve(), (repository_root(), source.root, source.public_path.parent,
                                Path(evidence["path"]).parent))
    loaded = load(source)
    packet = {"schema": SCHEMA, "official": False, "paid_execution_authorized": False,
              "source": source.record(), "evidence": evidence, "checkpoint": loaded.receipt,
              "runtime_hash": runtime_content_hash(),
              "implementation_hashes": implementation_hashes()}
    supplement = observation(packet)
    a, b = loaded.request, caller_information.project(loaded.request, supplement)
    packet["pair"] = {"A_request_hash": sha256_json(a), "B_request_hash": sha256_json(b)}
    packet["supplement_hash"] = sha256_json(supplement)
    output.mkdir()
    store = ArtifactStore(output / "artifacts")
    packet["requests"] = {arm: store.put_json(req).model_dump(mode="json")
                          for arm, req in (("A", a), ("B", b))}
    (output / "operator-supplement.json").write_text(canonical_json(supplement) + "\n")
    raw = (canonical_json(packet) + "\n").encode()
    (output / "packet.json").write_bytes(raw)
    digest = sha256_bytes(raw)
    DevJournal(output, "run_dev_cleanupinformationpreparation").append(
        "diagnostic_input_pair_prepared", {"packet_hash": digest, "model_calls": 0})
    return {"packet": str(output / "packet.json"), "packet_hash": digest}


def validate(path, digest):
    require(sha256_bytes(path.read_bytes()) == digest, "packet identity changed")
    packet = json.loads(path.read_bytes())
    require(packet["schema"] == SCHEMA and packet["paid_execution_authorized"] is False
            and packet["runtime_hash"] == runtime_content_hash()
            and packet["implementation_hashes"] == implementation_hashes(),
            "checkpoint implementation changed")
    loaded = load(Source.from_record(packet["source"]))
    supplement = observation(packet)
    require(loaded.receipt == packet["checkpoint"]
            and sha256_json(supplement) == packet["supplement_hash"], "checkpoint changed")
    store = SourceStore(path.parent)
    for arm, expected in (("A", loaded.request),
                          ("B", caller_information.project(loaded.request, supplement))):
        actual = json.loads(store.read_bytes(Artifact.model_validate(packet["requests"][arm])))
        require(actual == expected and sha256_json(actual) == packet["pair"][arm + "_request_hash"],
                "input pair changed")
    events = DevJournal(path.parent, "run_dev_cleanupinformationpreparation").events()
    require(len(events) == 1 and events[0]["payload"]["packet_hash"] == digest,
            "preparation binding changed")
    return {"verified": True, "model_calls": 0}
