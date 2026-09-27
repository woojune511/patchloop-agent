"""Offline matched inputs before a selected public probe-driven decision."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import yaml

from diagnostics.cleanup_information_checkpoint import ForkStore
from diagnostics.decision_sampler import require
from diagnostics.declaration_checkpoint import Source, disjoint
from diagnostics.segmented_input_audit import verify_turn
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact, PublicTask
from patchloop.dev.state import DevJournal
from patchloop.runtime import repository_root, runtime_content_hash
from patchloop.util import canonical_json, sha256_bytes, sha256_json

SCHEMA = "post-check-extension-v1"
EXTRA_SECONDS = 3600


def project(request):
    selected = copy.deepcopy(request)
    view = json.loads(selected["input"][-1]["content"])
    view["state"]["remaining_budget"]["active_wall_time_seconds"] += EXTRA_SECONDS
    selected["input"][-1]["content"] = canonical_json(view)
    return selected


def load(source: Source, turn_id: str):
    journal = DevJournal(source.root, source.run_id)
    for path, digest in (
        (journal.path, source.journal_hash),
        (journal.envelope_path, source.envelope_hash),
        (source.public_path, source.public_hash),
    ):
        require(sha256_bytes(path.read_bytes()) == digest, "source identity changed")
    events, envelope = journal.events(), journal.load_envelope()
    require(
        envelope.runtime_hash == runtime_content_hash()
        and envelope.context_policy == "segmented-v1",
        "source runtime changed",
    )
    public = PublicTask.model_validate(
        yaml.safe_load(source.public_path.read_text(encoding="utf-8"))
    )
    require(
        public.split == "dev-train" and public.task_id == envelope.task_id,
        "dev-train source required",
    )
    turn = next(
        e
        for e in events
        if e["event_type"] == "turn_started" and e["payload"]["turn_id"] == turn_id
    )
    count = next(
        e
        for e in events
        if e["event_type"] == "input_count_started" and e["payload"]["turn_id"] == turn_id
    )
    prefix = [e for e in events if e["sequence"] < count["sequence"]]
    reader = ForkStore(source.root, prefix)
    prepared = turn["payload"]["prepared_input"]
    request = json.loads(reader.read_bytes(Artifact.model_validate(prepared["artifact"])))[
        "request"
    ]
    require(sha256_json(request) == prepared["request_hash"], "prepared request changed")
    context = json.loads(
        reader.read_bytes(Artifact.model_validate(turn["payload"]["context_artifact"]))
    )
    require(context["public_task"] == public.model_dump(mode="json"), "public task changed")
    require(request["model"] == envelope.model, "model identity changed")
    observed = next(e for e in reversed(prefix) if e["event_type"] == "action_finished")
    require(observed["payload"]["result"]["tool"] == "run_check", "post-check boundary required")
    require(
        not any(
            e["event_type"] == "action_started" and e["sequence"] > observed["sequence"]
            for e in prefix
        ),
        "intervening action before checkpoint",
    )
    require(observed["payload"]["result"]["output"]["passed"] is True,
            "last check must pass")
    view = type("Prefix", (), {"events": lambda self: prefix})()
    require(DevJournal.unresolved_provider_call(view) is None
            and DevJournal.unresolved_input_count(view) is None, "uncertain prefix")
    uncertain = journal.unresolved_provider_call()
    require(uncertain is not None and uncertain["turn_id"] == turn_id,
            "selected turn must be the unresolved source dispatch")
    require(not any(e["event_type"] in ("action_started", "provider_call_finished")
                    for e in events if e["sequence"] >= count["sequence"]),
            "source executed beyond selected boundary")
    verified = verify_turn(turn, events, reader, actual_input=request["input"])
    receipt = {
        "turn_id": turn_id,
        "cutoff_sequence": prefix[-1]["sequence"],
        "prefix_hash": prefix[-1]["event_hash"],
        "check_action_id": observed["payload"]["action_id"],
        "delivery": verified,
        "request_hash": sha256_json(request),
        "source_unknown_call": {k: uncertain[k] for k in ("call_id", "turn_id", "request_hash")},
        "source_wall_time_seconds": envelope.limits.wall_time_seconds,
    }
    return request, receipt


def prepare(source: Source, turn_id: str, output: Path):
    disjoint(output.resolve(), (repository_root(), source.root, source.public_path.parent))
    control, receipt = load(source, turn_id)
    treatment = project(control)
    output.mkdir()
    store = ArtifactStore(output / "artifacts")
    packet = {
        "schema": SCHEMA,
        "official": False,
        "paid_execution_authorized": False,
        "execution_status": "NOT_RUN",
        "source": source.record(),
        "checkpoint": receipt,
        "runtime_hash": runtime_content_hash(),
        "implementation_hash": sha256_bytes(Path(__file__).read_bytes()),
        "extra_seconds": EXTRA_SECONDS,
        "control": store.put_json(control).model_dump(mode="json"),
        "treatment": store.put_json(treatment).model_dump(mode="json"),
        "control_hash": sha256_json(control),
        "treatment_hash": sha256_json(treatment),
    }
    raw = (canonical_json(packet) + "\n").encode()
    (output / "packet.json").write_bytes(raw)
    digest = sha256_bytes(raw)
    DevJournal(output, "run_dev_timeextensionpreparation").append(
        "offline_pair_prepared", {"packet_hash": digest, "provider_calls": 0}
    )
    return {"packet": str(output / "packet.json"), "packet_hash": digest}


def validate(path: Path, digest: str):
    require(sha256_bytes(path.read_bytes()) == digest, "packet identity changed")
    packet = json.loads(path.read_bytes())
    require(
        packet["schema"] == SCHEMA
        and packet["paid_execution_authorized"] is False
        and packet["execution_status"] == "NOT_RUN"
        and packet["extra_seconds"] == EXTRA_SECONDS
        and packet["runtime_hash"] == runtime_content_hash()
        and packet["implementation_hash"] == sha256_bytes(Path(__file__).read_bytes()),
        "offline contract changed",
    )
    control, receipt = load(Source.from_record(packet["source"]), packet["checkpoint"]["turn_id"])
    require(receipt == packet["checkpoint"], "checkpoint changed")
    store = ArtifactStore(path.parent / "artifacts")
    for key, expected in (("control", control), ("treatment", project(control))):
        actual = json.loads(store.read_bytes(Artifact.model_validate(packet[key])))
        require(actual == expected and sha256_json(actual) == packet[key + "_hash"], "pair changed")
    events = DevJournal(path.parent, "run_dev_timeextensionpreparation").events()
    require(
        len(events) == 1 and events[0]["payload"]["packet_hash"] == digest,
        "preparation binding changed",
    )
    return {"verified": True, "provider_calls": 0, "execution_status": "NOT_RUN"}
