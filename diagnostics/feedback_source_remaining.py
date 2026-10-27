"""Finish the one unstarted R1 after the documented, settled R0 empty-diff stop.

This is not a general restart facility. The original evidence stays immutable;
only the exact unstarted arm is admitted, with its original request and total cap.
"""
from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path

from diagnostics import feedback_source as f

ORIGINAL = Path("C:/pt/feedback-source-plan-v1/manifest.json")
ORIGINAL_HASH = "sha256:844256532293cfdeaf8ecdc3f1a3924dd8eb1bdcf9381d1df967fbc7e58b228e"
PRIOR = Path("C:/pt/feedback-source-live-v1")
RESULT_ROOT = Path("C:/pt/feedback-source-remaining-live-v1")
FROZEN = {
    "runs/run_dev_feedbacksourcecomparison.jsonl":
        "sha256:3f01942c1aabe4459a9d9b9752c793e19f2ee3b4491838cb17aea95ffd353fa5",
    "R0/runs/run_dev_feedbacksourcemodel.jsonl":
        "sha256:8f2700cd3ebd9cd2bc9b8378dfc4e24d4bf4e1fd559489628506be75f98ba873",
    "R0/acceptance/summary.json":
        "sha256:8e1d7ece141e0678757f4d35e61ead58693fb0f01acad9f6d065259b2c52f174",
}


def assert_same_conditions(original, updated):
    for key in ("scope", "runtime_hash", "credential_file", "bundle_hash",
                "first_request_hashes", "interpretation"):
        f.require(original[key] == updated[key], f"remaining-arm condition changed: {key}")
    before = {entry["path"]: entry for entry in original["bindings"]}
    after = {entry["path"]: entry for entry in updated["bindings"]}
    f.require(before.keys() == after.keys(), "bound input set changed")
    changed = [path for path in before if before[path] != after[path]]
    f.require(changed == [str(Path(f.__file__).resolve())],
              "changes extend beyond the documented no-diff handling")


def prior_result():
    f.require(f.sha256_bytes(ORIGINAL.read_bytes()) == ORIGINAL_HASH,
              "original plan changed")
    f.require(not (PRIOR / "R1").exists(), "R1 was already started")
    for relative, digest in FROZEN.items():
        f.require(f.sha256_bytes((PRIOR / relative).read_bytes()) == digest,
                  "settled original evidence changed")
    events = f.DevJournal(PRIOR, "run_dev_feedbacksourcecomparison").events()
    model = f.DevJournal(PRIOR / "R0", "run_dev_feedbacksourcemodel")
    model_events = model.events()
    usage = model.provider_usage()
    started = [event["payload"]["call_id"] for event in model_events
               if event["event_type"] == "provider_call_started"]
    f.require(len(started) == len(set(started)) == len(usage) == 7
              and set(started) == {row["call_id"] for row in usage}
              and model.unresolved_input_count() is None,
              "original provider or count outcome is unsettled")
    row = next(event["payload"].copy() for event in events
               if event["event_type"] == "model_row_finished")
    checks = next(event["payload"].copy() for event in events
                  if event["event_type"] == "candidate_ready_for_evaluation")
    checks.pop("arm")
    summary = json.loads((PRIOR / "R0/acceptance/summary.json").read_bytes())
    f.require(row["arm"] == "R0" and row["billing_known"]
              and not row["stop_remaining"] and row["new_mutations"] == 1
              and row["candidate_diff_hash"] == f.host.EMPTY_DIFF
              and sum(item["cost_nanos"] for item in usage) == row["new_cost_nanos"]
              and summary["status"] == "PRECHECK_FAILED"
              and summary["evaluator_dispatches"] == 0
              and summary["candidate_patch_hash"] == f.host.EMPTY_DIFF,
              "original stop is not the known settled empty-diff case")
    diff = f.WorkspaceManager.diff_summary(PRIOR / "R0/workspaces/saved/repo")
    f.require(diff.patch_hash == f.host.EMPTY_DIFF and not diff.untracked_files,
              "original candidate changed")
    row.update(public_checks=checks, acceptance=summary,
               outcome_classification="NO_CANDIDATE_DIFF",
               evidence_root=str(PRIOR / "R0"))
    return row, usage


