"""Single-use matched expectation-review pair with fresh shared and row caps."""
from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path

from diagnostics import checkpoint_comparison as live
from diagnostics import checkpoint_continuation as continuation
from diagnostics import expectation_review_checkpoint as checkpoint
from diagnostics import expectation_review_continuation as review
from diagnostics.decision_sampler import require
from diagnostics.declaration_checkpoint import Source, disjoint
from diagnostics.post_edit_budget_checkpoint import project as fund
from patchloop.artifacts import ArtifactStore
from patchloop.dev import runner
from patchloop.dev.cost import DevCostLedger, pricing_for_model, usd_to_nanos
from patchloop.dev.state import DevJournal
from patchloop.runtime import repository_root
from patchloop.util import canonical_json, sha256_bytes, sha256_json

IMPLEMENTATION = (
    "diagnostics/expectation_review_collector.py",
    "diagnostics/expectation_review_checkpoint.py",
    "diagnostics/expectation_review_continuation.py",
    "diagnostics/post_edit_budget_checkpoint.py",
    "diagnostics/checkpoint_continuation.py",
    "diagnostics/checkpoint_comparison.py",
    "diagnostics/completion_advice_checkpoint.py",
    ".agent/expectation-review-collector.md",
)


def controls(packet_path, packet_hash, env_file, result_root, new_cap_usd):
    checkpoint.validate(packet_path, packet_hash)
    packet = json.loads(packet_path.read_bytes())
    source = Source.from_record(packet["source"])
    envelope = DevJournal(source.root, source.run_id).load_envelope()
    require(sha256_bytes(str(env_file.resolve()).encode()) == envelope.credential_file_path_hash,
            "credential path changed")
    disjoint(result_root.resolve(), (repository_root(), source.root, packet_path.parent,
                                    source.public_path.parent))
    cap = usd_to_nanos(new_cap_usd)
    require(cap > 0 and cap % 2 == 0, "positive evenly divisible cap required")
    original, _ = checkpoint.load(source, packet["checkpoint"]["turn_id"])
    baseline = fund(original, cap // 2)
    return {"schema": "expectation-review-live-v1", "official": False,
            "paid_execution_authorized": False,
            "packet": str(packet_path.resolve()), "packet_hash": packet_hash,
            "task": str(source.public_path.resolve()), "model": envelope.model,
            "reasoning_effort": envelope.reasoning_effort,
            "max_output_tokens": envelope.max_output_tokens,
            "env_file": str(env_file.resolve()), "repeat": 2, "order": ["A1", "B1"],
            "new_cap_nanos": cap, "row_new_cap_nanos": cap // 2,
            "result_root": str(result_root.resolve()),
            "first_request_hashes": {"A1": sha256_json(baseline),
                                     "B1": sha256_json(checkpoint.project(baseline))},
            "sdk_retries": 0, "automatic_resume": False,
            "runtime_hash": packet["runtime_hash"],
            "implementation": {p: sha256_bytes((repository_root() / p).read_bytes())
                               for p in IMPLEMENTATION}}


def prepare(packet_path, packet_hash, env_file, result_root, output, new_cap_usd):
    plan = controls(packet_path, packet_hash, env_file, result_root, new_cap_usd)
    source = Source.from_record(json.loads(packet_path.read_bytes())["source"])
    disjoint(output.resolve(), (repository_root(), source.root, packet_path.parent,
                                result_root.resolve(), source.public_path.parent))
    runner._require_tracked_clean_paths(repository_root(), list(IMPLEMENTATION))
    output.mkdir()
    raw = (canonical_json(plan) + "\n").encode()
    (output / "manifest.json").write_bytes(raw)
    journal = DevJournal(output, "run_dev_reviewlivepreparation")
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
    require(plan == controls(packet_path, plan["packet_hash"], env_file, root, approved_cap_usd),
            "manifest controls changed")
    runner._require_tracked_clean_paths(repository_root(), list(IMPLEMENTATION))
    root.mkdir()  # Single use, including preflight/transport failure; never auto-resume.
    journal = DevJournal(root, "run_dev_reviewcomparison")
    store = ArtifactStore(root / "artifacts")
    ledger = DevCostLedger(approved_cap_usd, pricing_for_model(plan["model"]))
    rows = [{"row": label, "status": "NOT_RUN", "billing_known": True}
            for label in plan["order"]]
    with journal.execution_lock():
        journal.append("continuation_authorized", {"manifest_hash": approved_hash, "plan": plan})
        preflight = live.check_environment(packet_path, plan["packet_hash"], env_file)
        journal.append("environment_checked", preflight)
        if preflight["status"] == "READY":
            for index, label in enumerate(plan["order"]):
                branch = None
                try:
                    branch = continuation.restore(
                        packet_path, plan["packet_hash"], root / label, label[0],
                        mode="live-checkpoint", review_new_cap_nanos=plan["row_new_cap_nanos"])
                    require(sha256_json(branch.selected) == plan["first_request_hashes"][label],
                            "funded request differs from frozen plan")
                    branch.request = branch.request.model_copy(update={"env_file": env_file})
                    require(runner._credential_file_path_hash(branch.request)
                            == branch.envelope.credential_file_path_hash, "credential path changed")
                    with review.inputs(branch):
                        row = live.run_branch(branch, ledger, journal, store, label)
                except Exception as exc:
                    known = branch is None or runner._provider_usage_failure(branch.journal) is None
                    row = {"row": label, "status": "COLLECTOR_FAILED",
                           "error_type": type(exc).__name__, "error": str(exc),
                           "billing_known": known, "stop_remaining": True}
                rows[index] = row
                journal.append("row_finished", row)
                if row["stop_remaining"]:
                    break
        known = all(row["billing_known"] for row in rows)
        receipt = {"official": False, "manifest_hash": approved_hash, "rows": rows,
                   "preflight_status": preflight["status"],
                   "new_cost_nanos": ledger.spent_nanos if known else None,
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
    prep.add_argument("--new-cap-usd", type=Decimal, required=True)
    run = sub.add_parser("collect")
    run.add_argument("--manifest", type=Path, required=True)
    run.add_argument("--approved-manifest-hash", required=True)
    run.add_argument("--approved-new-cap-usd", type=Decimal, required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        result = prepare(args.packet, args.packet_hash, args.env_file,
                         args.result_root, args.output, args.new_cap_usd)
    else:
        result = collect(args.manifest, args.approved_manifest_hash, args.approved_new_cap_usd)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
