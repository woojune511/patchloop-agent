"""Frozen submission decisions with a generic public-evidence disposition request."""
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

SCHEMA = "evidence-disposition-sampler-v1"
MODEL = "gpt-5.4-2026-03-05"
ROOT = Path("C:/pt")
SOURCES = (
    ("C1", ROOT / "analyses/observation-repair-panel-20260929-v1/state/B2",
     "turn_02f6b9132e2e43d4aa39e991bfef8564", "hf-hub-xet-endpoint-propagation", 5),
    ("C2", ROOT / "analyses/observation-repair-panel-20260929-v1/state/B1",
     "turn_8c924f5bb22c4afd9c5af9c89a9c6dd6", "hf-hub-xet-endpoint-propagation", 5),
    ("C3", ROOT / "observation-comparison-20260929-v1/N1B",
     "turn_97c0feda4c21455e967c395573b90a55", "anyio-interrupt-runner-cleanup", 3),
)
BLOCKS = (("C1", 1, "AB"), ("C2", 1, "BA"), ("C3", 1, "AB"),
          ("C1", 2, "BA"), ("C2", 2, "AB"), ("C3", 2, "BA"))
SCHEDULE = tuple((case, arm, repeat) for case, repeat, arms in BLOCKS for arm in arms)
INSTRUCTION = (
    "For this next decision, use the existing public turn_decision.basis (within its "
    "length limit) to give a brief disposition of contrary check, probe, or operator "
    "observations relevant to your chosen action: applicable and unresolved; resolved "
    "by cited evidence; inapplicable for a cited reason; or insufficient evidence. "
    "Identify the observation by action ID or source field and distinguish its candidate "
    "from the current candidate. Relate any PASS you rely on to the behavior it actually "
    "exercises. An unsuccessful execution is not automatically a product defect, and "
    "an older observation is not automatically resolved. Select the next registered "
    "action using that assessment. Do not invent observations or presume that more "
    "inspection is always necessary. Provide only this short public evidence summary, "
    "not private reasoning. Keep the existing response schema."
)


def hashes():
    return {str(p.resolve()): sha256_bytes(p.read_bytes()) for p in (
        Path(__file__), Path(shared.__file__),
        repository_root() / ".agent/evidence-disposition-sampler.md")}


def protocol():
    profile = shared.ModelProfile(MODEL, **{
        k: str(v) for k, v in asdict(pricing_for_model(MODEL)).items()})
    return shared.CollectionProtocol(
        SCHEMA, {"A": "xhigh", "B": "xhigh"},
        tuple((f"{c}/{a}", n) for c, a, n in SCHEDULE), input_token_limit=60_000,
        reserve_future_calls=False, model_profiles={"A": profile, "B": profile},
        balanced_block_size=2)


def project(original):
    state = reconstruct_state(original["input"], context_policy="segmented-v1")
    checks, diff = state["visible_check_status"], state["current_diff"]
    shared.require(state["workflow_gate"] == "ready_to_submit"
                   and not state["remaining_visible_check_ids"] and checks
                   and all(c["status"] == "PASS" and c["diff_hash"] == diff["patch_hash"]
                           for c in checks), "checked submission checkpoint required")
    names = {t["name"] for t in original["tools"]}
    shared.require(names == set(state["available_tool_names"])
                   and {"finish_task", "search_files", "run_probe"} <= names,
                   "submission and investigation must be offered")
    shared.require(original["model"] == MODEL
                   and original["reasoning"]["effort"] == "xhigh"
                   and original["max_output_tokens"] == 25_000
                   and original["input"][0]["role"] == "system", "fixed model contract")
    a, b = copy.deepcopy(original), copy.deepcopy(original)
    b["input"][0]["content"] += "\n\n" + INSTRUCTION
    shared.require(reconstruct_state(b["input"], context_policy="segmented-v1") == state,
                   "state changed")
    return {"A": a, "B": b}


