"""Prepare an unhinted action-replay pair; dispatch only an approved frozen pair."""
from __future__ import annotations

import argparse
import copy
import json
from contextlib import contextmanager, nullcontext
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from diagnostics import observation_comparison as live
from diagnostics import observation_exposure as exposure
from diagnostics.checkpoint_continuation import ScriptedClient, inherited_reads
from diagnostics.decision_sampler import require
from diagnostics.declaration_checkpoint import Source, disjoint
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact
from patchloop.dev import probe_replay, runner
from patchloop.dev.cost import DevCostLedger, pricing_for_model, usd_to_nanos
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import DevToolGateway
from patchloop.runtime import git_commit, repository_root
from patchloop.util import canonical_json, sha256_bytes, sha256_json

RUBRIC = ".agent/probe-action-comparison.md"


def project_tools(schemas, arm):
    require(arm in {"A", "B"}, "unknown action replay arm")
    result = copy.deepcopy(schemas)
    if arm == "A":
        for tool in result:
            if tool["name"] != "run_probe":
                continue
            tool["description"] = tool["description"].replace(" " + probe_replay.DESCRIPTION, "")
            params = tool["parameters"]
            del params["properties"]["replay_action_id"]
            params["required"].remove("replay_action_id")
            for field in ("question", "python_source"):
                params["properties"][field]["type"] = "string"
    return result


@contextmanager
def surface(arm):
    original = runner.dev_tool_schemas
    execute = DevToolGateway.execute

    def admitted(gateway, call):
        require(not (arm == "A" and call.name == "run_probe"
                     and call.arguments.get("replay_action_id") is not None),
                "action replay is not offered by the control")
        return execute(gateway, call)

    with (patch.object(runner, "dev_tool_schemas",
                       lambda **kwargs: project_tools(original(**kwargs), arm)),
          patch.object(DevToolGateway, "execute", admitted)):
        yield


def parent_reads(source):
    """Use a parent's exact copied-reference map when the source is itself a fork."""
    path = source.root / "fork.json"
    if not path.exists():
        return nullcontext()
    saved = json.loads(path.read_bytes())
    require(any(e["event_type"] == "observation_exposure_fork"
                and e["payload"] == saved["marker"]
                for e in DevJournal(source.root, source.run_id).events()),
            "parent fork marker differs from journal")
    return inherited_reads(SimpleNamespace(
        references=saved["references"], store=ArtifactStore(source.root / "artifacts")))


def audit(source, sequence, target):
    journal = DevJournal(source.root, source.run_id)
    for path, digest in ((journal.path, source.journal_hash),
                         (journal.envelope_path, source.envelope_hash),
                         (source.public_path, source.public_hash)):
        require(sha256_bytes(path.read_bytes()) == digest, "source identity changed")
    events, envelope = journal.events(), journal.load_envelope()
    boundary = next(e for e in events if e["sequence"] == sequence)
    require(boundary["event_type"] == "model_input_prepared", "prepared boundary required")
    prefix = [e for e in events if e["sequence"] < sequence]
    require(not any(e["event_type"] in {"submission_recorded", "evaluator_finished", "terminal"}
                    for e in prefix), "post-submission prefix forbidden")
    program = probe_replay.prepare({"replay_action_id": target}, prefix)
    with parent_reads(source):
        raw = ArtifactStore(source.root / "artifacts").read_bytes(
            Artifact.model_validate(boundary["payload"]["artifact"]))
    request = json.loads(raw)["request"]
    require(sha256_json(request) == boundary["payload"]["request_hash"], "input binding changed")
    state = json.loads(request["input"][-1]["content"])["state"]
    require(target in canonical_json(state), "target ID absent from current public state")
    require("run_probe" in {t["name"] for t in request["tools"]}, "probe is not offered")
    require(envelope.probe_policy == "none", "ordinary-probe comparison required")
    return {"request_hash": boundary["payload"]["request_hash"],
            "prefix_hash": prefix[-1]["event_hash"],
            "remaining_budget": state["remaining_budget"],
            "candidate_diff_hash": state["current_diff"]["patch_hash"],
            "target": program["replayed_from"],
            "target_question": program["question"],
            "target_id_visible": True, "replay_resolves_exact_program": True}


