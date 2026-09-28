"""Frozen public verification-selection diagnostic; sampled tools never execute."""
from __future__ import annotations

import copy
import json
from dataclasses import asdict
from pathlib import Path
from time import monotonic

from diagnostics import decision_sampler as shared
from patchloop.artifacts import ArtifactStore
from patchloop.dev import runner
from patchloop.dev.conversation import reconstruct_state
from patchloop.dev.cost import pricing_for_model
from patchloop.dev.state import DevJournal
from patchloop.runtime import repository_root, runtime_content_hash
from patchloop.util import canonical_json, sha256_bytes, sha256_json

MODEL = "gpt-5.4-2026-03-05"
SCHEMA = "discriminating-case-selection-v1"
SOURCE = Path("C:/pt/boundarypair0928b")
CASES = ("P", "H", "F", "L", "D", "G")
SCHEDULE = tuple((c, a, n) for n in (1, 2) for i, c in enumerate(CASES)
                 for a in (("A", "B") if (i + n) % 2 else ("B", "A")))
COMMON = """For this diagnostic response, choose one public verification action for
 the current candidate repair. Do not edit or submit. State a concrete input,
 the expected behavior derived from the public requirement, and what the proposed
 observation would establish. Use existing tool fields. If evidence is insufficient,
 select a targeted read/search and state what remains unresolved. Returned actions
 will be collected only; do not claim they have executed. The current patch and
 earlier public state below are the frozen candidate, not a known-correct solution."""
TREATMENT = """Try to falsify the candidate's applicability condition: look for
 inputs that satisfy the same proposed code guard but require different behavior
 under the public requirement. Hold incidental factors constant where possible.
 Identify which requirement distinction the guard might lose and choose evidence
 that would expose that mismatch. Do not invent a bug or an unsupported expectation;
 if no such case is supported, state that limit rather than fabricate one."""


def hashes():
    return {str(p.resolve()): sha256_bytes(p.read_bytes()) for p in (
        Path(__file__), Path(shared.__file__),
        repository_root() / ".agent/discriminating-case-selection.md")}


def protocol():
    profile = shared.ModelProfile(MODEL, **{
        k: str(v) for k, v in asdict(pricing_for_model(MODEL)).items()})
    return shared.CollectionProtocol(
        SCHEMA, {"A": "xhigh", "B": "xhigh"},
        tuple((f"{c}/{a}", n) for c, a, n in SCHEDULE),
        input_token_limit=60_000, reserve_future_calls=False,
        model_profiles={"A": profile, "B": profile}, balanced_block_size=2)


def project(original):
    state = reconstruct_state(original["input"], context_policy="segmented-v1")
    shared.require(state["current_diff"]["patch"], "candidate patch required")
    shared.require("run_probe" in {t["name"] for t in original["tools"]},
                   "probe unavailable at checkpoint")
    requests = {}
    for arm in ("A", "B"):
        request = copy.deepcopy(original)
        request["max_output_tokens"] = 25_000
        request["input"].append({"role": "user", "content": COMMON})
        if arm == "B":
            request["input"].append({"role": "user", "content": TREATMENT})
        requests[arm] = request
    return requests


