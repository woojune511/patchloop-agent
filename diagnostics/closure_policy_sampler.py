"""Frozen closure-policy responses; never execute or chain sampled actions."""
from __future__ import annotations

import argparse
import copy
import json
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path
from time import monotonic

from diagnostics import decision_sampler as shared
from diagnostics import segmented_input_audit
from diagnostics.cleanup_information_checkpoint import ForkStore
from diagnostics.declaration_checkpoint import disjoint
from patchloop.artifacts import ArtifactStore
from patchloop.dev import runner
from patchloop.dev.cost import pricing_for_model, usd_to_nanos
from patchloop.dev.state import DevJournal
from patchloop.runtime import repository_root, runtime_content_hash, runtime_content_paths
from patchloop.task_loader import load_public_task
from patchloop.util import canonical_json, sha256_bytes, sha256_json

SCHEMA = "closure-policy-sampler-v1"
SCHEDULE = (("A", 1), ("B", 1), ("B", 2), ("A", 2))
REMOVED = (
    "Use an affordable experiment if it could change the decision, otherwise submit.\n"
    "No extra review call, annotation or experiment is required.\n"
)
MODEL = "gpt-5.4-2026-03-05"
RECONCILE = (
    "\nWhen choosing an expected result for a probe, reconcile it with contrary observations "
    "already in context. If those observations refute the proposed formula, do not reuse it "
    "as an exact expectation without a justified applicability restriction. Separate "
    "implementation evidence from support for the expectation.\n"
)


def project_requests(original, intervention):
    baseline = copy.deepcopy(original)
    shared.require(intervention in {"remove-closure-advice", "reconcile-expectation"},
                   "unknown intervention")
    if intervention == "reconcile-expectation":
        shared.require("run_probe" in {t["name"] for t in baseline["tools"]},
                       "probe tool unavailable")
        baseline["tool_choice"] = {"type": "function", "name": "run_probe"}
    treatment = copy.deepcopy(baseline)
    system = treatment["input"][0]
    shared.require(system["role"] == "system", "first input is not system")
    if intervention == "remove-closure-advice":
        shared.require(system["content"].count(REMOVED) == 1, "policy text not unique")
        system["content"] = system["content"].replace(REMOVED, "", 1)
    else:
        system["content"] += RECONCILE
    return {"A": baseline, "B": treatment}


def implementation_hashes():
    return {str(p.relative_to(repository_root()).as_posix()): sha256_bytes(p.read_bytes())
            for p in (Path(__file__).resolve(), Path(shared.__file__).resolve(),
                      Path(segmented_input_audit.__file__).resolve(),
                      Path(__file__).resolve().with_name("cleanup_information_checkpoint.py"),
                      Path(__file__).resolve().with_name("declaration_checkpoint.py"),
                      repository_root() / ".agent/closure-policy-sampler.md")}


def sampler_hash():
    return sha256_json(implementation_hashes())


def protocol():
    profile = shared.ModelProfile(MODEL, **{
        k: str(v) for k, v in asdict(pricing_for_model(MODEL)).items()})
    # The inherited 60K input bound plus the full 25K output ceiling must fit $1.
    # No spare allowance is transferred from another response.
    shared.require(shared.full_reservation(60_000, profile.pricing()) <= usd_to_nanos(Decimal(1)),
                   "price table exceeds per-response cap")
    return shared.CollectionProtocol(
        SCHEMA, {"A": "xhigh", "B": "xhigh"}, SCHEDULE,
        input_token_limit=60_000, reserve_future_calls=False,
        model_profiles={"A": profile, "B": profile},
    )


