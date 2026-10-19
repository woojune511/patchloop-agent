"""Freeze and run the twelve inherited-budget branches; separate audit from grades."""
from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from diagnostics import caller_evidence_grading as grading
from diagnostics import (
    caller_uptake,
    caller_uptake_execution,
    checkpoint_comparison,
    portfolio_dev20,
    probe_recheck_panel,
    saved_caller_checkpoint,
)
from diagnostics import checkpoint_continuation as continuation
from diagnostics.cleanup_information_checkpoint import ForkStore
from diagnostics.decision_sampler import require
from diagnostics.declaration_checkpoint import Source, disjoint
from diagnostics.positive_verification_panel import save
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact
from patchloop.dev import runner
from patchloop.dev.evaluation_completion import load_evaluation_completion
from patchloop.dev.state import DevJournal
from patchloop.runtime import git_commit, repository_root, runtime_content_hash
from patchloop.util import sha256_bytes, sha256_json

JOURNAL = "run_dev_callerevidence"
NOTE = ".agent/plans/caller-evidence-checkpoint.md"
file_ref, read_ref = caller_uptake.file_ref, caller_uptake.read_ref


def bindings():
    names = {*checkpoint_comparison.IMPLEMENTATION, NOTE,
             "diagnostics/caller_evidence_execution.py", "diagnostics/caller_evidence_grading.py",
             "diagnostics/caller_uptake.py", "diagnostics/caller_uptake_execution.py",
             "diagnostics/caller_uptake_grading.py", "diagnostics/portfolio_dev20.py",
             "diagnostics/probe_recheck_panel.py", "diagnostics/swebench_lite_native.py",
             "diagnostics/positive_verification_panel.py",
             "tests/test_saved_caller_checkpoint.py", "tests/test_caller_evidence_grading.py",
             "tests/test_caller_evidence_execution.py"}
    return {name: sha256_bytes((repository_root() / name).read_bytes()) for name in sorted(names)}


def rows_for(plan):
    packet, source, envelope = checkpoint_comparison.source_state(
        Path(plan["packet"]), plan["packet_hash"])
    require(packet["schema"] == saved_caller_checkpoint.SCHEMA, "saved caller packet required")
    return [{"row_id": label, "arm": label[0], "request": continuation.restored_request(
        source, envelope, Path(plan["result_root"]) / label).model_copy(
            update={"env_file": Path(plan["env_file"])}).model_dump(mode="json")}
            for label in plan["order"]]


def freeze(root, *, packet, env_file, live, validation, preparation, pricing):
    plan = checkpoint_comparison.controls(Path(packet["path"]), packet["hash"], env_file, live)
    disjoint(root.resolve(), (repository_root(), Path(packet["path"]).parent, live.resolve()))
    evidence = probe_recheck_panel.validation_evidence(Path(validation["path"]).parent)
    require(file_ref(Path(validation["path"])) == validation
            and evidence["head"] == git_commit() and evidence["implementation"] == bindings()
            and evidence["provider_calls"] == evidence["input_count_calls"] == 0,
            "final-commit offline validation required")
    prepared = json.loads(read_ref(preparation))
    require(prepared["passed"] is True and prepared["runtime_hash"] == runtime_content_hash()
            and prepared["implementation"] == bindings()
            and prepared["provider_calls"] == prepared["input_count_calls"] == 0,
            "provider-free preparation identity changed")
    for ref in prepared["files"]:
        read_ref(ref)
    rate = json.loads(read_ref(pricing))
    require(rate["prices"] == plan["pricing"] and rate["source"] == plan["pricing_source"],
            "official price review differs")
    runner._require_tracked_clean_paths(repository_root(), list(bindings()))
    preflight = checkpoint_comparison.check_environment(Path(packet["path"]), packet["hash"],
                                                       env_file)
    require(preflight["status"] == "READY", "environment is not ready")
    source_packet = json.loads(read_ref(packet))
    spec = json.loads(read_ref(source_packet["specification"]))
    dependencies = Path(spec["source"]["root"])
    envelope = DevJournal(dependencies, spec["source"]["run_id"]).load_envelope()
    manifest = {"schema": "caller-evidence-execution-v1", "paid_authorized": False,
        "official": False, "claim_eligible": False, "head": git_commit(),
        "runtime_hash": runtime_content_hash(), "implementation": bindings(),
        "controls": plan, "rows": rows_for(plan), "validation": validation,
        "preparation": preparation, "pricing_review": pricing, "preflight": preflight,
        "invariants": caller_uptake.invariants(),
        "programs": {r["mode"]: r["program"] for r in spec["public_provenance"]},
        "environments": {a: {"dependencies": file_ref(Path(
            envelope.prepared_probe_dependencies_path))} for a in "AB"},
        "native_input": caller_uptake.native_input(),
        "native_identity": portfolio_dev20.native_identity(),
        "native_patch_scope": "full-submission", "caller_patch_scope": "source-only",
        "rubric": file_ref(repository_root() / NOTE), "grades_before_audit": False,
        "limitations": prepared["limitations"], "fresh_price_review_required_at_dispatch": True}
    root.mkdir()
    save(root, "continuation-manifest.json", plan)
    save(root, "manifest.json", manifest)
    digest = sha256_json(manifest)
    DevJournal(root, JOURNAL).append("execution_frozen", {"manifest_hash": digest,
        "manifest": file_ref(root / "manifest.json"), "paid_authorized": False})
    return {"manifest": str(root / "manifest.json"), "manifest_hash": digest,
            "new_cap_usd": str(Decimal(plan["new_cap_nanos"]) / 10**9), "paid_authorized": False}


