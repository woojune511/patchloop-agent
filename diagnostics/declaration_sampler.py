"""Frozen post-search A/B decisions using the existing bounded one-response collector.

prepare/validate use local public source only. collect requires an exact fresh grant.
Sampled actions are never executed or chained; task acceptance stays NOT_RUN.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path
from time import monotonic

from diagnostics import decision_sampler as shared
from diagnostics import declaration_checkpoint as checkpoint
from diagnostics import declaration_context, segmented_input_audit
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact
from patchloop.dev import runner
from patchloop.dev.cost import pricing_for_model, usd_to_nanos
from patchloop.prepared_source import load_source
from patchloop.runtime import repository_root, runtime_content_paths
from patchloop.util import canonical_json, sha256_bytes, sha256_json, sha256_text

SCHEMA = "declaration-checkpoint-sampler-v1"
SCHEDULE = (("A", 1), ("B", 1), ("B", 2), ("A", 2))
REVIEW = {
    "protocol.md": (
        "One failure-selected first post-search checkpoint; four independent next responses "
        "in A1 B1 B2 A2 order. A exactly rebuilds the saved request. B expands matched Python "
        "declaration documentation and recomputes the ordinary source-dependent state. "
        "Original plan, notes, encrypted continuation, calls, prompt, schemas, budgets, "
        "model/effort/25K output and segment remain fixed. No successful patch or desired "
        "condition is supplied. Historical budget is frozen input, not new spending authority.\n"
        "Use one new invocation cap, exact root .env, reviewed prices and <=60K counted input. "
        "Reserve each A/B pair at the full 25K output ceiling. Count immediately before each "
        "dispatch; zero retries, no resume/replacement/correction, and stop on uncertainty. "
        "Sampled actions are never executed or chained. No Docker or hidden evaluator runs.\n"
        "Compare public questions, proposed reads/edits and their stated purpose. "
        "This does not establish first-edit behavior after a selected read, completed "
        "verification, acceptance, the cause of the initial plan or a general success rate.\n"
    ),
    "rubric.json": canonical_json({
        "official": False, "task_acceptance": "NOT_RUN", "grading": "PUBLIC_DECISION_ONLY",
        "criteria": [
            "What uncertainty is identified, and why could the selected action resolve it?",
            "Does the decision distinguish a setting's meaning from its applicability?",
            "Does the response state a concrete observation that could change its next edit?",
            "Are claims grounded in the public task and observed source rather than check PASS?",
        ],
        "decision_rule": "A repeated difference is a signal for a later rollout, not acceptance.",
        "review": "Use anonymous public decisions before reading arm/cost metadata.",
    }),
}


def wire(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def implementation_hashes():
    return {f"diagnostics/{p.name}": sha256_bytes(p.read_bytes()) for p in (
        Path(__file__), Path(checkpoint.__file__), Path(declaration_context.__file__),
        Path(segmented_input_audit.__file__), Path(shared.__file__),
    )}


def sampler_hash():
    return sha256_json(implementation_hashes())


def protocol(model, effort):
    profile = shared.ModelProfile(model, **{
        k: str(v) for k, v in asdict(pricing_for_model(model)).items()})
    return shared.CollectionProtocol(
        SCHEMA, {"A": effort, "B": effort}, tuple((f"C1/{a}", n) for a, n in SCHEDULE),
        input_token_limit=60_000, reserve_future_calls=False,
        model_profiles={"A": profile, "B": profile}, balanced_block_size=2,
    )


def prepare(source: checkpoint.Source, root: Path, *, cap: Decimal) -> dict:
    usd_to_nanos(cap)
    loaded = checkpoint.load(source)
    checkpoint.disjoint(root, (repository_root(), source.root,
                              Path(loaded.envelope.prepared_source_path).parent))
    root.mkdir()
    requests, receipt = checkpoint.rebuild(loaded, root / "search-replay")
    store = ArtifactStore(root)
    artifacts = {a: store.put_text(wire(r).decode(), "application/json").model_dump(mode="json")
                 for a, r in requests.items()}
    collection = protocol(loaded.envelope.model, loaded.envelope.reasoning_effort)
    packet = {
        **shared.BOUNDARIES, "schema_version": SCHEMA, "status": "PREPARED_NOT_EXECUTABLE",
        "paid_execution_authorized": False, "runtime_hash": loaded.envelope.runtime_hash,
        "source": source.record(), "source_run_id": source.run_id,
        "source_journal_hash": source.journal_hash,
        "source_envelope_hash": source.envelope_hash, "task_id": loaded.public.task_id,
        "task_version": loaded.public.task_version,
        "task_content_hash": loaded.envelope.task_content_hash,
        "model": loaded.envelope.model, "reasoning_effort": loaded.envelope.reasoning_effort,
        "implementation_hashes": implementation_hashes(),
        "pricing": shared.protocol_prices(collection),
        "proposed_total_cap_usd": str(cap), "schedule": [list(x) for x in SCHEDULE],
        "credential_path": str((repository_root() / ".env").resolve()),
        "request_artifacts": artifacts,
        "request_hashes": {a: sha256_json(r) for a, r in requests.items()},
        "ordered_request_hashes": {a: sha256_bytes(wire(r)) for a, r in requests.items()},
        "rebuild_receipt": store.put_json(receipt).model_dump(mode="json"),
        "source_checkpoints": [{
            "case_id": "C1", "turn_id": loaded.start["payload"]["turn_id"],
            "turn_start_event_hash": loaded.start["event_hash"],
            "historical_input_tokens": loaded.historical_count,
            "max_parallel_reads": loaded.start["payload"]["max_parallel_reads"],
            "read_paths": loaded.start["payload"]["targeted_read_paths"],
        }],
        "reviewer_files": {k: sha256_text(v) for k, v in REVIEW.items()},
        "maximum_generation_calls": len(SCHEDULE), "maximum_input_count_calls": len(SCHEDULE),
        "maximum_tool_executions": 0, "maximum_retries": 0, "resume_allowed": False,
        "actual_provider_calls": 0, "actual_cost_nanos": 0,
    }
    for name, body in REVIEW.items():
        store.write_text_immutable(root / name, body)
    store.write_text_immutable(root / "packet.json", canonical_json(packet))
    return {"packet_hash": sha256_bytes((root / "packet.json").read_bytes()),
            "sampler_hash": sampler_hash(), "pricing_hash": sha256_json(packet["pricing"]),
            "status": packet["status"], "actual_provider_calls": 0}


def _read(store, record):
    return store.read_bytes(Artifact.model_validate(record))


def load_plan(packet_path: Path, expected_hash: str) -> shared.FrozenPlan:
    raw = packet_path.read_bytes()
    shared.require(sha256_bytes(raw) == expected_hash, "packet hash changed")
    packet = json.loads(raw)
    shared.require(packet["schema_version"] == SCHEMA
                   and packet["status"] == "PREPARED_NOT_EXECUTABLE"
                   and packet["paid_execution_authorized"] is False
                   and packet["implementation_hashes"] == implementation_hashes()
                   and packet["schedule"] == [list(x) for x in SCHEDULE], "design changed")
    source = checkpoint.Source.from_record(packet["source"])
    loaded = checkpoint.load(source)
    envelope = loaded.envelope
    shared.require((packet["model"], packet["reasoning_effort"], packet["runtime_hash"],
                    packet["task_id"], packet["task_version"], packet["task_content_hash"])
                   == (envelope.model, envelope.reasoning_effort, envelope.runtime_hash,
                       envelope.task_id, envelope.task_version, envelope.task_content_hash),
                   "frozen model/task/runtime mismatch")
    load_source(Path(envelope.prepared_source_path), loaded.public.repository.url,
                loaded.public.repository.base_commit, expected_hash=envelope.prepared_source_hash)
    store = object.__new__(ArtifactStore)
    store.root, store.objects = packet_path.parent, packet_path.parent / "objects/sha256"
    receipt = json.loads(_read(store, packet["rebuild_receipt"]))
    for path, digest in receipt["inherited_artifacts"].items():
        shared.require(sha256_bytes(Path(path).read_bytes()) == digest,
                       "inherited artifact changed")
    requests = {a: _read(store, packet["request_artifacts"][a]) for a in ("A", "B")}
    shared.require(requests["A"] == wire(loaded.request), "baseline frozen request differs")
    for arm, body in requests.items():
        shared.require(sha256_bytes(body) == packet["ordered_request_hashes"][arm]
                       and sha256_json(json.loads(body)) == packet["request_hashes"][arm],
                       "frozen request changed")
    for name, body in REVIEW.items():
        shared.require((packet_path.parent / name).read_bytes() == body.encode(),
                       "review contract changed")
    collection = protocol(envelope.model, envelope.reasoning_effort)
    shared.require(packet["pricing"] == shared.protocol_prices(collection), "price table changed")
    point = packet["source_checkpoints"][0]
    shared.require(point["turn_start_event_hash"] == loaded.start["event_hash"], "cutoff changed")
    cells = tuple(shared.Cell(
        "C1", arm, requests[arm].decode(), packet["request_hashes"][arm], loaded.historical_count,
        loaded.start["payload"]["turn_id"], loaded.start["payload"]["max_parallel_reads"],
        tuple(loaded.start["payload"]["targeted_read_paths"]), repeat,
    ) for arm, repeat in SCHEDULE)
    return shared.FrozenPlan(packet_path.resolve(), expected_hash, packet, cells,
                             source.root.resolve(), {**implementation_hashes(),
                                                     **packet["reviewer_files"]})


def collect(plan, approval, *, adapter_factory=None, clock=monotonic, hook=lambda _: None):
    collection = protocol(plan.packet["model"], plan.packet["reasoning_effort"])
    shared._validate_collection_approval(
        plan, approval, sampler_hash(),
        expected_pricing_hash=sha256_json(shared.protocol_prices(collection)),
    )
    shared.require(str(approval.credential_file.resolve()) == plan.packet["credential_path"],
                   "credential path changed")
    refreshed = load_plan(plan.packet_path, approval.packet_hash)
    shared.require(refreshed.design_hashes == plan.design_hashes, "validated design changed")
    source = checkpoint.Source.from_record(plan.packet["source"])
    envelope = json.loads((source.root / "runs" /
                           f"{source.run_id}.envelope.json").read_bytes())
    # Also exclude ancestors of protected trees, not just children.
    checkpoint.disjoint(approval.result_root, (repository_root(), source.root,
                        plan.packet_path.parent, source.public_path.parent,
                        Path(envelope["prepared_source_path"]).parent))
    if adapter_factory is None:
        runner._require_tracked_clean_paths(repository_root(), [
            *runtime_content_paths(), *implementation_hashes(),
            source.public_path.relative_to(repository_root()).as_posix(),
        ])
    return shared._collect_validated(
        refreshed, approval, protocol=collection, adapter_factory=adapter_factory,
        clock=clock, checkpoint=hook,
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    preparing = commands.add_parser("prepare")
    preparing.add_argument("--source", type=Path, required=True,
                           help="JSON containing exact Source paths and hashes")
    preparing.add_argument("--output", type=Path, required=True)
    preparing.add_argument("--proposed-cap-usd", type=Decimal, required=True)
    for name in ("validate", "collect"):
        command = commands.add_parser(name)
        command.add_argument("--packet", type=Path, required=True)
        command.add_argument("--packet-hash", required=True)
        if name == "collect":
            command.add_argument("--grant", type=Path, required=True,
                                 help="Exact approval fields; preparation is not authorization")
    inspecting = commands.add_parser("inspect")
    inspecting.add_argument("--result", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "prepare":
        result = prepare(checkpoint.Source.from_record(json.loads(args.source.read_bytes())),
                         args.output, cap=args.proposed_cap_usd)
    elif args.command == "inspect":
        result = shared.inspect_result(args.result)
    else:
        plan = load_plan(args.packet, args.packet_hash)
        if args.command == "validate":
            result = {"status": "VALIDATED_NOT_EXECUTED", "cells": len(plan.cells)}
        else:
            grant = json.loads(args.grant.read_bytes())
            grant.update(result_root=Path(grant["result_root"]),
                         credential_file=Path(grant["credential_file"]),
                         max_cost_usd=Decimal(grant["max_cost_usd"]))
            result = collect(plan, shared.Approval(**grant))
    print(canonical_json(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
