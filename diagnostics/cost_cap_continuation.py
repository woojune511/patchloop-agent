"""Prepare and collect a separately funded continuation of settled cost-cap stops."""
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from diagnostics import observation_comparison as live
from diagnostics import observation_exposure as exposure
from diagnostics.checkpoint_continuation import ScriptedClient
from diagnostics.decision_sampler import require
from diagnostics.declaration_checkpoint import Source, disjoint
from patchloop.artifacts import ArtifactStore
from patchloop.dev import runner
from patchloop.dev.cost import DevCostLedger, pricing_for_model, usd_to_nanos
from patchloop.dev.state import DevJournal
from patchloop.runtime import git_commit, repository_root
from patchloop.util import canonical_json, sha256_bytes, sha256_json


def controls(sources, env_file, result_root, new_row_cap_usd):
    cap = usd_to_nanos(new_row_cap_usd)
    require(cap > 0 and sources, "positive allocation and source rows required")
    rows = []
    for index, source in enumerate(sources, 1):
        journal = DevJournal(source.root, source.run_id)
        for path, digest in ((journal.path, source.journal_hash),
                             (journal.envelope_path, source.envelope_hash),
                             (source.public_path, source.public_hash)):
            require(sha256_bytes(path.read_bytes()) == digest, "parent identity changed")
        old, events = journal.load_envelope(), journal.events()
        require(old.runtime_hash == runner._runtime_hash(), "parent runtime changed")
        require(journal.terminal()["payload"]["terminal"] == "COST_CAP_REACHED",
                "only settled cost-cap stops are supported")
        require(runner._provider_usage_failure(journal) is None
                and journal.unresolved_input_count() is None, "parent usage/count uncertain")
        require(old.provider == "openai" and old.split == "dev-train",
                "OpenAI dev-train parent required")
        require(sha256_bytes(str(env_file.resolve()).encode()) == old.credential_file_path_hash,
                "credential path changed")
        cut = [e for e in events if e["event_type"] == "model_input_prepared"][-1]
        require(not any(e["event_type"] in {"provider_call_started", "action_started"}
                        for e in events if e["sequence"] > cut["sequence"]),
                "last prepared request already executed")
        disjoint(result_root.resolve(), (repository_root(), source.root, source.public_path.parent))
        rows.append({"label": str(index), "source": source.record(),
                     "cut_sequence": cut["sequence"], "new_cap_nanos": cap,
                     "active_elapsed_ms": journal.latest_active_elapsed_ms(),
                     "executing_probe_identity": {"image_digest": old.probe_image_digest,
                                                   "profile_hash": old.probe_profile_hash},
                     "model": old.model, "repeat": 1})
    require(len({(r["source"]["root"], r["source"]["run_id"]) for r in rows}) == len(rows),
            "duplicate parent")
    require(len({r["model"] for r in rows}) == 1, "one model per invocation required")
    return {"schema": "cost-cap-continuation-v1", "official": False,
            "paid_execution_authorized": False, "rows": rows, "model": rows[0]["model"],
            "new_cap_nanos": cap * len(rows), "env_file": str(env_file.resolve()),
            "result_root": str(result_root.resolve()), "runtime_hash": runner._runtime_hash(),
            "implementation_hash": exposure.implementation_hash(), "git_commit": git_commit(),
            "historical_allocations_reopened": False, "sdk_retries": 0}


def restore(row, output, env_file=None):
    branch = exposure._fork(
        Source.from_record(row["source"]), row["cut_sequence"], output, "B",
        new_cap_usd=Decimal(row["new_cap_nanos"]) / 10**9,
        mode="funded-observation" if env_file else "offline-scripted-only",
        env_file=env_file or output / "NO_CREDENTIAL_FILE",
        preserve_parent_configuration=True,
    )
    # Include time spent on the failed admission; the fork must not refund it.
    branch.journal.append("cost_cap_continuation", {
        "parent": row["source"], "active_elapsed_ms": row["active_elapsed_ms"],
        "intervention": "new_cost_allowance_only", "original_terminal_preserved": True,
    })
    return branch


