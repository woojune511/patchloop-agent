"""Provider-free, one-field-family ablation of retained prior public decisions."""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

from diagnostics import evidence_context_design as base
from patchloop.artifacts import ArtifactStore
from patchloop.dev.state import DevJournal
from patchloop.runtime import repository_root
from patchloop.util import canonical_json, sha256_bytes, sha256_json

require = base.shared.require
SCHEMA = "prior-decision-preparation-v1"
KEYS = {"turn_decision", "plan_update"}


def scan(value, path="$", depth=0):
    """Inspect containers and JSON-encoded tool outputs without executing their text."""
    require(depth < 100, "nested input exceeds diagnostic inspection depth")
    yield path, value
    if isinstance(value, dict):
        for key, child in value.items():
            yield from scan(child, f"{path}.{key}", depth + 1)
    elif isinstance(value, list):
        for i, child in enumerate(value):
            yield from scan(child, f"{path}[{i}]", depth + 1)
    elif isinstance(value, str):
        try:
            decoded = json.loads(value)
        except ValueError:
            return
        if isinstance(decoded, (dict, list)):
            yield from scan(decoded, path + "::<json>", depth + 1)


def project(original):
    require(original.get("reviewer_instruction") == base.QUESTION
            and set(original.get("data", {})) == {"evidence"}, "original reduced view required")
    a, b = copy.deepcopy(original), copy.deepcopy(original)
    cards = b["data"]["evidence"]["recent_attempt_result_next_question"]
    removed = []
    for index, card in enumerate(cards):
        if "turn_decision" in card:
            decision = card.pop("turn_decision")
            require(isinstance(decision, dict), "decision object required")
            removed.append({"card_index": index, "action_id": card["action_id"],
                            "turn_decision": decision})
    require(removed, "no prior decisions to compare")
    restored = copy.deepcopy(b)
    for record in removed:
        restored["data"]["evidence"]["recent_attempt_result_next_question"][
            record["card_index"]]["turn_decision"] = record["turn_decision"]
    require(restored == original, "non-target evidence changed")
    nodes = list(scan(b))
    remaining = [f"{path}.{key}" for path, value in nodes if isinstance(value, dict)
                 for key in value if key in KEYS]
    require(not remaining, "duplicate structured decision remains: " + ", ".join(remaining))
    explanations = [text for r in removed for key, text in r["turn_decision"].items()
                    if key in {"basis", "plan_update"} and isinstance(text, str) and text.strip()]
    duplicates = [path for path, value in nodes if isinstance(value, str)
                  and any(" ".join(text.split()) in " ".join(value.split())
                          for text in explanations)]
    require(not duplicates, "duplicate explanation text remains: " + ", ".join(duplicates))
    return {"A": a, "B": b}, {
        "removed": removed,
        "only_removed_paths": [
            f"$.data.evidence.recent_attempt_result_next_question[{r['card_index']}].turn_decision"
            for r in removed],
        "preserved_remainder_hash": sha256_json(b), "reconstruction_matches_original": True,
        "structured_decision_copies_remaining": 0, "exact_explanation_copies_remaining": 0,
        "duplicate_audit_limit": "Containers and JSON strings plus whitespace-normalized exact "
                                 "explanations; semantic paraphrases and other advice may remain.",
        "utf8_bytes": {arm: len(canonical_json(v).encode()) for arm, v in {"A": a, "B": b}.items()},
    }


def hashes():
    return {**base.implementation_hashes(), **{str(p.resolve()): sha256_bytes(p.read_bytes())
            for p in (Path(__file__), repository_root() / ".agent/prior-decision-design.md")}}


def inputs(source_path, source_hash):
    source_path = Path(source_path).resolve()
    require(sha256_bytes(source_path.read_bytes()) == source_hash, "source packet changed")
    base.validate(source_path)
    packet = json.loads(source_path.read_bytes())
    require(set(packet["cases"]) == {"C1", "C2", "C3", "C4"}, "four frozen cases required")
    projected = {}
    for case, saved in packet["cases"].items():
        ref = saved["views"]["B"]
        raw = Path(ref["path"]).read_bytes()
        require(sha256_bytes(raw) == ref["content_hash"] and len(raw) == ref["size_bytes"],
                "source view changed")
        views, audit = project(json.loads(raw))
        projected[case] = (views, {**audit, "source_view_hash": ref["content_hash"],
                                  "source_receipt": saved["receipt"]})
    return projected


def prepare(source_path, source_hash, root):
    root = Path(root).resolve()
    require(not root.exists() and not root.is_relative_to(repository_root()),
            "fresh external root required")
    projected = inputs(source_path, source_hash)
    root.mkdir(parents=True)
    store = ArtifactStore(root / "artifacts")
    cases = {c: {"audit": audit, "views": {
        a: store.put_json(v).model_dump(mode="json") for a, v in views.items()}}
        for c, (views, audit) in projected.items()}
    packet = {"schema": SCHEMA, "official": False, "status": "PREPARED_NOT_EXECUTABLE",
              "dispatch_enabled": False, "provider_calls": 0, "source_path": str(
                  Path(source_path).resolve()), "source_hash": source_hash,
              "implementation_hashes": hashes(), "cases": cases,
              "question_hash": sha256_json(base.QUESTION),
              "arm_definition": "A=previous reduced-context B; B=that input minus retained "
                                "attempt-card turn_decision objects only. Other advice stays.",
              "limits": "No inference about independent solving, all framing, length alone, "
                        "or runtime adoption. No API requests, collector or paid authorization."}
    with (root / "packet.json").open("x", encoding="utf-8") as f:
        f.write(canonical_json(packet))
    DevJournal(root, "run_dev_priordecisionprep").append("comparison_prepared", {
        "packet_artifact": store.put_json(packet).model_dump(mode="json")})
    return sha256_bytes((root / "packet.json").read_bytes())


def validate(path):
    path = Path(path)
    packet = json.loads(path.read_bytes())
    require(packet["schema"] == SCHEMA and packet["status"] == "PREPARED_NOT_EXECUTABLE"
            and packet["dispatch_enabled"] is False and packet["provider_calls"] == 0
            and packet["implementation_hashes"] == hashes()
            and packet["question_hash"] == sha256_json(base.QUESTION), "design changed")
    projected = inputs(packet["source_path"], packet["source_hash"])
    require(set(packet["cases"]) == set(projected), "case set changed")
    for case, (views, audit) in projected.items():
        saved = packet["cases"][case]
        require(saved["audit"] == audit and set(saved["views"]) == {"A", "B"}, "audit changed")
        for arm, ref in saved["views"].items():
            raw = base.shared.read_source_artifact(path.parent, ref)
            require(json.loads(raw) == views[arm], "projection changed")
    return {"cases": 4, "views": 8, "provider_calls": 0,
            "removed_decisions": sum(len(a["removed"]) for _, a in projected.values()),
            "only_target_fields_changed": True, "original_source_validated": True}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    p = commands.add_parser("prepare")
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--source-hash", required=True)
    p.add_argument("--root", type=Path, required=True)
    p = commands.add_parser("validate")
    p.add_argument("--packet", type=Path, required=True)
    args = parser.parse_args()
    print(canonical_json(prepare(args.source, args.source_hash, args.root)
                         if args.command == "prepare" else validate(args.packet)))