def prepare(output, result_root):
    f.require(result_root.resolve() == RESULT_ROOT.resolve(),
              "this incident has one fixed remaining-arm directory")
    prior_result()
    original = json.loads(ORIGINAL.read_bytes())
    receipt = f.prepare(output, result_root, Path(original["credential_file"]))
    updated = json.loads((output / "manifest.json").read_bytes())
    assert_same_conditions(original, updated)
    plan = {"schema": "feedback-source-unstarted-r1-v1", "official": False,
            "manifest": f.file_binding(output / "manifest.json"),
            "operator": f.file_binding(Path(__file__)),
            "original_manifest_hash": ORIGINAL_HASH, "prior_evidence": FROZEN,
            "remaining_arm": "R1", "total_cap_usd": "2.40",
            "authorization": "Complete the current user-authorized pair; no R0 retry, "
                "new repetition or increased cap. Original evidence is preserved."}
    target = output / "remaining.json"
    target.write_text(f.canonical_json(plan) + "\n", encoding="utf-8")
    receipt.update(remaining_manifest=str(target),
                   remaining_manifest_hash=f.sha256_bytes(target.read_bytes()))
    f.DevJournal(output, "run_dev_feedbacksourceremainingprep").append("prepared", receipt)
    return receipt


def collect(remaining, approved_hash, approved_cap_usd):
    f.require(approved_cap_usd == f.PROFILE.invocation_cap
              and f.sha256_bytes(remaining.read_bytes()) == approved_hash,
              "remaining-arm authorization differs")
    plan = json.loads(remaining.read_bytes())
    f.require(plan["operator"] == f.file_binding(Path(__file__))
              and plan["manifest"] == f.file_binding(plan["manifest"]["path"]),
              "remaining-arm binding changed")
    manifest = Path(plan["manifest"]["path"])
    current, loaded = f.validate(manifest, plan["manifest"]["hash"])
    assert_same_conditions(json.loads(ORIGINAL.read_bytes()), current)
    prior, usage = prior_result()
    relative = [Path(row["path"]).relative_to(f.repository_root()).as_posix()
                for row in current["bindings"]
                if Path(row["path"]).is_relative_to(f.repository_root())]
    f.loop.runner._require_tracked_clean_paths(f.repository_root(),
        [*f.runtime_content_paths(), *relative,
         Path(__file__).relative_to(f.repository_root()).as_posix()])
    root = Path(current["result_root"])
    f.require(root.resolve() == RESULT_ROOT.resolve(),
              "this incident has one fixed remaining-arm directory")
    root.mkdir()  # Single use; the interrupted original and this directory are never restarted.
    journal = f.DevJournal(root, "run_dev_feedbacksourceremaining")
    group = f.DevCostLedger(approved_cap_usd, f.pricing_for_model(f.loop.MODEL))
    group.restore_settled_usage(usage)
    journal.append("remaining_arm_started", {"remaining_manifest_hash": approved_hash,
        "prior_cost_nanos": group.spent_nanos, "total_cap_usd": str(approved_cap_usd),
        "original_manifest_hash": ORIGINAL_HASH, "original_row": prior})
    try:
        gateway = f.saved_gateway(loaded, root / "R1", "R1")
        key = f.loop.load_exact_openai_api_key(Path(current["credential_file"]))
        adapter = f.loop.OpenAIResponsesAdapter(f.loop.config(), api_key=key)
        del key
        try:
            row = {"arm": "R1", **f.loop.run_model(loaded, "R1", gateway, adapter, group,
                first_hash=current["first_request_hashes"]["R1"], profile=f.PROFILE,
                request_builder=f.request_payload)}
        finally:
            adapter.client.close()
        journal.append("model_row_finished", row)
        if not row["stop_remaining"] and row["terminal"] == "CANDIDATE_PRODUCED":
            checks = f.host.public_checks(loaded, gateway, root / "R1/public")
            row["public_checks"] = checks
            journal.append("candidate_ready_for_evaluation", {"arm": "R1", **checks})
            row["acceptance"] = f.acceptance(gateway, root / "R1/acceptance",
                                             checks["regression_passed"])
            row["task_acceptance"] = row["acceptance"]["acceptance"]
        journal.append("row_finished", row)
    except BaseException as exc:
        journal.append("collection_interrupted", {"error_type": type(exc).__name__,
                                                   "resume_allowed": False})
        raise
    result = {"official": False, "rows": [prior, row], "cost_nanos": group.spent_nanos,
              "allocation_closed": True, "interpretation": current["interpretation"],
              "recovery": "R0 known empty-diff stop retained; only unstarted R1 executed."}
    (root / "result.json").write_text(f.canonical_json(result) + "\n", encoding="utf-8")
    journal.append("closed", {"artifact": f.ArtifactStore(root / "artifacts")
                             .put_json(result).model_dump(mode="json")})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prep = commands.add_parser("prepare")
    prep.add_argument("--output", type=Path, required=True)
    prep.add_argument("--result-root", type=Path, required=True)
    run = commands.add_parser("collect")
    run.add_argument("--remaining", type=Path, required=True)
    run.add_argument("--approved-hash", required=True)
    run.add_argument("--approved-cap-usd", type=Decimal, required=True)
    args = vars(parser.parse_args())
    command = args.pop("command")
    print(f.canonical_json(globals()[command](**args)))


if __name__ == "__main__":
    main()