def validate(root, digest):
    value = json.loads((root / "manifest.json").read_bytes())
    require(sha256_json(value) == digest and value["paid_authorized"] is False,
            "execution manifest changed")
    require(value["head"] == git_commit() and value["runtime_hash"] == runtime_content_hash()
            and value["implementation"] == bindings()
            and value["invariants"] == caller_uptake.invariants(), "implementation changed")
    runner._require_tracked_clean_paths(repository_root(), list(bindings()))
    plan = value["controls"]
    # controls() requires a fresh destination; after dispatch its identity is
    # checked through the frozen plan/row records, not by claiming a second run.
    require(json.loads((root / "continuation-manifest.json").read_bytes()) == plan,
            "continuation controls changed")
    saved_caller_checkpoint.validate(Path(plan["packet"]), plan["packet_hash"])
    require(value["rows"] == rows_for(plan), "row settings changed")
    for key in ("validation", "preparation", "pricing_review", "rubric"):
        read_ref(value[key])
    for ref in json.loads(read_ref(value["preparation"]))["files"]:
        read_ref(ref)
    for ref in value["programs"].values():
        read_ref(ref)
    require(value["native_identity"] == portfolio_dev20.native_identity()
            and value["native_input"] == caller_uptake.native_input(), "native identity changed")
    return value


def due_receipts(branch, row):
    """Check completion/cleanup before the next row, without exporting private grades."""
    result = row["result"]
    if result.get("artifact_hashes", {}).get("submitted_patch"):
        with continuation.inherited_reads(branch):
            completion = load_evaluation_completion(branch.journal, branch.store, branch.envelope)
        require(completion is not None and not completion.stop_remaining
                and completion.artifact_hashes == result["artifact_hashes"],
                "submitted patch has no settled registered receipt")
    for e in branch.journal.events()[branch.inherited_events:]:
        if e["event_type"] == "action_finished":
            require(not e["payload"]["result"].get("output", {}).get("cleanup_failed"),
                    "probe cleanup uncertain")


def collect(root, digest, authorization, pricing_review):
    packet = validate(root, digest)
    plan = packet["controls"]
    require(authorization == {"approved": True, "manifest_hash": digest,
        "task": plan["task"], "model": plan["model"], "credential_file": plan["env_file"],
        "repeat_per_arm": 6, "new_cap_nanos": plan["new_cap_nanos"],
        "human_message": authorization.get("human_message")} and authorization["human_message"],
        "exact human authorization required")
    require(pricing_review == {"verified_on": datetime.now(UTC).date().isoformat(),
        "source": plan["pricing_source"], "prices": plan["pricing"]},
        "fresh official price review required")
    journal = DevJournal(root, JOURNAL)
    with journal.execution_lock():
        require(not any(e["event_type"] == "collection_started" for e in journal.events()),
                "no resume or replacement collection")
        journal.append("collection_started", {"authorization": authorization,
                                               "pricing_review": pricing_review})
        result = checkpoint_comparison.collect(root / "continuation-manifest.json",
            sha256_bytes((root / "continuation-manifest.json").read_bytes()),
            Decimal(plan["new_cap_nanos"]) / 10**9, after_row=due_receipts)
        sealed = ArtifactStore(root / "sealed")
        rows = []
        for row in result["rows"]:
            if "result" not in row:
                continue
            value = {"ok": row["billing_known"] and not row["stop_remaining"],
                     "result": {"runs": [row["result"]]}, "continuation": row}
            rows.append({"row_id": row["row"], "sealed": sealed.put_json(value).model_dump(
                mode="json")})
        save(root, "collection.json", {"rows": rows, "intended": plan["order"],
            "stopped": result["stop_reason"], "new_cost_nanos": result["new_cost_nanos"]})
        journal.append("collection_closed", {"collection": file_ref(root / "collection.json"),
            "billing_known": result["billing_known"], "grades": "SEALED"})
    return {"started": len(rows), "grades": "SEALED", "stop_reason": result["stop_reason"],
            "new_cost_nanos": result["new_cost_nanos"], "billing_known": result["billing_known"]}


