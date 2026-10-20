"""Provider-free saved-submission assessment after a stopped caller A/B study.

The original packet/journal/audit remain read-only. This is a separate evaluation,
not a retry of the frozen study and not a new solve. No action runs on import.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from diagnostics import caller_uptake as panel
from diagnostics import caller_uptake_execution as execution
from diagnostics import caller_uptake_grading as grading
from diagnostics.positive_verification_panel import require, save
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact
from patchloop.dev.contracts import DevRunRequest
from patchloop.dev.evaluation_completion import load_evaluation_completion
from patchloop.dev.state import DevJournal
from patchloop.runtime import git_commit, repository_root, runtime_content_hash
from patchloop.util import canonical_json, sha256_json

JOURNAL = "run_dev_callersavedassessment"
REPAIRED = {"diagnostics/caller_uptake_execution.py", "diagnostics/swebench_lite_native.py"}


def validate_source(root, digest):
    """Keep frozen input/oracle/runtime gates; explicitly bind the repaired operator."""
    packet = json.loads((root / "manifest.json").read_bytes())
    require(sha256_json(packet) == digest and packet["paid_authorized"] is False,
            "original packet changed")
    require(packet["runtime_hash"] == runtime_content_hash()
            and packet["invariants"] == panel.invariants(), "runtime or budgets changed")
    current = panel.bindings()
    require(current.keys() == packet["implementation"].keys() and all(
        current[name] == expected for name, expected in packet["implementation"].items()
        if name not in REPAIRED), "unrelated operator or oracle changed")
    for key in ("validation", "preparation", "pricing_evidence", "rubric"):
        panel.read_ref(packet[key])
    for ref in json.loads(panel.read_ref(packet["preparation"]))["files"]:
        panel.read_ref(ref)
    for case, ref in packet["programs"].items():
        panel.read_ref(ref)
        require(ref["hash"] == grading.PROGRAMS[case], "assessment program changed")
    require(packet["native_identity"] == panel.portfolio_dev20.native_identity()
            and packet["native_input"] == panel.native_input(), "native identity changed")
    panel.read_ref(packet["native_input"]["rows"])  # Opaque bytes, never audit/solver context.
    deps, live = Path(packet["dependencies_root"]), Path(packet["live_root"])
    require(packet["environments"] == panel.environments(deps, live), "environment changed")
    require(packet["rows"] == [{"row_id": label, "arm": label[0], "request":
        panel.request(deps, live, label).model_dump(mode="json")} for label in panel.ORDER],
        "original roster or settings changed")
    journal = DevJournal(root, panel.JOURNAL)
    events = journal.events()
    require(events[0]["event_type"] == "packet_frozen"
            and events[0]["payload"]["packet_hash"] == digest, "original journal differs")
    kinds = [e["event_type"] for e in events]
    require(kinds.count("collection_closed") == kinds.count("audit_sealed")
            == kinds.count("assessment_stopped") == 1
            and "caller_assessment_started" not in kinds and "study_closed" not in kinds,
            "requires a sealed collection stopped before its first assessment")
    seal = next(e["payload"] for e in events if e["event_type"] == "audit_sealed")
    annotations = json.loads(ArtifactStore(root / "artifacts").read_bytes(
        Artifact.model_validate(seal["annotations"])))
    allowed = json.loads(panel.read_ref(seal["index"]))["files"]
    require({r["row_id"]: grading.validate_annotation(r, allowed) for r in annotations["rows"]}
            == seal["uptake"], "sealed uptake differs")
    collection = json.loads((root / "collection.json").read_bytes())
    require(collection["rows"] == [e["payload"] for e in events if e["event_type"] == "row_sealed"]
            and [r["row_id"] for r in collection["rows"]] == list(panel.ORDER)
            and collection["stopped"] is False, "collection lineage differs")
    by_id = {r["row_id"]: r for r in packet["rows"]}
    submissions = []
    for bound in collection["rows"]:
        value = json.loads(ArtifactStore(root / "sealed").read_bytes(
            Artifact.model_validate(bound["sealed"])))
        req = DevRunRequest.model_validate(by_id[bound["row_id"]]["request"])
        execution.due_receipts(None, value, req)
        run = value["result"]["runs"][0]
        patch_hash = run.get("artifact_hashes", {}).get("submitted_patch")
        if patch_hash:
            source_journal = DevJournal(req.state_root, run["run_id"])
            store = ArtifactStore(req.state_root / "artifacts")
            completion = load_evaluation_completion(source_journal, store,
                                                    source_journal.load_envelope())
            artifact = completion.artifacts["submitted_patch"]
            require(bool(store.read_bytes(artifact)) and artifact.content_hash == patch_hash,
                    "missing or changed saved submission")
            workspace = req.state_root / "workspaces" / run["run_id"] / "repo"
            require(execution.WorkspaceManager.diff_summary(workspace).patch_hash == patch_hash,
                    "saved submission workspace changed")
            submissions.append({"row_id": bound["row_id"], "submitted_diff": patch_hash,
                                "artifact": artifact.model_dump(mode="json")})
    refs = [panel.file_ref(root / name) for name in ("manifest.json", "collection.json")]
    refs.extend([panel.file_ref(journal.path), seal["index"],
                 {"path": seal["annotations"]["path"],
                  "hash": seal["annotations"]["content_hash"]}])
    return packet, seal, submissions, refs


def assess_saved(root, digest, output, *, expected_submissions, authorization):
    require(bool(authorization.strip()), "record explicit local assessment authorization")
    require(not output.exists() and not output.resolve().is_relative_to(repository_root()),
            "fresh external follow-up root required; no retry")
    require(not output.resolve().is_relative_to(root.resolve())
            and not root.resolve().is_relative_to(output.resolve()), "independent output root")
    packet, seal, submissions, refs = validate_source(root, digest)
    require(expected_submissions > 0 and len(submissions) == expected_submissions,
            "submitted roster differs from authorized scope")
    live = Path(packet["live_root"]).resolve()
    require(not output.resolve().is_relative_to(live)
            and not live.is_relative_to(output.resolve()), "output overlaps original solver state")
    names = [*panel.bindings(), "diagnostics/caller_uptake_followup.py",
             "tests/test_caller_uptake_followup.py", "tests/test_swebench_lite_native.py",
             ".agent/caller-uptake-followup.md"]
    panel.runner._require_tracked_clean_paths(repository_root(), names)
    manifest = {"schema": "caller-uptake-saved-assessment-v1", "authorization": authorization,
        "original_packet_hash": digest, "original_head": packet["head"], "head": git_commit(),
        "runtime_hash": runtime_content_hash(), "inputs": refs, "submissions": submissions,
        "implementation": [panel.file_ref(repository_root() / name) for name in names],
        "invariants": packet["invariants"], "programs": packet["programs"],
        "provider_calls": 0, "input_count_calls": 0, "paid_cap_usd": "0",
        "max_caller_probes": expected_submissions * 2,
        "max_native_assessments": expected_submissions,
        "original_frozen_study_retried": False, "official": False, "claim_eligible": False}
    output.mkdir(parents=True)
    save(output, "manifest.json", manifest)
    journal = DevJournal(output, JOURNAL)
    with journal.execution_lock():
        journal.append("saved_assessment_started", {"manifest": panel.file_ref(
            output / "manifest.json"), "packet_hash": digest})
        try:
            return execution._assess_rows(root, output, packet, journal, seal, metadata={
                "execution_kind": "saved_patch_followup", "original_frozen_study_retried": False,
                "provider_calls": 0, "input_count_calls": 0, "favorable_local_signal": False})
        finally:
            for ref in refs:
                panel.read_ref(ref)
            journal.append("original_evidence_preserved", {"inputs": refs})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--hash", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--expected-submissions", required=True, type=int)
    parser.add_argument("--authorization", required=True)
    args = parser.parse_args()
    result = assess_saved(args.source, args.hash, args.output,
        expected_submissions=args.expected_submissions, authorization=args.authorization)
    print(canonical_json({k: v for k, v in result.items() if k != "rows"}), flush=True)


if __name__ == "__main__":
    main()