def load_pair(path, expected_hash):
    raw = path.read_bytes()
    shared.require(sha256_bytes(raw) == expected_hash, "pair hash changed")
    pair = json.loads(raw)
    shared.require(pair["schema"] == "closure-policy-next-decision-design-v1"
                   and pair["paid_execution_authorized"] is False, "pair schema")
    source = Path(pair["source_root"])
    lane = pair.get("source_lane", "time-extension")
    shared.require(lane in {"time-extension", "post-invalid-probe"}, "unknown source lane")
    group_id, branch_name = (("run_dev_timeextension", "A1") if lane == "time-extension"
                             else ("run_dev_probefollowup", "B2"))
    group = DevJournal(source, group_id)
    branch = DevJournal(source / branch_name, "run_dev_33068b6e257f423a")
    shared.require(sha256_bytes(group.path.read_bytes()) == pair["source_group_hash"]
                   and sha256_bytes(branch.path.read_bytes()) == pair["source_branch_hash"],
                   "source journal changed")
    envelope = branch.load_envelope()
    task = Path(envelope.task_path)
    shared.require(envelope.split == "dev-train" and envelope.task_id == "original-toqito-1538"
                   and envelope.model == MODEL and envelope.reasoning_effort == "xhigh"
                   and envelope.runtime_hash == runtime_content_hash(), "source identity changed")
    shared.require(sha256_json(load_public_task(task).model_dump(mode="json"))
                   == envelope.public_spec_hash,
                   "public task changed")
    events = branch.events()
    turn = next(e for e in events if e["sequence"] == pair["source_turn_sequence"])
    shared.require(turn["event_type"] == "turn_started", "not a turn boundary")
    dispatches = [e for e in group.events() if e["event_type"] == "actual_dispatch_started"]
    shared.require(len(dispatches) == (1 if lane == "time-extension" else 5),
                   "ambiguous source dispatch")
    original = json.loads(shared.read_source_artifact(
        source, dispatches[-1]["payload"]["artifact"]))
    if lane == "post-invalid-probe":
        state = json.loads(original["input"][-1]["content"])["state"]
        shared.require(state["completion_guidance"]["submission_ready"]
                       and state["remaining_budget"]["accepted_mutations"] == 0
                       and "SyntaxError" in canonical_json(original["input"])
                       and {"run_probe", "finish_task"} <= {t["name"] for t in original["tools"]},
                       "not the post-invalid-probe submission boundary")
    requests = {arm: json.loads(shared.read_source_artifact(path.parent, pair["requests"][arm]))
                for arm in ("A", "B")}
    intervention = pair.get("intervention", "remove-closure-advice")
    shared.require(intervention != "reconcile-expectation" or lane == "post-invalid-probe",
                   "reconciliation requires post-invalid-probe source")
    expected = project_requests(original, intervention)
    shared.require(requests["A"] == expected["A"], "baseline differs from projection")
    shared.require(requests["B"] == expected["B"], "treatment changed other fields")
    shared.require({a: sha256_json(r) for a, r in requests.items()} == pair["request_hashes"],
                   "request hash changed")
    shared.require(original["model"] == MODEL and original["reasoning"]["effort"] == "xhigh"
                   and original["max_output_tokens"] == shared.OUTPUT_CEILING,
                   "request settings changed")
    segmented_input_audit.verify_turn(turn, events, ForkStore(source / branch_name, events),
                                      actual_input=original["input"])
    return pair, envelope, turn, requests


def prepare(pair_path, pair_hash, output):
    pair, envelope, _, _ = load_pair(pair_path, pair_hash)
    disjoint(output, (repository_root(), pair_path.parent, Path(pair["source_root"])))
    output.mkdir()
    store = ArtifactStore(output / "artifacts")
    packet = {
        **shared.BOUNDARIES, "schema_version": SCHEMA, "paid_execution_authorized": False,
        "pair_path": str(pair_path.resolve()), "pair_hash": pair_hash,
        "implementation_hashes": implementation_hashes(), "runtime_hash": envelope.runtime_hash,
        "source_run_id": envelope.run_id, "source_journal_hash": pair["source_branch_hash"],
        "task_id": envelope.task_id, "task_version": envelope.task_version,
        "task_content_hash": envelope.task_content_hash,
        "public_task_hash": envelope.public_spec_hash,
        "credential_path": str((repository_root() / ".env").resolve()),
        "proposed_total_cap_usd": "4.00", "per_response_cap_usd": "1.00",
        "pricing": shared.protocol_prices(protocol()), "schedule": SCHEDULE,
        "active_seconds": shared.ACTIVE_SECONDS,
    }
    artifact = store.put_json(packet)
    DevJournal(output, "run_dev_closurepolicyplan").append(
        "plan_prepared", {"packet": artifact.model_dump(mode="json")})
    with (output / "packet.json").open("x", encoding="utf-8") as stream:
        stream.write(canonical_json(packet))
    return {"packet_hash": sha256_bytes((output / "packet.json").read_bytes()),
            "sampler_hash": sampler_hash(), "pricing_hash": sha256_json(packet["pricing"]),
            "status": "PREPARED_NOT_EXECUTED"}