def export_audit(root, digest):
    packet = validate(root, digest)
    journal = DevJournal(root, JOURNAL)
    require(any(e["event_type"] == "collection_closed" for e in journal.events()),
            "collection must close before audit")
    target = root / "audit-public"
    target.mkdir()
    source = Source.from_record(json.loads(
        Path(packet["controls"]["packet"]).read_bytes())["source"])
    files = {}
    for row in packet["rows"]:
        state = Path(row["request"]["state_root"])
        path = state / "runs" / (source.run_id + ".jsonl")
        exported = []
        if path.is_file():
            events = DevJournal(state, source.run_id).events()
            fork = next(e["sequence"] for e in events if e["event_type"]
                        == "diagnostic_checkpoint_fork")
            exported = [e for e in caller_uptake_execution.public_events(
                events, ForkStore(state, events)) if e["sequence"] > fork]
        dispatches = [e for e in exported if e["event_type"] == "provider_call_started"]
        expected = packet["controls"]["first_request_hashes"][row["arm"] + "_request_hash"]
        require(not dispatches or dispatches[0]["payload"]["actual_request_hash"] == expected,
                "first delivery differs from frozen request")
        save(target, row["row_id"] + ".json", {"row_id": row["row_id"], "events": exported,
            "first_delivery": "COMPLETE" if dispatches else "NOT_RUN",
            "first_request_hash": expected, "inherited_decisions_excluded": True})
        ref = file_ref(target / (row["row_id"] + ".json"))
        files[ref["path"]] = ref["hash"]
    save(target, "index.json", {"files": files, "grade_exposure": [], "arm_blind": False,
                                "historical_outcomes_blind": False})
    journal.append("public_audit_exported", {"index": file_ref(target / "index.json")})
    return files


def seal_audit(root, digest, annotations):
    packet = validate(root, digest)
    journal = DevJournal(root, JOURNAL)
    require(not any(e["event_type"] in {"audit_sealed", "assessments_started"}
                    for e in journal.events()), "audit already sealed or grades opened")
    index = next(e["payload"]["index"] for e in journal.events()
                 if e["event_type"] == "public_audit_exported")
    allowed = json.loads(read_ref(index))["files"]
    raw = json.loads(annotations.read_bytes())
    require([r["row_id"] for r in raw["rows"]] == packet["controls"]["order"]
            and "fresh_grade_exposure" in raw, "all rows and grade exposure required")
    axes = {r["row_id"]: grading.validate_annotation(r, allowed) for r in raw["rows"]}
    journal.append("audit_sealed", {"annotations": ArtifactStore(root / "artifacts").put_json(
        raw).model_dump(mode="json"), "index": index, "axes": axes,
        "uptake": {label: "YES" if a["J"] == a["action_use"] == "SUPPORTED" else "UNKNOWN"
                   for label, a in axes.items()}, "exposure": raw["fresh_grade_exposure"]})
    return axes


def assess(root, digest):
    packet = validate(root, digest)
    journal = DevJournal(root, JOURNAL)
    seal = next((e["payload"] for e in journal.events() if e["event_type"] == "audit_sealed"), None)
    require(seal is not None, "seal public annotations before opening grades")
    ArtifactStore(root / "artifacts").read_bytes(Artifact.model_validate(seal["annotations"]))
    read_ref(seal["index"])
    require(not any(e["event_type"] == "assessments_started" for e in journal.events()),
            "no assessment retry")
    journal.append("assessments_started", {"manifest_hash": digest})
    return caller_uptake_execution._assess_rows(root, root, packet, journal, seal,
        order=packet["controls"]["order"], aggregate=grading.aggregate, native_full_patch=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("freeze", "validate", "collect", "export", "seal",
                                            "assess"))
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--hash")
    parser.add_argument("--inputs", type=Path)
    args = parser.parse_args()
    if args.command == "freeze":
        inputs = json.loads(args.inputs.read_bytes())
        inputs["env_file"], inputs["live"] = Path(inputs["env_file"]), Path(inputs["live"])
        result = freeze(args.root, **inputs)
    elif args.command == "collect":
        inputs = json.loads(args.inputs.read_bytes())
        result = collect(args.root, args.hash, inputs["authorization"], inputs["pricing_review"])
    elif args.command == "seal":
        result = seal_audit(args.root, args.hash, args.inputs)
    else:
        result = {"validate": validate, "export": export_audit, "assess": assess}[
            args.command](args.root, args.hash)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
