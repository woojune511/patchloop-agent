"""Serial collection, sealed public judgment, then independent local assessment."""
from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from diagnostics import caller_uptake as prior
from diagnostics import caller_uptake_execution as existing
from diagnostics import parallel_dev_batch
from diagnostics import verification_state_grading as grading
from diagnostics import verification_state_off as off
from diagnostics import verification_state_panel as panel
from diagnostics.positive_verification_panel import require, save
from patchloop.artifacts import ArtifactStore
from patchloop.dev.state import DevJournal
from patchloop.runtime import repository_root
from patchloop.util import canonical_json

COLLECTION = "run_dev_verificationstatecollection42"
AUDIT = "run_dev_verificationstateaudit42"
ASSESSMENT = "run_dev_verificationstateassessment42"


def authorize(digest, authorization):
    require(authorization == {
        "approved": True, "manifest_hash": digest,
        "task": str(repository_root() / panel.TASK), "model": panel.MODEL,
        "credential_file": str(repository_root() / ".env"), "repeat_per_arm": 6,
        "total_cap_usd": "10.56", "human_message": authorization.get("human_message"),
    } and bool(authorization["human_message"]), "new exact human authorization required")


def collect(root, digest, authorization, rates):
    authorize(digest, authorization)
    packet = panel.validate(root, digest)
    require(rates == {
        "verified_on": datetime.now(UTC).date().isoformat(),
        "source": "https://developers.openai.com/api/docs/pricing", "prices": packet["pricing"],
    }, "fresh official price review required")
    journal = DevJournal(root, COLLECTION)
    live = Path(packet["live_root"])
    with journal.execution_lock():
        require(not journal.events() and not live.exists(), "no resume/replacement collection")
        live.mkdir(parents=True)
        journal.append("collection_started", {
            "manifest_hash": digest, "authorization": authorization, "pricing_review": rates,
            "reserved_nanos": 10_560_000_000, "transfer": False,
        })
        ledger, completed, attempted = existing.Allocation(), [], []
        reason, billing_known = None, True
        try:
            for row in packet["rows"]:
                panel.validate(root, digest)
                label = row["row_id"]
                attempted.append(label)
                journal.append("row_admission_started", {"row_id": label, "arm": row["arm"]})
                initializer = (off.initialize_off_worker if row["arm"] == "A"
                               else parallel_dev_batch.initialize_worker)
                wave = parallel_dev_batch.run_parallel_rows(
                    [row], total_cap=panel.ROW_CAP, workers=1, journal=journal,
                    after_row=existing.due_receipts, initializer=initializer)
                require(len(wave["rows"]) == 1, "missing row receipt")
                value = wave["rows"][0]
                sealed = ArtifactStore(root / "sealed").put_json(value).model_dump(mode="json")
                completed.append({"row_id": label, "sealed": sealed})
                journal.append("row_sealed", completed[-1])
                billing_known &= value.get("accounting", {}).get("billing_known") is True
                if not ledger.settle(label, value) or wave["stopped"]:
                    ledger.stopped, reason = True, "worker/accounting/cleanup stop"
                    break
        except BaseException as exc:
            ledger.stopped, billing_known, reason = True, False, type(exc).__name__
            journal.append("collection_stopped", {"error_type": reason})
        result = {
            "rows": completed, "stopped": ledger.stopped, "stop_reason": reason,
            "settled_cost_nanos": ledger.cost, "billing_known": billing_known,
            "intended": list(panel.ORDER), "attempted": attempted,
            "unsealed_unknown_rows": [r for r in attempted
                                     if r not in {c["row_id"] for c in completed}],
            "not_run": [r for r in panel.ORDER if r not in attempted],
            "allocation_closed": True, "grades": "SEALED", "repair_success": "NOT_ASSESSED",
        }
        save(root, "collection.json", result)
        journal.append("collection_closed", {
            "collection": prior.file_ref(root / "collection.json")})
        return result