def load_plan(path, expected_hash):
    raw = path.read_bytes()
    shared.require(sha256_bytes(raw) == expected_hash, "packet hash changed")
    packet = json.loads(raw)
    shared.require(packet["schema_version"] == SCHEMA
                   and packet["paid_execution_authorized"] is False
                   and packet["implementation_hashes"] == implementation_hashes()
                   and packet["runtime_hash"] == runtime_content_hash()
                   and packet["proposed_total_cap_usd"] == "4.00"
                   and packet["per_response_cap_usd"] == "1.00"
                   and packet["schedule"] == [list(x) for x in SCHEDULE]
                   and packet["pricing"] == shared.protocol_prices(protocol()), "plan changed")
    pair, envelope, turn, requests = load_pair(Path(packet["pair_path"]), packet["pair_hash"])
    shared.require(packet["public_task_hash"] == envelope.public_spec_hash
                   and packet["task_content_hash"] == envelope.task_content_hash
                   and packet["credential_path"] == str((repository_root() / ".env").resolve()),
                   "task or credential identity changed")
    cells = tuple(shared.Cell(
        "C1", arm, json.dumps(requests[arm], ensure_ascii=False, separators=(",", ":")),
        sha256_json(requests[arm]), None, turn["payload"]["turn_id"],
        turn["payload"]["max_parallel_reads"], tuple(turn["payload"]["targeted_read_paths"]), n,
    ) for arm, n in SCHEDULE)
    return shared.FrozenPlan(path.resolve(), expected_hash, packet, cells,
                             Path(pair["source_root"]).resolve(), implementation_hashes())


def collect(plan, approval, *, adapter_factory=None, clock=monotonic, hook=lambda _: None):
    refreshed = load_plan(plan.packet_path, approval.packet_hash)
    shared._validate_collection_approval(
        refreshed, approval, sampler_hash(),
        expected_pricing_hash=sha256_json(shared.protocol_prices(protocol())))
    shared.require(str(approval.credential_file.resolve()) == refreshed.packet["credential_path"],
                   "credential path changed")
    disjoint(approval.result_root, (repository_root(), refreshed.source_root,
                                   refreshed.packet_path.parent,
                                   Path(refreshed.packet["pair_path"]).parent))
    if adapter_factory is None:
        runner._require_tracked_clean_paths(repository_root(), [
            *runtime_content_paths(), *implementation_hashes(),
            "tasks/dev-train/original-toqito-1538/public.yaml",
        ])
    return shared._collect_validated(refreshed, approval, protocol=protocol(),
                                     adapter_factory=adapter_factory, clock=clock, checkpoint=hook)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prep = commands.add_parser("prepare")
    prep.add_argument("--pair", type=Path, required=True)
    prep.add_argument("--pair-hash", required=True)
    prep.add_argument("--output", type=Path, required=True)
    for name in ("validate", "collect"):
        command = commands.add_parser(name)
        command.add_argument("--packet", type=Path, required=True)
        command.add_argument("--packet-hash", required=True)
        if name == "collect":
            command.add_argument("--grant", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "prepare":
        result = prepare(args.pair, args.pair_hash, args.output)
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
