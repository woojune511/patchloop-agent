"""Two-phase operator execution: fresh solves, sealed public audit, then assessment.

Nothing in this module runs on import. collect() requires a separately recorded
human authorization of the exact packet; preparation/tests use injected fakes.
"""
from __future__ import annotations

import copy
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic

from diagnostics import caller_uptake as panel
from diagnostics import caller_uptake_grading as grading
from diagnostics import parallel_dev_batch, portfolio_dev20
from diagnostics.positive_verification_panel import require, save
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact
from patchloop.deadline import ExecutionDeadline
from patchloop.dev.contracts import DevRunRequest
from patchloop.dev.cost import usd_to_nanos
from patchloop.dev.evaluation_completion import load_evaluation_completion
from patchloop.dev.state import DevJournal
from patchloop.git_execution import run_git
from patchloop.prepared_probe_dependencies import admit, load_dependencies
from patchloop.prepared_source import admission_hash
from patchloop.repository import WorkspaceManager
from patchloop.runtime import repository_root
from patchloop.sandbox.probes import DockerProbeSandbox
from patchloop.task_loader import load_task_package
from patchloop.util import sha256_bytes, sha256_json
from patchloop.verifier.policy import verify_scope, verify_test_tampering


class Allocation:
    def __init__(self):
        self.cursor = 0
        self.cost = {"A": 0, "B": 0}
        self.stopped = False

    def settle(self, label, value):
        require(not self.stopped and self.cursor < len(panel.ORDER)
                and label == panel.ORDER[self.cursor], "out of order or stopped allocation")
        self.cursor += 1
        account = value.get("accounting", {})
        cost = account.get("cost_nanos")
        known = (value.get("ok") is True and account.get("billing_known") is True
                 and account.get("counting_known") is True and type(cost) is int
                 and 0 <= cost <= usd_to_nanos(panel.ROW_CAP))
        if type(cost) is int:
            self.cost[label[0]] += cost
        self.stopped = not (known and all(n <= usd_to_nanos(panel.ARM_CAP)
                                         for n in self.cost.values())
                            and sum(self.cost.values()) <= usd_to_nanos(panel.CAP))
        return not self.stopped


def due_receipts(_index, value, req):
    """Validate sealed evaluator lineage/cleanup without exposing its grade to the audit."""
    require(len(value["result"]["runs"]) == 1, "one fresh run required")
    run = value["result"]["runs"][0]
    journal = DevJournal(req.state_root, run["run_id"])
    if run.get("artifact_hashes", {}).get("submitted_patch"):
        completion = load_evaluation_completion(
            journal, ArtifactStore(req.state_root / "artifacts"), journal.load_envelope())
        require(completion is not None and not completion.stop_remaining,
                "submitted patch has no settled registered receipt")
        require(completion.artifact_hashes == run["artifact_hashes"], "receipt lineage differs")
    for event in journal.events():
        if event["event_type"] == "action_finished":
            output = event["payload"].get("result", {}).get("output") or {}
            require(not output.get("cleanup_failed"), "probe cleanup uncertain")
    return {"ok": True, "due_receipts_validated": True, "native": "DEFERRED_UNTIL_AUDIT"}


