"""Prepare or explicitly authorize one unhinted, newly funded continuation."""
from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path

from diagnostics import checkpoint_comparison as live
from diagnostics import checkpoint_continuation as continuation
from diagnostics import post_edit_budget_checkpoint as checkpoint
from diagnostics.decision_sampler import require
from diagnostics.declaration_checkpoint import Source, disjoint
from patchloop.artifacts import ArtifactStore
from patchloop.dev import runner
from patchloop.dev.cost import DevCostLedger, pricing_for_model, usd_to_nanos
from patchloop.dev.state import DevJournal
from patchloop.runtime import repository_root
from patchloop.util import canonical_json, sha256_bytes


def controls(packet_path, packet_hash, env_file, result_root):
    checkpoint.validate(packet_path, packet_hash)
    packet = json.loads(packet_path.read_bytes())
    source = Source.from_record(packet["source"])
    envelope = DevJournal(source.root, source.run_id).load_envelope()
    require(sha256_bytes(str(env_file.resolve()).encode()) == envelope.credential_file_path_hash,
            "credential path changed")
    disjoint(result_root.resolve(), (repository_root(), source.root, packet_path.parent,
                                    source.public_path.parent))
    return {"schema": "post-edit-budget-continuation-v1", "official": False,
            "paid_execution_authorized": False,
            "packet": str(packet_path.resolve()), "packet_hash": packet_hash,
            "task": str(source.public_path.resolve()), "model": envelope.model,
            "reasoning_effort": envelope.reasoning_effort,
            "max_output_tokens": envelope.max_output_tokens,
            "env_file": str(env_file.resolve()), "repeat": 1,
            "new_cap_nanos": packet["new_cap_nanos"],
            "result_root": str(result_root.resolve()),
            "selected_request_hash": packet["selected_request_hash"],
            "verification_scope_cue": packet.get(checkpoint.SCOPE_FIELD),
            "scope_cue_timing": packet.get("scope_cue_timing", "first-input"),
            "remaining_budget": packet["checkpoint"]["remaining_budget"],
            "sdk_retries": 0, "automatic_resume": False,
            "runtime_hash": packet["runtime_hash"],
            "implementation": checkpoint.implementation_hashes()}


def prepare(packet_path, packet_hash, env_file, result_root, output):
    plan = controls(packet_path, packet_hash, env_file, result_root)
    source = Source.from_record(json.loads(packet_path.read_bytes())["source"])
    disjoint(output.resolve(), (repository_root(), source.root, packet_path.parent,
                                result_root.resolve(), source.public_path.parent))
    runner._require_tracked_clean_paths(repository_root(), list(checkpoint.IMPLEMENTATION))
    output.mkdir()
    raw = (canonical_json(plan) + "\n").encode()
    (output / "manifest.json").write_bytes(raw)
    journal = DevJournal(output, "run_dev_posteditlivepreparation")
    journal.append("continuation_prepared", {"manifest_hash": sha256_bytes(raw), "plan": plan})
    preflight = live.check_environment(packet_path, packet_hash, env_file)
    journal.append("environment_checked", preflight)
    (output / "preflight.json").write_text(canonical_json(preflight) + "\n", encoding="utf-8")
    return {"manifest": str(output / "manifest.json"), "manifest_hash": sha256_bytes(raw),
            "preflight": preflight, "new_cap_usd": str(Decimal(plan["new_cap_nanos"]) / 10**9)}


def collect(manifest_path, approved_hash, approved_cap_usd):
    raw = manifest_path.read_bytes()
    require(sha256_bytes(raw) == approved_hash, "approved manifest hash differs")
    plan = json.loads(raw)
    require(usd_to_nanos(approved_cap_usd) == plan["new_cap_nanos"], "approved cap differs")
    packet_path, env_file, root = map(Path, (plan["packet"], plan["env_file"], plan["result_root"]))
    require(plan == controls(packet_path, plan["packet_hash"], env_file, root),
            "manifest controls changed")
    runner._require_tracked_clean_paths(repository_root(), list(checkpoint.IMPLEMENTATION))
    root.mkdir()  # Single use, including preflight/transport failure; never auto-resume.
    journal = DevJournal(root, "run_dev_posteditcontinuation")
    store = ArtifactStore(root / "artifacts")
    ledger = DevCostLedger(approved_cap_usd, pricing_for_model(plan["model"]))
    row = {"status": "NOT_RUN", "billing_known": True}
    with journal.execution_lock():
        journal.append("continuation_authorized", {"manifest_hash": approved_hash, "plan": plan})
        preflight = live.check_environment(packet_path, plan["packet_hash"], env_file)
        journal.append("environment_checked", preflight)
        branch = None
        if preflight["status"] == "READY":
            try:
                branch = continuation.restore(packet_path, plan["packet_hash"], root / "A1",
                                              "A", mode="live-checkpoint")
                branch.request = branch.request.model_copy(update={"env_file": env_file})
                require(runner._credential_file_path_hash(branch.request)
                        == branch.envelope.credential_file_path_hash, "credential path changed")
                row = live.run_branch(branch, ledger, journal, store, "A1")
            except Exception as exc:
                known = branch is None or runner._provider_usage_failure(branch.journal) is None
                row = {"status": "COLLECTOR_FAILED", "error_type": type(exc).__name__,
                       "billing_known": known, "stop_remaining": True}
        receipt = {"official": False, "manifest_hash": approved_hash, "row": row,
                   "preflight_status": preflight["status"],
                   "new_cost_nanos": ledger.spent_nanos if row["billing_known"] else None,
                   "recorded_new_cost_nanos": ledger.spent_nanos,
                   "new_cap_nanos": ledger.cap_nanos, "historical_allocations_reopened": False,
                   "fresh_solve": False, "efficacy_claim": "NOT_ESTABLISHED"}
        journal.append("continuation_finished", receipt)
        (root / "result.json").write_text(canonical_json(receipt) + "\n", encoding="utf-8")
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    for key in ("packet", "env-file", "result-root", "output"):
        prep.add_argument("--" + key, type=Path, required=True)
    prep.add_argument("--packet-hash", required=True)
    run = sub.add_parser("collect")
    run.add_argument("--manifest", type=Path, required=True)
    run.add_argument("--approved-manifest-hash", required=True)
    run.add_argument("--approved-new-cap-usd", type=Decimal, required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        result = prepare(args.packet, args.packet_hash, args.env_file,
                         args.result_root, args.output)
    else:
        result = collect(args.manifest, args.approved_manifest_hash, args.approved_new_cap_usd)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
