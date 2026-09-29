"""Pre-mutation requirement focus diagnostic; no returned tool execution."""
from __future__ import annotations

import copy
import json
from dataclasses import asdict
from pathlib import Path
from time import monotonic

from diagnostics import decision_sampler as shared
from diagnostics import segmented_input_audit
from diagnostics.cleanup_information_checkpoint import ForkStore
from patchloop.dev.conversation import reconstruct_state
from patchloop.dev.cost import pricing_for_model
from patchloop.dev.state import DevJournal
from patchloop.runtime import repository_root, runtime_content_hash
from patchloop.util import canonical_json, sha256_bytes, sha256_json

MODEL = "gpt-5.4-2026-03-05"
SCHEMA = "pre-edit-issue-focus-v1"
CASES = (
    ("P", "C:/pt/planafter0927a", "run_dev_planafter0927a", "PA1",
     "run_dev_178cdeda35fb487a", "pydantic-ai-synthetic-tool-reasoning"),
    ("H", "C:/pt/planafter0927a", "run_dev_planafter0927a", "HA1",
     "run_dev_60f3627c7a1a4ddf", "hf-hub-xet-endpoint-propagation"),
    ("F", "C:/pt/planreg0927a", "run_dev_planreg0927a", "FA1",
     "run_dev_6e5fa3bd61854018", "fromager-recursive-orphan-removal"),
)
SCHEDULE = tuple((case, arm, n) for n in (1, 2) for case, *_ in CASES
                 for arm in (("A", "B") if n == 1 else ("B", "A")))
# P/F before the first mutation; H before the final self.endpoint forwarding mutation.
CALLS = {"P": 5, "H": 9, "F": 2}
HEADER = "Original public issue, repeated verbatim for the next action. " \
         "This is not a new requirement or new observation."


def hashes():
    return {str(p.resolve()): sha256_bytes(p.read_bytes()) for p in (
        Path(__file__), Path(shared.__file__), Path(segmented_input_audit.__file__),
        repository_root() / ".agent/pre-edit-issue-focus.md")}


def protocol():
    profile = shared.ModelProfile(MODEL, **{
        k: str(v) for k, v in asdict(pricing_for_model(MODEL)).items()})
    return shared.CollectionProtocol(
        SCHEMA, {"A": "xhigh", "B": "xhigh"},
        tuple((f"{c}/{a}", n) for c, a, n in SCHEDULE),
        input_token_limit=60_000, reserve_future_calls=False,
        model_profiles={"A": profile, "B": profile}, balanced_block_size=2)


def project(original):
    a = copy.deepcopy(original)
    a["max_output_tokens"] = 25_000  # Common fresh response allowance, not the intervention.
    state = reconstruct_state(a["input"], context_policy="segmented-v1")
    shared.require("replace_text" in {t["name"] for t in a["tools"]},
                   "mutation unavailable at checkpoint")
    issue = state["public_task"]["issue"]
    b = copy.deepcopy(a)
    b["input"].append({"role": "user", "content": canonical_json({
        "description": HEADER, "issue": issue})})
    return {"A": a, "B": b}


def sources():
    loaded, bindings = {}, {}
    for case, root_s, group_id, label, run_id, task_id in CASES:
        root = Path(root_s)
        group, branch = DevJournal(root, group_id), DevJournal(root / label, run_id)
        events, envelope = branch.events(), branch.load_envelope()
        shared.require(envelope.split == "dev-train" and envelope.task_id == task_id
                       and envelope.model == MODEL and envelope.reasoning_effort == "xhigh",
                       "source task/model mismatch")
        for path in (group.path, branch.path, branch.path.with_suffix(".envelope.json")):
            bindings[str(path)] = sha256_bytes(path.read_bytes())
        turns = [e for e in events if e["event_type"] == "turn_started"]
        dispatches = [e for e in group.events() if e["event_type"] == "diagnostic_wire_dispatch"
                      and e["payload"]["label"] == label]
        shared.require(len(turns) == len(dispatches), "ambiguous dispatch binding")
        index = CALLS[case] - 1
        original = json.loads(shared.read_source_artifact(
            root, dispatches[index]["payload"]["request_artifact"]))
        receipt = segmented_input_audit.verify_turn(
            turns[index], events, ForkStore(root / label, events), actual_input=original["input"])
        loaded[case] = (project(original), turns[index]["payload"], receipt, envelope)
    return loaded, bindings


def prepare(root):
    shared.require(not root.exists() and not root.resolve().is_relative_to(repository_root()),
                   "fresh external plan required")
    loaded, bindings = sources()
    root.mkdir()
    packet = {**shared.BOUNDARIES, "schema_version": SCHEMA,
              "runtime_hash": runtime_content_hash(), "implementation_hashes": hashes(),
              "source_run_id": "multi-task-frozen", "source_journal_hash": sha256_json(bindings),
              "task_id": "multi-task-dev-train", "task_version": 1,
              "task_content_hash": sha256_json([v[3].task_content_hash for v in loaded.values()]),
              "sources": bindings, "schedule": SCHEDULE, "proposed_total_cap_usd": "8",
              "credential_path": str((repository_root() / ".env").resolve()),
              "pricing": shared.protocol_prices(protocol()),
              "request_hashes": {c: {a: sha256_json(r) for a, r in v[0].items()}
                                 for c, v in loaded.items()},
              "delivery": {c: v[2] for c, v in loaded.items()}}
    with (root / "packet.json").open("x", encoding="utf-8") as f:
        f.write(canonical_json(packet))
    DevJournal(root, "run_dev_preeditfocusplan").append("plan_prepared", packet)
    return sha256_bytes((root / "packet.json").read_bytes())


def load_plan(path, expected_hash):
    raw = path.read_bytes()
    shared.require(sha256_bytes(raw) == expected_hash, "packet changed")
    p = json.loads(raw)
    shared.require(p["implementation_hashes"] == hashes()
                   and p["runtime_hash"] == runtime_content_hash()
                   and p["schema_version"] == SCHEMA
                   and p["schedule"] == [list(x) for x in SCHEDULE]
                   and p["proposed_total_cap_usd"] == "8"
                   and p["pricing"] == shared.protocol_prices(protocol()), "design changed")
    loaded, bindings = sources()
    shared.require(p["sources"] == bindings, "source changed")
    cells = []
    for case, arm, n in SCHEDULE:
        requests, turn, _, _ = loaded[case]
        r = requests[arm]
        shared.require(sha256_json(r) == p["request_hashes"][case][arm], "request changed")
        wire = json.dumps(r, ensure_ascii=False, separators=(",", ":"))
        cells.append(shared.Cell(case, arm, wire,
                                 sha256_json(r), None, turn["turn_id"],
                                 turn["max_parallel_reads"], tuple(turn["targeted_read_paths"]), n))
    return shared.FrozenPlan(path.resolve(), expected_hash, p, tuple(cells),
                             Path("C:/pt/planafter0927a"), hashes())


def collect(plan, approval, *, adapter_factory=None):
    plan = load_plan(plan.packet_path, approval.packet_hash)
    shared._validate_collection_approval(
        plan, approval, sha256_json(hashes()), protected_roots=(Path("C:/pt/planreg0927a"),),
        expected_pricing_hash=sha256_json(shared.protocol_prices(protocol())))
    shared.require(str(approval.credential_file.resolve()) == plan.packet["credential_path"],
                   "wrong credential file")
    return shared._collect_validated(plan, approval, protocol=protocol(),
                                    adapter_factory=adapter_factory, clock=monotonic,
                                    checkpoint=lambda _: None)