def controls(source, sequence, target, env_file, result_root, row_cap_usd):
    cap = usd_to_nanos(row_cap_usd)
    require(cap > 0, "positive new allowance required")
    checked = audit(source, sequence, target)
    old = DevJournal(source.root, source.run_id).load_envelope()
    require(old.provider == "openai" and old.split == "dev-train", "OpenAI dev-train required")
    require(sha256_bytes(str(env_file.resolve()).encode()) == old.credential_file_path_hash,
            "credential path changed")
    disjoint(result_root.resolve(), (repository_root(), source.root, source.public_path.parent))
    fork_path = source.root / "fork.json"
    return {"schema": "probe-action-comparison-v1", "official": False,
            "paid_execution_authorized": False, "source": source.record(),
            "parent_fork_hash": (sha256_bytes(fork_path.read_bytes())
                                 if fork_path.exists() else None),
            "cut_sequence": sequence, "target_action_id": target, "audit": checked,
            "rows": [{"label": arm, "arm": arm, "repeat": 1, "new_cap_nanos": cap}
                     for arm in ("A", "B")],
            "model": old.model, "reasoning_effort": old.reasoning_effort,
            "max_output_tokens": old.max_output_tokens,
            "retained_source_chars": old.retained_source_chars,
            "env_file": str(env_file.resolve()), "result_root": str(result_root.resolve()),
            "executing_probe_identity": {
                "image_digest": runner.probe_profile(old.probe_dependencies)["image_digest"],
                "profile_hash": runner.probe_profile_hash(old.probe_dependencies)},
            "new_cap_nanos": 2 * cap, "sdk_retries": 0, "automatic_resume": False,
            "runtime_hash": runner._runtime_hash(), "git_commit": git_commit(),
            "implementation_hash": exposure.implementation_hash(),
            "rubric_hash": sha256_bytes((repository_root() / RUBRIC).read_bytes())}


def fork(plan, row, output, *, live_mode=False):
    source = Source.from_record(plan["source"])
    with parent_reads(source):
        # Internal B preserves all observations; the experiment changes only probe schema.
        branch = exposure._fork(
            source, plan["cut_sequence"], output, "B",
            new_cap_usd=Decimal(row["new_cap_nanos"]) / 10**9,
            mode="funded-observation" if live_mode else "offline-scripted-only",
            env_file=Path(plan["env_file"]) if live_mode else output / "NO_CREDENTIAL_FILE",
            preserve_parent_configuration=True)
    branch.journal.append("probe_action_comparison_arm", {
        "arm": row["arm"], "intervention": "probe_action_replay_schema_only",
        "target_action_id_is_operator_metadata_only": True})
    return branch


def environment(plan):
    return live.check_environment(plan, Path(plan["env_file"]))


def prepare(source, sequence, target, env_file, result_root, row_cap_usd, output):
    plan = controls(source, sequence, target, env_file, result_root, row_cap_usd)
    disjoint(output.resolve(), (repository_root(), source.root, source.public_path.parent,
                                result_root.resolve()))
    live.clean_implementation()
    runner._require_tracked_clean_paths(repository_root(), [RUBRIC])
    output.mkdir()
    journal = DevJournal(output, "run_dev_probeactionpreparation")
    requests = {}
    for row in plan["rows"]:
        branch = fork(plan, row, output / row["label"])
        client = ScriptedClient([[{"name": "stop_task", "action_id": "preparation_stop",
            "arguments": {"reason_code": "insufficient_public_evidence",
                "summary": "Offline preparation only.", "turn_decision": {
                    "mode": "stop", "basis": "Synthetic preparation only.",
                    "evidence_goal": None, "memory_update": None, "plan_update": None}}}]])
        with surface(row["arm"]):
            receipt = exposure.rehearse(branch, client)
        require(receipt["result"]["terminal"] == "AGENT_STOPPED"
                and len(client.counted) == len(client.created) == 1, "restoration failed")
        request = live.normalized(client.created[0])
        require(plan["target_action_id"] in request["input"][-1]["content"],
                "target ID absent from rebuilt state")
        requests[row["label"]] = request
        artifact = ArtifactStore(output / "artifacts").put_json(request)
        journal.append("first_input_checked", {"row": row["label"], "request":
            artifact.model_dump(mode="json"), "receipt": receipt, "provider_calls": 0})
    expected_a = {**requests["B"], "tools": project_tools(requests["B"]["tools"], "A")}
    require(requests["A"] == expected_a, "pair differs beyond the probe schema")
    plan["first_request_hashes"] = {key: sha256_json(value) for key, value in requests.items()}
    raw = (canonical_json(plan) + "\n").encode()
    (output / "manifest.json").write_bytes(raw)
    preflight = environment(plan)
    result = {"manifest": str(output / "manifest.json"), "manifest_hash": sha256_bytes(raw),
              "preflight": preflight, "provider_calls": 0, "cost_nanos": 0,
              "pair_diff": "run_probe schema only", "paid_execution_authorized": False}
    journal.append("preparation_finished", result)
    (output / "preparation.json").write_text(canonical_json(result), encoding="utf-8")
    return result