def prepare(sources, env_file, result_root, new_row_cap_usd, output):
    plan = controls(sources, env_file, result_root, new_row_cap_usd)
    disjoint(output.resolve(), (repository_root(), result_root,
                                *(s.root for s in sources),
                                *(s.public_path.parent for s in sources)))
    live.clean_implementation()
    output.mkdir()
    journal = DevJournal(output, "run_dev_costcontinuationpreparation")
    fingerprints, preflight = {}, {}
    for row in plan["rows"]:
        branch = restore(row, output / row["label"])
        client = ScriptedClient([[{"name": "stop_task", "action_id": "preparation_stop",
            "arguments": {"reason_code": "insufficient_public_evidence",
                "summary": "Offline restoration checked.", "turn_decision": {
                    "mode": "stop", "basis": "Synthetic preparation only.",
                    "evidence_goal": None, "memory_update": None, "plan_update": None}}}]])
        receipt = exposure.rehearse(branch, client)
        require(receipt["result"]["terminal"] == "AGENT_STOPPED"
                and len(client.counted) == len(client.created) == 1, "offline restoration failed")
        first = live.normalized(client.created[0])
        fingerprints[row["label"]] = sha256_json(first)
        (output / f'{row["label"]}-first.json').write_text(canonical_json(first), encoding="utf-8")
        preflight[row["label"]] = live.check_environment(row, env_file)
        journal.append("restoration_checked", {"row": row["label"], "receipt": receipt,
                       "preflight": preflight[row["label"]], "actual_provider_calls": 0})
    plan["first_request_hashes"] = fingerprints
    raw = (canonical_json(plan) + "\n").encode()
    (output / "manifest.json").write_bytes(raw)
    result = {"manifest": str(output / "manifest.json"), "manifest_hash": sha256_bytes(raw),
              "preflight": preflight, "actual_provider_calls": 0, "new_cost_nanos": 0,
              "new_cap_nanos": plan["new_cap_nanos"], "paid_execution_authorized": False}
    journal.append("preparation_finished", result)
    (output / "preparation.json").write_text(canonical_json(result), encoding="utf-8")
    return result


def collect(manifest_path, approved_hash, approved_cap_usd):
    raw = manifest_path.read_bytes()
    require(sha256_bytes(raw) == approved_hash, "approved manifest differs")
    plan = json.loads(raw)
    require(usd_to_nanos(approved_cap_usd) == plan["new_cap_nanos"], "approved cap differs")
    env_file, root = Path(plan["env_file"]), Path(plan["result_root"])
    sources = [Source.from_record(row["source"]) for row in plan["rows"]]
    expected = controls(sources, env_file, root,
                        Decimal(plan["rows"][0]["new_cap_nanos"]) / 10**9)
    require({k: v for k, v in plan.items() if k != "first_request_hashes"} == expected,
            "prepared controls changed")
    live.clean_implementation()
    root.mkdir()
    journal, store = DevJournal(root, "run_dev_costcontinuation"), ArtifactStore(root / "artifacts")
    group = DevCostLedger(approved_cap_usd, pricing_for_model(plan["model"]))
    rows = [{"row": r["label"], "status": "NOT_RUN"} for r in plan["rows"]]
    stop_reason, known = None, True
    with journal.execution_lock():
        journal.append("continuation_authorized", {"manifest_hash": approved_hash, "plan": plan})
        for i, row in enumerate(plan["rows"]):
            if stop_reason:
                break
            branch = None
            try:
                preflight = live.check_environment(row, env_file)
                journal.append("environment_checked", {"row": row["label"], **preflight})
                require(preflight["status"] == "READY", "environment preflight failed")
                branch = restore(row, root / row["label"], env_file)
                result = live.run_branch(branch, group, journal, store, row["label"],
                                         plan["first_request_hashes"][row["label"]])
            except Exception as exc:
                known = branch is None or runner._provider_usage_failure(branch.journal) is None
                result = {"row": row["label"], "status": "COLLECTOR_FAILED",
                          "error_type": type(exc).__name__, "billing_known": known,
                          "stop_remaining": True}
            rows[i] = result
            known = known and result["billing_known"]
            journal.append("row_finished", result)
            if result["stop_remaining"]:
                stop_reason = result.get("result", {}).get("terminal", result["status"])
        receipt = {"official": False, "rows": rows, "stop_reason": stop_reason,
                   "billing_known": known, "new_cost_nanos": group.spent_nanos if known else None,
                   "new_cap_nanos": group.cap_nanos, "historical_allocations_reopened": False,
                   "fresh_solve": False, "efficacy_claim": "NOT_ESTABLISHED"}
        journal.append("continuation_finished", receipt)
        (root / "result.json").write_text(canonical_json(receipt), encoding="utf-8")
    return receipt