def sources():
    loaded, bindings = {}, {}
    for case, root, turn_id, task, version in SOURCES:
        envelopes = list((root / "runs").glob("*.envelope.json"))
        shared.require(len(envelopes) == 1, "ambiguous source")
        journal = DevJournal(root, envelopes[0].name.removesuffix(".envelope.json"))
        events, envelope = journal.events(), journal.load_envelope()
        shared.require((envelope.split, envelope.task_id, envelope.task_version,
                        envelope.model, envelope.reasoning_effort) ==
                       ("dev-train", task, version, MODEL, "xhigh"), "source contract")
        turn = next(e["payload"] for e in events if e["event_type"] == "turn_started"
                    and e["payload"]["turn_id"] == turn_id)
        bundle = json.loads(shared.read_source_artifact(root, turn["prepared_input"]["artifact"]))
        original = bundle["request"]
        actual = runner._load_active_model_input(
            turn, ArtifactStore(root / "artifacts"), context_policy="segmented-v1")
        shared.require(original["input"] == actual
                       and sha256_json(original) == turn["prepared_input"]["request_hash"],
                       "actual request binding")
        state = reconstruct_state(actual, context_policy="segmented-v1")
        feedback = state.get("operator_public_feedback")
        if case in {"C1", "C2"}:
            current = feedback["observed_on_diff_hash"] == state["current_diff"]["patch_hash"]
            shared.require(current == (case == "C1") and feedback["currency"] ==
                           ("current_candidate" if current else "historical_candidate"),
                           "feedback currency control changed")
        else:
            probes = [p for p in state["recent_probes"]
                      if p["action_id"] == "call_2JGcBMcg2C5fCncp3neASL4Q"]
            shared.require(len(probes) == 1 and probes[0]["historical"]
                           and probes[0]["observation"]["setup_check_observation"]["status"]
                           == "failed" and "wrapped_name" in probes[0]["stderr"],
                           "setup control changed")
        for p in (journal.path, envelopes[0]):
            bindings[str(p)] = sha256_bytes(p.read_bytes())
        receipt = {"task_id": task, "task_version": version,
                   "task_content_hash": envelope.task_content_hash,
                   "run_id": journal.run_id, "turn_id": turn_id,
                   "input_hash": sha256_json(actual), "request_hash": sha256_json(original),
                   "state_hash": sha256_json(state),
                   "diff_hash": state["current_diff"]["patch_hash"]}
        loaded[case] = (project(original), turn, receipt)
    return loaded, bindings


def packet_data(loaded, bindings):
    return {**shared.BOUNDARIES, "schema_version": SCHEMA,
            "runtime_hash": runtime_content_hash(), "implementation_hashes": hashes(),
            "source_run_id": "multiple-frozen-public-checkpoints",
            "source_journal_hash": sha256_json(bindings), "sources": bindings,
            "source_checkpoints": {c: x[2] for c, x in loaded.items()},
            "task_id": "multi-task-disposition-diagnostic", "task_version": 1,
            "task_content_hash": sha256_json([x[2]["task_content_hash"] for x in loaded.values()]),
            "schedule": [list(x) for x in SCHEDULE], "proposed_total_cap_usd": "8",
            "credential_path": str((repository_root() / ".env").resolve()),
            "pricing": shared.protocol_prices(protocol()),
            "request_hashes": {c: {a: sha256_json(r) for a, r in x[0].items()}
                               for c, x in loaded.items()}}


def prepare(root):
    root = Path(root)
    shared.require(not root.exists() and not root.resolve().is_relative_to(repository_root()),
                   "fresh external root required")
    loaded, bindings = sources()
    packet = packet_data(loaded, bindings)
    root.mkdir(parents=True)
    store = ArtifactStore(root)
    # Requests contain only original public input plus the generic instruction, no grading data.
    request_refs = {c: {a: store.put_json(r).model_dump(mode="json") for a, r in x[0].items()}
                    for c, x in loaded.items()}
    (root / "packet.json").write_text(canonical_json(packet), encoding="utf-8")
    DevJournal(root, "run_dev_dispositionplan").append(
        "plan_prepared", {"packet": packet, "request_artifacts": request_refs})
    return sha256_bytes((root / "packet.json").read_bytes())


def load_plan(path, expected_hash):
    path = Path(path)
    raw = path.read_bytes()
    shared.require(sha256_bytes(raw) == expected_hash, "packet changed")
    packet = json.loads(raw)
    loaded, bindings = sources()
    shared.require(packet == packet_data(loaded, bindings), "design or source changed")
    cells = []
    for case, arm, number in SCHEDULE:
        requests, turn, _ = loaded[case]
        request = requests[arm]
        cells.append(shared.Cell(case, arm, canonical_json(request), sha256_json(request),
                                 None, turn["turn_id"], turn["max_parallel_reads"],
                                 tuple(turn["targeted_read_paths"]), number))
    return shared.FrozenPlan(path.resolve(), expected_hash, packet, tuple(cells), ROOT, hashes())


def collect(plan, approval, *, adapter_factory=None):
    plan = load_plan(plan.packet_path, approval.packet_hash)
    # Protect exact sources, not the whole C:/pt parent used for independent new results.
    source_root = SOURCES[0][1]
    plan = shared.FrozenPlan(plan.packet_path, plan.packet_hash, plan.packet, plan.cells,
                             source_root, plan.design_hashes)
    shared._validate_collection_approval(
        plan, approval, sha256_json(hashes()),
        protected_roots=tuple(s[1] for s in SOURCES[1:]),
        expected_pricing_hash=sha256_json(shared.protocol_prices(protocol())))
    shared.require(str(approval.credential_file.resolve()) == plan.packet["credential_path"],
                   "wrong credential file")
    return shared._collect_validated(plan, approval, protocol=protocol(),
                                    adapter_factory=adapter_factory, clock=monotonic,
                                    checkpoint=lambda _: None)