def sources():
    loaded, bindings = {}, {}
    for case in CASES:
        root = SOURCE / "state" / f"{case}A1"
        envelopes = list((root / "runs").glob("*.envelope.json"))
        shared.require(len(envelopes) == 1, "ambiguous source")
        run_id = envelopes[0].name.removesuffix(".envelope.json")
        journal = DevJournal(root, run_id)
        events, envelope = journal.events(), journal.load_envelope()
        shared.require(envelope.split == "dev-train" and envelope.model == MODEL
                       and envelope.reasoning_effort == "xhigh", "source contract")
        decision = next(e for e in events if e["event_type"] == "turn_decision_recorded"
                        and any(c["name"] == "run_check" for c in e["payload"]["tool_calls"]))
        turn = next(e["payload"] for e in events if e["event_type"] == "turn_started"
                    and e["payload"]["turn_id"] == decision["payload"]["turn_id"])
        prior = events[:events.index(decision)]
        shared.require(not any(e["event_type"] == "action_finished"
                               and e["payload"]["result"]["tool"] in {"run_check", "run_probe"}
                               for e in prior), "checkpoint includes verification feedback")
        bundle = json.loads(shared.read_source_artifact(root, turn["prepared_input"]["artifact"]))
        original = bundle["request"]
        shared.require(sha256_json(original) == turn["prepared_input"]["request_hash"],
                       "prepared request binding")
        actual = runner._load_active_model_input(
            turn, ArtifactStore(root / "artifacts"), context_policy="segmented-v1")
        shared.require(original["input"] == actual, "actual input mismatch")
        for p in (journal.path, envelopes[0]):
            bindings[str(p)] = sha256_bytes(p.read_bytes())
        receipt = {"task_id": envelope.task_id, "task_version": envelope.task_version,
                   "run_id": run_id, "turn_id": turn["turn_id"],
                   "actual_input_hash": sha256_json(actual),
                   "source_request_hash": sha256_json(original),
                   "prior_check_or_probe_results": 0}
        loaded[case] = (project(original), turn, receipt, envelope)
    return loaded, bindings


def prepare(root):
    shared.require(not root.exists() and not root.resolve().is_relative_to(repository_root()),
                   "fresh external root required")
    loaded, bindings = sources()
    packet = {**shared.BOUNDARIES, "schema_version": SCHEMA,
              "runtime_hash": runtime_content_hash(), "implementation_hashes": hashes(),
              "source_run_id": "six-frozen-public-candidates",
              "source_journal_hash": sha256_json(bindings), "sources": bindings,
              "task_id": "six-dev-train", "task_version": 1,
              "task_content_hash": sha256_json([x[3].task_content_hash for x in loaded.values()]),
              "schedule": SCHEDULE, "proposed_total_cap_usd": "13",
              "credential_path": str((repository_root() / ".env").resolve()),
              "pricing": shared.protocol_prices(protocol()),
              "request_hashes": {c: {a: sha256_json(r) for a, r in x[0].items()}
                                 for c, x in loaded.items()},
              "delivery": {c: x[2] for c, x in loaded.items()}}
    root.mkdir()
    (root / "packet.json").write_text(canonical_json(packet), encoding="utf-8")
    DevJournal(root, "run_dev_caseselectionplan").append("plan_prepared", packet)
    return sha256_bytes((root / "packet.json").read_bytes())


def load_plan(path, expected_hash):
    raw = path.read_bytes()
    shared.require(sha256_bytes(raw) == expected_hash, "packet changed")
    packet = json.loads(raw)
    shared.require(packet["implementation_hashes"] == hashes()
                   and packet["runtime_hash"] == runtime_content_hash()
                   and packet["schema_version"] == SCHEMA
                   and packet["schedule"] == [list(x) for x in SCHEDULE]
                   and packet["pricing"] == shared.protocol_prices(protocol())
                   and packet["proposed_total_cap_usd"] == "13", "design changed")
    loaded, bindings = sources()
    shared.require(packet["sources"] == bindings, "source changed")
    cells = []
    for case, arm, n in SCHEDULE:
        requests, turn, _, _ = loaded[case]
        request = requests[arm]
        shared.require(sha256_json(request) == packet["request_hashes"][case][arm],
                       "request changed")
        cells.append(shared.Cell(case, arm, canonical_json(request), sha256_json(request),
                                 None, turn["turn_id"], turn["max_parallel_reads"],
                                 tuple(turn["targeted_read_paths"]), n))
    return shared.FrozenPlan(path.resolve(), expected_hash, packet, tuple(cells), SOURCE, hashes())


def collect(plan, approval, *, adapter_factory=None):
    plan = load_plan(plan.packet_path, approval.packet_hash)
    shared._validate_collection_approval(
        plan, approval, sha256_json(hashes()),
        expected_pricing_hash=sha256_json(shared.protocol_prices(protocol())))
    shared.require(str(approval.credential_file.resolve()) == plan.packet["credential_path"],
                   "wrong credential file")
    return shared._collect_validated(plan, approval, protocol=protocol(),
                                    adapter_factory=adapter_factory, clock=monotonic,
                                    checkpoint=lambda _: None)