def collect(root, digest, authorization, *, pricing_review):
    packet = panel.validate(root, digest)
    require(authorization == {"approved": True, "packet_hash": digest,
        "task": str(repository_root() / panel.TASK), "model": panel.MODEL,
        "credential_file": str(repository_root() / ".env"), "repeat_per_arm": 6,
        "total_cap_usd": str(panel.CAP), "human_message": authorization.get("human_message")}
        and bool(authorization["human_message"]), "exact human authorization required")
    require(pricing_review == {"verified_on": datetime.now(UTC).date().isoformat(),
        "source": "https://developers.openai.com/api/docs/pricing", "prices": packet["pricing"]},
        "fresh official rate review required")
    journal = DevJournal(root, panel.JOURNAL)
    with journal.execution_lock():
        require(not any(e["event_type"] == "collection_started" for e in journal.events()),
                "no resume or replacement collection")
        live = Path(packet["live_root"])
        require(not live.exists(), "fresh live root required")
        live.mkdir(parents=True)
        journal.append("collection_started", {"packet_hash": digest,
            "authorization": authorization, "pricing_review": pricing_review,
            "reserved_nanos": usd_to_nanos(panel.CAP), "transfer": False})
        ledger, completed = Allocation(), []
        try:
            for row in packet["rows"]:
                panel.validate(root, digest)  # Exact identity/images/cost inputs before each row.
                wave = parallel_dev_batch.run_parallel_rows([row], total_cap=panel.ROW_CAP,
                    workers=1, journal=journal, after_row=due_receipts)
                require(len(wave["rows"]) == 1, "missing dispatched row receipt")
                value = wave["rows"][0]
                sealed = ArtifactStore(root / "sealed").put_json(value).model_dump(mode="json")
                completed.append({"row_id": row["row_id"], "sealed": sealed})
                journal.append("row_sealed", completed[-1])
                if not ledger.settle(row["row_id"], value) or wave["stopped"]:
                    ledger.stopped = True
                    break
        except BaseException as exc:
            ledger.stopped = True
            journal.append("collection_stopped", {"error_type": type(exc).__name__})
        save(root, "collection.json", {"rows": completed, "stopped": ledger.stopped,
             "cost_nanos": ledger.cost, "intended": list(panel.ORDER)})
        journal.append("collection_closed", {"started": len(completed),
            "cost_nanos": ledger.cost, "grades": "SEALED", "stopped": ledger.stopped})
        return {"started": len(completed), "cost_nanos": ledger.cost, "grades": "SEALED"}


def public_events(events, store):
    """Export only actually dispatched inputs and explicit public decisions/results.

    Encrypted items are represented by hashes, never decrypted or interpreted.
    Terminal/evaluation events and unrestricted artifact traversal are excluded.
    """
    prepared = {}
    exported = []
    for event in events:
        kind, p = event["event_type"], event["payload"]
        if kind == "model_input_prepared":
            bundle = json.loads(store.read_bytes(Artifact.model_validate(p["artifact"])))
            require(sha256_json(bundle["request"]) == p["request_hash"], "prepared input changed")
            prepared[bundle["turn"]["turn_id"]] = bundle["request"]
        if kind == "provider_call_started":
            wire = copy.deepcopy(prepared[p["turn_id"]])
            wire["max_output_tokens"] = p["output_ceiling"]
            require(sha256_json(wire) == p["request_hash"], "dispatched request mismatch")
            for i, item in enumerate(wire["input"]):
                if item.get("type") == "reasoning":
                    wire["input"][i] = {"type": "reasoning_redacted",
                                          "item_hash": sha256_json(item)}
            payload = {"wire": wire, "actual_request_hash": p["request_hash"],
                       "turn_id": p["turn_id"], "active_elapsed_ms": p["active_elapsed_ms"]}
        elif kind == "turn_decision_recorded":
            payload = {k: p[k] for k in ("turn_id", "tool_calls", "error_code", "incomplete_reason")
                       if k in p}
        elif kind in {"action_finished", "working_notes_updated", "working_plan_updated"}:
            payload = copy.deepcopy(p)
        else:
            continue
        exported.append({"sequence": event["sequence"], "event_hash": event["event_hash"],
                         "event_type": kind, "payload": payload})
    return exported


def export_audit(root, digest):
    packet = panel.validate(root, digest)
    journal = DevJournal(root, panel.JOURNAL)
    require(any(e["event_type"] == "collection_closed" for e in journal.events()),
            "collection must close before audit")
    target = root / "audit-public"
    require(not target.exists(), "audit export already exists")
    target.mkdir()
    files = {}
    for row in packet["rows"]:
        state = Path(row["request"]["state_root"])
        events = []
        for path in sorted((state / "runs").glob("*.jsonl")):
            events.extend(public_events(DevJournal(state, path.stem).events(),
                                       ArtifactStore(state / "artifacts")))
        save(target, row["row_id"] + ".json", {"row_id": row["row_id"], "events": events})
        ref = panel.file_ref(target / (row["row_id"] + ".json"))
        files[ref["path"]] = ref["hash"]
    save(target, "index.json", {"files": files, "grade_exposure": [],
        "arm_blind": False, "historical_outcomes_blind": False})
    journal.append("public_audit_exported", {"index": panel.file_ref(target / "index.json")})
    return files