def collect(manifest_path, approved_hash, approved_cap_usd):
    raw = manifest_path.read_bytes()
    require(sha256_bytes(raw) == approved_hash, "approved manifest differs")
    plan = json.loads(raw)
    require(usd_to_nanos(approved_cap_usd) == plan["new_cap_nanos"], "approved cap differs")
    source = Source.from_record(plan["source"])
    root, env_file = Path(plan["result_root"]), Path(plan["env_file"])
    expected = controls(source, plan["cut_sequence"], plan["target_action_id"], env_file, root,
                        Decimal(plan["rows"][0]["new_cap_nanos"]) / 10**9)
    require({k: v for k, v in plan.items() if k != "first_request_hashes"} == expected,
            "prepared controls changed")
    disjoint(root, (manifest_path.parent,))
    live.clean_implementation()
    runner._require_tracked_clean_paths(repository_root(), [RUBRIC])
    root.mkdir()
    journal = DevJournal(root, "run_dev_probeactioncomparison")
    store = ArtifactStore(root / "artifacts")
    group = DevCostLedger(approved_cap_usd, pricing_for_model(plan["model"]))
    rows = [{"row": row["label"], "status": "NOT_RUN"} for row in plan["rows"]]
    known, stop_reason = True, None
    with journal.execution_lock():
        journal.append("comparison_authorized", {"manifest_hash": approved_hash, "plan": plan})
        for i, row in enumerate(plan["rows"]):
            preflight = environment(plan)
            journal.append("environment_checked", {"row": row["label"], **preflight})
            if preflight["status"] != "READY":
                stop_reason = "PREFLIGHT_FAILED"
                break
            branch = None
            try:
                branch = fork(plan, row, root / row["label"], live_mode=True)
                with surface(row["arm"]):
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
                break
        result = {"official": False, "rows": rows, "stop_reason": stop_reason,
                  "billing_known": known, "new_cost_nanos": group.spent_nanos if known else None,
                  "new_cap_nanos": group.cap_nanos, "fresh_solve": False,
                  "efficacy_claim": "NOT_ESTABLISHED", "historical_allocations_reopened": False}
        journal.append("comparison_finished", result)
        (root / "result.json").write_text(canonical_json(result), encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    for name in ("case", "env-file", "result-root", "output"):
        prep.add_argument("--" + name, type=Path, required=True)
    prep.add_argument("--row-cap-usd", type=Decimal, required=True)
    run = sub.add_parser("collect")
    run.add_argument("--manifest", type=Path, required=True)
    run.add_argument("--approved-manifest-hash", required=True)
    run.add_argument("--approved-new-cap-usd", type=Decimal, required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        case = json.loads(args.case.read_bytes())
        result = prepare(Source.from_record(case["source"]), case["cut_sequence"],
                         case["target_action_id"], args.env_file, args.result_root,
                         args.row_cap_usd, args.output)
    else:
        result = collect(args.manifest, args.approved_manifest_hash, args.approved_new_cap_usd)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
