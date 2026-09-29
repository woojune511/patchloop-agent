"""Fixed post-check completion-guidance ablation; sampled tools never execute."""
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
SCHEMA = "completion-recommendation-ablation-v1"
SOURCE = Path("C:/pt/analyses/observation-repair-panel-20260929-v1/state/B2")
SCHEDULE = (("H", "A", 1), ("H", "B", 1), ("H", "B", 2),
            ("H", "A", 2), ("H", "A", 3), ("H", "B", 3))
ORIGINAL_MESSAGE = (
    "Run one remaining visible check for the current diff: upstream-xet-regression. "
    "Use run_check; PASS on a different diff does not count toward completion. "
    "Submission becomes available when all required checks pass on this scoped patch.")
NEUTRAL_MESSAGE = (
    "PASS on a different diff does not count toward completion. "
    "Submission becomes available when all required checks pass on this scoped patch.")


def hashes():
    return {str(p.resolve()): sha256_bytes(p.read_bytes()) for p in (
        Path(__file__), Path(shared.__file__),
        repository_root() / ".agent/completion-recommendation-ablation.md")}


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
    shared.require(state["completion_guidance"]["stage"] == "needs_visible_checks"
                   and state["remaining_visible_check_ids"] == ["upstream-xet-regression"]
                   and state["completion_guidance"]["message"] == ORIGINAL_MESSAGE,
                   "wrong post-contract checkpoint")
    shared.require(state["operator_public_feedback"]["currency"] == "current_candidate",
                   "current counterexample required")
    shared.require(original["max_output_tokens"] == 25_000, "output ceiling changed")
    a, b = copy.deepcopy(original), copy.deepcopy(original)
    last = b["input"][-1]
    view = json.loads(last["content"])
    shared.require(last.get("role") == "developer" and view["kind"] == "harness_current_state",
                   "latest current-state item required")
    guidance = view["state"]["completion_guidance"]
    shared.require(guidance.pop("next_action") == {
        "tool": "run_check", "check_id": "upstream-xet-regression"}, "unexpected recommendation")
    guidance["message"] = NEUTRAL_MESSAGE
    last["content"] = canonical_json(view)
    expected = copy.deepcopy(state)
    expected["completion_guidance"].pop("next_action")
    expected["completion_guidance"]["message"] = NEUTRAL_MESSAGE
    shared.require(reconstruct_state(b["input"], context_policy="segmented-v1") == expected,
                   "unrelated state changed")
    return {"A": a, "B": b}


def sources():
    root = SOURCE
    envelopes = list((root / "runs").glob("*.envelope.json"))
    shared.require(len(envelopes) == 1, "ambiguous source")
    journal = DevJournal(root, envelopes[0].name.removesuffix(".envelope.json"))
    events, envelope = journal.events(), journal.load_envelope()
    shared.require(envelope.split == "dev-train" and envelope.model == MODEL
                   and envelope.reasoning_effort == "xhigh"
                   and envelope.task_id == "hf-hub-xet-endpoint-propagation"
                   and envelope.task_version == 5, "source contract")
    turns = [e for e in events if e["event_type"] == "turn_started"]
    turn = turns[1]["payload"]
    prior = events[:events.index(turns[1])]
    checks = [e["payload"]["result"] for e in prior if e["event_type"] == "action_finished"]
    shared.require(len(checks) == 1 and checks[0]["tool"] == "run_check"
                   and checks[0]["output"]["passed"] is True, "checkpoint result mismatch")
    bundle = json.loads(shared.read_source_artifact(root, turn["prepared_input"]["artifact"]))
    original = bundle["request"]
    actual = runner._load_active_model_input(
        turn, ArtifactStore(root / "artifacts"), context_policy="segmented-v1")
    shared.require(original["input"] == actual
                   and sha256_json(original) == turn["prepared_input"]["request_hash"],
                   "actual request binding")
    bindings = {str(p): sha256_bytes(p.read_bytes()) for p in (journal.path, envelopes[0])}
    receipt = {"task_id": envelope.task_id, "task_version": envelope.task_version,
               "run_id": journal.run_id, "turn_id": turn["turn_id"],
               "actual_input_hash": sha256_json(actual),
               "source_request_hash": sha256_json(original),
               "prior_check_results": 1}
    return {"H": (project(original), turn, receipt, envelope)}, bindings


def prepare(root):
    shared.require(not root.exists() and not root.resolve().is_relative_to(repository_root()),
                   "fresh external root required")
    loaded, bindings = sources()
    packet = {**shared.BOUNDARIES, "schema_version": SCHEMA,
              "runtime_hash": runtime_content_hash(), "implementation_hashes": hashes(),
              "source_run_id": "run_dev_21504b465fd94901",
              "source_journal_hash": sha256_json(bindings), "sources": bindings,
              "task_id": "hf-hub-xet-endpoint-propagation", "task_version": 5,
              "task_content_hash": sha256_json([x[3].task_content_hash for x in loaded.values()]),
              "schedule": SCHEDULE, "proposed_total_cap_usd": "4",
              "credential_path": str((repository_root() / ".env").resolve()),
              "pricing": shared.protocol_prices(protocol()),
              "request_hashes": {c: {a: sha256_json(r) for a, r in x[0].items()}
                                 for c, x in loaded.items()},
              "delivery": {c: x[2] for c, x in loaded.items()}}
    root.mkdir()
    (root / "packet.json").write_text(canonical_json(packet), encoding="utf-8")
    DevJournal(root, "run_dev_guidanceablationplan").append("plan_prepared", packet)
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
                   and packet["proposed_total_cap_usd"] == "4", "design changed")
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