def seal_audit(root, annotations):
    journal = DevJournal(root, panel.JOURNAL)
    require(not any(e["event_type"] in {"audit_sealed", "assessments_started"}
                    for e in journal.events()), "audit already sealed or grades opened")
    index = next(e["payload"]["index"] for e in journal.events()
                 if e["event_type"] == "public_audit_exported")
    allowed = json.loads(panel.read_ref(index))["files"]
    raw = json.loads(annotations.read_bytes())
    require([r["row_id"] for r in raw["rows"]] == list(panel.ORDER), "all assigned rows required")
    require("fresh_grade_exposure" in raw, "record accidental grade exposure explicitly")
    uptake = {r["row_id"]: grading.validate_annotation(r, allowed) for r in raw["rows"]}
    artifact = ArtifactStore(root / "artifacts").put_json(raw).model_dump(mode="json")
    journal.append("audit_sealed", {"annotations": artifact, "index": index,
                                    "uptake": uptake, "exposure": raw["fresh_grade_exposure"]})
    return uptake


def assessment_deadline(started, *, clock=monotonic):
    remaining = 600 - (clock() - started)
    require(remaining > 0, "shared 600-second assessment allowance exhausted")
    return ExecutionDeadline.from_remaining(remaining)


def native_assessment(root, req, patch, entry, deadline):
    """Existing pinned native harness, within the remainder shared with public probes."""
    root.mkdir(parents=True)
    save(root, "prediction.jsonl", {"instance_id": entry["instance_id"],
        "model_name_or_path": req.model, "model_patch": patch.decode()})
    with (root / "native.log").open("xb") as log:
        process = subprocess.run([str(portfolio_dev20.NATIVE_PYTHON), "-X", "utf8", "-m",
            "diagnostics.swebench_lite_native", "--rows", entry["native_row"],
            "--output", str(root / "output"), "--predictions", str(root / "prediction.jsonl")],
            cwd=repository_root(), env=portfolio_dev20.native_env(), stdout=log,
            stderr=subprocess.STDOUT, timeout=deadline.remaining_seconds(), check=False)
    cleanup = json.loads((root / "output/cleanup.json").read_bytes())
    controls = [json.loads(p.read_bytes()) for p in (root / "output").glob("control-*.json")]
    require(process.returncode == 0 and not cleanup["remaining"] and len(controls) == 1
            and controls[0]["instance_id"] == entry["instance_id"] and controls[0]["complete"]
            and controls[0]["missing_count"] == 0 and type(controls[0]["resolved"]) is bool,
            "native result or cleanup uncertain")
    status = "PASS" if controls[0]["resolved"] else "FAIL"
    save(root, "receipt.json", {"status": status, "source_only_diff": sha256_bytes(patch),
        "cleanup_confirmed": True, "files": [panel.file_ref(p)
            for p in sorted(root.rglob("*")) if p.is_file()]})
    return status


