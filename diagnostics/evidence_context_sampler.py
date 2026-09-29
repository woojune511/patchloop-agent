"""Frozen public-evidence assessments; report function is never executed."""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path
from time import monotonic

from diagnostics import decision_sampler as shared
from diagnostics import evidence_context_design as design
from patchloop.artifacts import ArtifactStore
from patchloop.dev.cost import pricing_for_model
from patchloop.dev.state import DevJournal
from patchloop.runtime import repository_root, runtime_content_hash
from patchloop.util import canonical_json, sha256_bytes, sha256_json

MODEL = "gpt-5.4-2026-03-05"
SCHEMA = "evidence-context-sampler-v1"
BLOCKS = (("C1", 1, "AB"), ("C2", 1, "BA"), ("C3", 1, "AB"), ("C4", 1, "BA"),
          ("C1", 2, "BA"), ("C2", 2, "AB"), ("C3", 2, "BA"), ("C4", 2, "AB"))
SCHEDULE = tuple((c, a, n) for c, n, arms in BLOCKS for a in arms)
REPORT = {"type": "function", "name": "record_assessment", "strict": True,
          "description": "Return the requested short public assessment. No action is executed.",
          "parameters": {"type": "object", "properties": {"assessment": {"type": "string"}},
                         "required": ["assessment"], "additionalProperties": False}}


def hashes():
    return {**design.implementation_hashes(), **{str(p.resolve()): sha256_bytes(p.read_bytes())
            for p in (Path(__file__), repository_root() / ".agent/evidence-context-sampler.md")}}


def protocol():
    profile = shared.ModelProfile(MODEL, **{
        k: str(v) for k, v in asdict(pricing_for_model(MODEL)).items()})
    return shared.CollectionProtocol(
        SCHEMA, {"A": "xhigh", "B": "xhigh"},
        tuple((f"{c}/{a}", n) for c, a, n in SCHEDULE), input_token_limit=60_000,
        reserve_future_calls=False, model_profiles={"A": profile, "B": profile},
        balanced_block_size=2)


def requests_from_preparation(path):
    path = Path(path).resolve()
    design.validate(path)
    packet = json.loads(path.read_bytes())
    shared.require(set(packet["cases"]) == {c for c, _, _ in SCHEDULE}, "four cases required")
    requests = {}
    for case, saved in packet["cases"].items():
        requests[case] = {}
        for arm, ref in saved["views"].items():
            view = json.loads(Path(ref["path"]).read_bytes())
            requests[case][arm] = {
                **shared.SETTINGS, "model": MODEL, "reasoning": {"effort": "xhigh"},
                "parallel_tool_calls": False, "tools": [REPORT],
                "input": [{"role": "system", "content": view["reviewer_instruction"]},
                          {"role": "user", "content": canonical_json(view["data"])}]}
    return packet, requests


def packet_data(preparation_path):
    path = Path(preparation_path).resolve()
    source, requests = requests_from_preparation(path)
    packet = {
        **shared.BOUNDARIES, "schema_version": SCHEMA, "runtime_hash": runtime_content_hash(),
        "implementation_hashes": hashes(), "preparation_path": str(path),
        "source_packet_hash": sha256_bytes(path.read_bytes()),
        "source_run_id": "four-frozen-public-checkpoints",
        "source_journal_hash": sha256_json(source["source_bindings"]),
        "source_checkpoints": {c: s["receipt"] for c, s in source["cases"].items()},
        "task_id": "multi-task-evidence-context-review", "task_version": 1,
        "task_content_hash": sha256_json(source["cases"]),
        "split": "dev-train", "schedule": [list(s) for s in SCHEDULE],
        "proposed_total_cap_usd": "9",
        "credential_path": str((repository_root() / ".env").resolve()),
        "pricing": shared.protocol_prices(protocol()),
        "request_hashes": {c: {a: sha256_json(r) for a, r in arms.items()}
                           for c, arms in requests.items()},
        "approval": "NOT_GRANTED", "rubric_hash": hashes()[str(
            (repository_root() / ".agent/evidence-context-sampler.md").resolve())],
    }
    return packet, requests


def prepare(preparation_path, root):
    root = Path(root).resolve()
    shared.require(not root.exists() and not root.is_relative_to(repository_root()),
                   "fresh external plan required")
    packet, requests = packet_data(preparation_path)
    root.mkdir(parents=True)
    store = ArtifactStore(root)
    refs = {c: {a: store.put_json(r).model_dump(mode="json") for a, r in arms.items()}
            for c, arms in requests.items()}
    store.write_text_immutable(root / "packet.json", canonical_json(packet))
    DevJournal(root, "run_dev_contextplan").append(
        "plan_prepared", {"packet": packet, "request_artifacts": refs})
    return sha256_bytes((root / "packet.json").read_bytes())


def load_plan(path, expected_hash):
    path = Path(path).resolve()
    shared.require(sha256_bytes(path.read_bytes()) == expected_hash, "packet changed")
    packet = json.loads(path.read_bytes())
    expected, requests = packet_data(packet["preparation_path"])
    shared.require(packet == expected, "design or source changed")
    cells = tuple(shared.Cell(c, a, canonical_json(requests[c][a]), sha256_json(requests[c][a]),
                              None, packet["source_checkpoints"][c]["turn_id"], 1, (), n)
                  for c, a, n in SCHEDULE)
    return shared.FrozenPlan(path, expected_hash, packet, cells,
                             Path(packet["preparation_path"]).parent, hashes())


def parse_report(calls):
    shared.require(len(calls) == 1 and calls[0]["name"] == REPORT["name"],
                   "exactly one assessment report required")
    args = calls[0]["arguments"]
    shared.require(set(args) == {"assessment"} and isinstance(args["assessment"], str)
                   and bool(args["assessment"].strip()), "nonempty public assessment required")
    return args


def collect(plan, approval, *, adapter_factory=None):
    plan = load_plan(plan.packet_path, approval.packet_hash)
    shared._validate_collection_approval(
        plan, approval, sha256_json(hashes()),
        protected_roots=tuple(c[1].resolve() for c in design.CASES),
        expected_pricing_hash=sha256_json(shared.protocol_prices(protocol())))
    shared.require(str(approval.credential_file.resolve()) == plan.packet["credential_path"],
                   "wrong credential file")
    return shared._collect_validated(
        plan, approval, protocol=protocol(), adapter_factory=adapter_factory,
        clock=monotonic, checkpoint=lambda _: None, report_parser=parse_report)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    p = commands.add_parser("prepare")
    p.add_argument("--preparation", type=Path, required=True)
    p.add_argument("--root", type=Path, required=True)
    for command in ("validate", "collect"):
        p = commands.add_parser(command)
        p.add_argument("--packet", type=Path, required=True)
        p.add_argument("--packet-hash", required=True)
        if command == "collect":
            p.add_argument("--approval", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        print(prepare(args.preparation, args.root))
        return
    plan = load_plan(args.packet, args.packet_hash)
    if args.command == "validate":
        print(canonical_json({"cells": len(plan.cells), "provider_calls": 0}))
        return
    approval_data = json.loads(args.approval.read_bytes())
    for name in ("result_root", "credential_file"):
        approval_data[name] = Path(approval_data[name])
    approval_data["max_cost_usd"] = Decimal(approval_data["max_cost_usd"])
    print(canonical_json(collect(plan, shared.Approval(**approval_data))))


if __name__ == "__main__":
    main()