def export(root, digest):
    packet = panel.validate(root, digest)
    require(any(e["event_type"] == "collection_closed"
                for e in DevJournal(root, COLLECTION).events()), "collection must close")
    journal = DevJournal(root, AUDIT)
    with journal.execution_lock():
        require(not journal.events(), "no replacement audit")
        target = root / "audit-public"
        target.mkdir()
        files = {}
        for row in packet["rows"]:
            state = Path(row["request"]["state_root"])
            paths = list((state / "runs").glob("*.jsonl"))
            require(len(paths) <= 1, "one fresh run per assignment")
            events = existing.public_events(
                DevJournal(state, paths[0].stem).events(), ArtifactStore(state / "artifacts"),
            ) if paths else []
            public = {"public_id": row["public_id"], "events": events}
            grading.public_index(public)
            save(target, row["public_id"] + ".json", public)
            files[row["public_id"]] = prior.file_ref(target / (row["public_id"] + ".json"))
        save(target, "index.json", {"files": files, "fresh_grade_exposure": [],
                                   "arm_codes_masked": True, "fully_blind": False})
        journal.append("public_audit_exported", {"index": prior.file_ref(target / "index.json")})
        return {"public_rows": len(files), "grades": "SEALED"}


def seal(root, digest, annotations):
    packet = panel.validate(root, digest)
    journal = DevJournal(root, AUDIT)
    with journal.execution_lock():
        require(not any(e["event_type"] == "audit_sealed" for e in journal.events())
                and not DevJournal(root, ASSESSMENT).events(), "audit sealed or grades opened")
        index_ref = next(e["payload"]["index"] for e in journal.events()
                         if e["event_type"] == "public_audit_exported")
        index = json.loads(prior.read_ref(index_ref))
        value = json.loads(annotations.read_bytes())
        require(value["fresh_grade_exposure"] == index["fresh_grade_exposure"] == [],
                "fresh grades exposed")
        require([r["public_id"] for r in value["rows"]]
                == [r["public_id"] for r in packet["rows"]], "all assigned rows required")
        axes, judgments = {}, {}
        for row, assigned in zip(value["rows"], packet["rows"], strict=True):
            public = json.loads(prior.read_ref(index["files"][row["public_id"]]))
            summary = grading.validate_annotation(row, public)
            axes[assigned["row_id"]] = {**row, "judgment": summary}
            judgments[assigned["row_id"]] = summary
        artifact = ArtifactStore(root / "artifacts").put_json(
            {"rows": axes, "judgments": judgments}).model_dump(mode="json")
        journal.append("audit_sealed", {"index": index_ref, "annotations": artifact,
                                        "input": prior.file_ref(annotations)})
        return {"rows": len(axes), "grades": "SEALED"}


def assess(root, digest):
    packet = panel.validate(root, digest)
    seal_event, = [e for e in DevJournal(root, AUDIT).events() if e["event_type"] == "audit_sealed"]
    sealed = seal_event["payload"]
    index = json.loads(prior.read_ref(sealed["index"]))
    for ref in index["files"].values():
        prior.read_ref(ref)
    from patchloop.contracts import Artifact

    value = json.loads(ArtifactStore(root / "artifacts").read_bytes(
        Artifact.model_validate(sealed["annotations"])))
    journal = DevJournal(root, ASSESSMENT)
    with journal.execution_lock():
        require(not journal.events(), "no assessment retry")
        journal.append("assessments_started", {
            "manifest_hash": digest, "audit_seal": seal_event["event_hash"],
            "maximum_caller_checks": 24, "maximum_native_evaluations": 12,
        })
        seal_value = {"axes": value["rows"], "uptake": {
            row: v["supported_application"] for row, v in value["judgments"].items()},
            "exposure": []}
        return existing._assess_rows(
            root, root, packet, journal, seal_value, order=panel.ORDER,
            aggregate=grading.aggregate, native_full_patch=True,
            metadata={"audit_seal": seal_event["event_hash"], "new_paid_calls": 0})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("collect", "export", "seal", "assess"))
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--hash", required=True)
    parser.add_argument("--authorization", type=Path)
    parser.add_argument("--pricing-review", type=Path)
    parser.add_argument("--annotations", type=Path)
    args = parser.parse_args()
    if args.mode == "collect":
        require(args.authorization is not None and args.pricing_review is not None,
                "authorization and rates required")
        result = collect(args.root, args.hash, json.loads(args.authorization.read_bytes()),
                         json.loads(args.pricing_review.read_bytes()))
    elif args.mode == "seal":
        result = seal(args.root, args.hash, args.annotations)
    else:
        result = (export if args.mode == "export" else assess)(args.root, args.hash)
    print(canonical_json(result))


if __name__ == "__main__":
    main()