def assess(root, digest):
    """Every submitted row in either arm; no feedback into a solver or audit."""
    packet = panel.validate(root, digest)
    journal = DevJournal(root, panel.JOURNAL)
    events = journal.events()
    seal = next((e["payload"] for e in events if e["event_type"] == "audit_sealed"), None)
    require(seal is not None, "seal all public annotations before opening grades")
    ArtifactStore(root / "artifacts").read_bytes(Artifact.model_validate(seal["annotations"]))
    panel.read_ref(seal["index"])
    require(not any(e["event_type"] == "assessments_started" for e in events),
            "no assessment retry")
    journal.append("assessments_started", {"packet_hash": digest})
    rows = []
    panel.read_ref(packet["native_input"]["rows"])
    entry = {"instance_id": packet["native_input"]["instance_id"],
             "native_row": packet["native_input"]["rows"]["path"]}
    by_id = {r["row_id"]: r for r in packet["rows"]}
    try:
        for bound in json.loads((root / "collection.json").read_bytes())["rows"]:
            label = bound["row_id"]
            value = json.loads(ArtifactStore(root / "sealed").read_bytes(
                Artifact.model_validate(bound["sealed"])))
            runs = (value.get("result") or {}).get("runs", [])
            run = runs[0] if len(runs) == 1 else {}
            req = DevRunRequest.model_validate(by_id[label]["request"])
            patch_hash = run.get("artifact_hashes", {}).get("submitted_patch")
            row = {"row_id": label, "completed": value["ok"], "settled": value["ok"],
                "submitted": bool(patch_hash), "submitted_diff": patch_hash,
                "U": seal["uptake"][label], "cleanup": value["ok"],
                "infrastructure": "SETTLED" if value["ok"] else "ERROR",
                "registered": (run.get("evaluator") or {}).get("task_acceptance", "NOT_RUN"),
                "safety": (run.get("evaluator") or {}).get("safety_state", "NOT_RUN"),
                "native": "NOT_RUN", "missing": "NOT_RUN", "present": "NOT_RUN"}
            rows.append(row)
            if not patch_hash:
                continue
            started = monotonic()
            workspace = req.state_root / "workspaces" / run["run_id"] / "repo"
            diff = WorkspaceManager.diff_summary(workspace)
            public = load_task_package(req.task.parent).public
            require(diff.patch_hash == patch_hash and verify_scope(diff, public.constraints).passed,
                    "submitted diff or scope changed")
            policy = verify_test_tampering(diff, public.constraints, workspace)
            require(policy.passed, "unsafe submitted tests")
            source_patch = run_git(workspace, "diff", "--binary", "HEAD", "--", ".",
                *[f":(exclude){p}" for p in policy.details["test_files"]]).stdout.encode()
            folder = root / "assessments" / label
            folder.mkdir(parents=True)
            ArtifactStore(root / "artifacts").write_bytes_atomic(
                folder / "source-only.patch", source_patch)
            row.update(assessed_from_diff=patch_hash, source_only_diff=sha256_bytes(source_patch),
                       omitted_additive_tests=policy.details["test_files"])
            manager = WorkspaceManager(repository_root() / "fixtures/repositories",
                folder / "workspaces", prepared_source=req.prepared_source,
                prepared_source_hash=admission_hash(req.prepared_source))
            staged = manager.create("run_dev_callerassessment", public.repository.url,
                public.repository.base_commit, deadline=assessment_deadline(started))
            manager.apply_patch(staged, folder / "source-only.patch",
                                deadline=assessment_deadline(started))
            require(manager.diff_summary(staged).patch_hash == row["source_only_diff"],
                    "assessment source projection changed")
            dep_path = Path(packet["environments"]["B"]["dependencies"]["path"])
            sandbox = DockerProbeSandbox(dependencies=load_dependencies(
                dep_path, public, admit(dep_path)))
            sandbox.preflight(deadline=assessment_deadline(started))
            for case in ("missing", "present"):
                program = panel.read_ref(packet["programs"][case])
                identity = {"run_id": panel.JOURNAL, "action_id": label + "-" + case,
                    "input_hash": sha256_json({"program": sha256_bytes(program),
                        "diff": row["source_only_diff"],
                        "dependencies": admit(dep_path).manifest_hash})}
                journal.append("caller_assessment_started", {"identity": identity})
                receipt = sandbox.run_probe(staged, "Assess frozen public failure/control input",
                    program.decode(), deadline=assessment_deadline(started),
                    execution_identity=identity)
                save(folder, case + "-receipt.json", receipt)
                clean = not receipt.get("cleanup_failed") and receipt["execution_policy"].get(
                    "cleanup_status") == "confirmed"
                grade = grading.caller_grade(receipt, case=case,
                    dependency_hash=admit(dep_path).manifest_hash,
                    diff_hash=manager.diff_summary(staged).patch_hash,
                    expected_diff=row["source_only_diff"], cleanup=clean)
                row[case] = grade["status"]
                journal.append("caller_assessment_finished", {"row_id": label, "grade": grade,
                    "receipt": panel.file_ref(folder / (case + "-receipt.json"))})
                require(row[case] != "ERROR", "caller assessment uncertain; stop remaining")
            row["caller_diff"] = row["source_only_diff"]
            row["native"] = native_assessment(folder / "native", req, source_patch, entry,
                                               assessment_deadline(started))
            row["native_diff"] = row["source_only_diff"]
            row["native_receipt"] = panel.file_ref(folder / "native/receipt.json")
            row["assessment_seconds"] = monotonic() - started
            save(folder, "row.json", row)
            journal.append("row_assessed", {"row_id": label, "result": panel.file_ref(
                folder / "row.json")})
            require(row["native"] == row["registered"], "acceptance disagreement; stop remaining")
    except BaseException as exc:
        journal.append("assessment_stopped", {"error_type": type(exc).__name__, "rows": rows})
        raise
    result = grading.aggregate(rows, panel.ORDER)
    if seal["exposure"]:
        result.update(favorable_local_signal=False, audit_grade_exposure=seal["exposure"])
    save(root, "result.json", result)
    journal.append("study_closed", {"result": panel.file_ref(root / "result.json")})
    return result
