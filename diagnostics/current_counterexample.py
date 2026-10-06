"""Frozen saved-candidate comparison: the same public program, withheld/observed output."""
from __future__ import annotations

import argparse
import copy
import json
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from diagnostics import candidate_review_repair as seeded
from diagnostics import observation_comparison as live
from diagnostics import observation_exposure as exposure
from diagnostics import probe_action_comparison as replay
from diagnostics.checkpoint_continuation import ScriptedClient, UnexecutedProbe
from diagnostics.decision_sampler import require
from diagnostics.declaration_checkpoint import Source, disjoint
from patchloop.agent.model import OpenAIResponsesAdapter
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact
from patchloop.deadline import ExecutionDeadline
from patchloop.dev import probe_replay, runner
from patchloop.dev.contracts import DevLimits, DevRunRequest
from patchloop.dev.cost import pricing_for_model, usd_to_nanos
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError
from patchloop.repository import WorkspaceManager
from patchloop.runtime import git_commit, repository_root
from patchloop.sandbox import LocalSandbox
from patchloop.util import canonical_json, sha256_bytes, sha256_json

RUBRIC = ".agent/current-counterexample.md"
ROW_CAP, CAP = Decimal("1.20"), Decimal("2.40")
ORDER = ("A", "B")
WITHHELD = "Execution observations are withheld in this condition; no result is supplied."


def local_task(old):
    path = repository_root() / "tasks/dev-train/current-dev20/18/public.yaml"
    _, package = runner._resolve_task_file(path)
    require(package.public_spec_hash == old.public_spec_hash
            and package.task_content_hash == old.task_content_hash,
            "local task differs from source")
    return path


def normalized(request_value):
    value = live.normalized(request_value)
    view = json.loads(value["input"][-1]["content"])
    handoff = view["state"].get("segment_handoff")
    if handoff is not None:
        require(isinstance(handoff.get("segment_id"), str), "segment identity missing")
        handoff["segment_id"] = "independent_fresh_run_segment"
    value["input"][-1]["content"] = canonical_json(view)
    return value


def load_calibration(case):
    require(set(case) == {"source", "cut_sequence", "target_action_id", "calibration"},
            "unexpected case fields")
    source = Source.from_record(case["source"])
    checked = replay.audit(source, case["cut_sequence"], case["target_action_id"])
    path = Path(case["calibration"]["path"])
    raw = path.read_bytes()
    require(sha256_bytes(raw) == case["calibration"]["hash"], "calibration changed")
    data = json.loads(raw)
    require(set(data) == {"schema", "source", "cut_sequence", "target_action_id",
                         "candidate_patch", "candidate_diff_hash", "base_commit", "question",
                         "python_source", "source_hash", "output", "execution_identity",
                         "public_program_origin", "protected_files", "official",
                         "observed_diff_hash_before", "observed_diff_hash_after"},
            "unexpected calibration fields")
    require(data["schema"] == "current-counterexample-calibration-v1"
            and data["official"] is False
            and data["public_program_origin"] == "source_agent_action"
            and all(data[k] == case[k] for k in ("source", "cut_sequence", "target_action_id")),
            "calibration source differs")
    journal = DevJournal(source.root, source.run_id)
    events, old = journal.events(), journal.load_envelope()
    prefix = [e for e in events if e["sequence"] < case["cut_sequence"]]
    program = probe_replay.prepare({"replay_action_id": case["target_action_id"]}, prefix)
    boundary = next(e for e in events if e["sequence"] == case["cut_sequence"])
    with replay.parent_reads(source):
        bundle = json.loads(ArtifactStore(source.root / "artifacts").read_bytes(
            Artifact.model_validate(boundary["payload"]["artifact"])))
    state = json.loads(bundle["request"]["input"][-1]["content"])["state"]
    require(data["candidate_patch"] == state["current_diff"]["patch"]
            and sha256_bytes(data["candidate_patch"].encode()) == data["candidate_diff_hash"]
            == checked["candidate_diff_hash"] == data["observed_diff_hash_before"]
            == data["observed_diff_hash_after"]
            and data["base_commit"] == old.base_commit, "calibration candidate differs")
    require(data["python_source"] == program["python_source"]
            and data["question"] == program["question"]
            and data["source_hash"] == sha256_bytes(data["python_source"].encode()),
            "calibration does not execute the original public program")
    output = data["output"]
    require(output["source_hash"] == data["source_hash"] and output["exit_code"] == 1
            and output["status"] == "failed" and "AssertionError" in output["stderr"],
            "calibration is not a completed assertion failure")
    validate_output(output, old)
    require(isinstance(data["execution_identity"], dict)
            and set(data["execution_identity"]) == {"run_id", "action_id", "input_hash"}
            and data["execution_identity"]["input_hash"] == sha256_json({
                "question": data["question"], "python_source": data["python_source"],
                "diff_hash": data["candidate_diff_hash"]}),
            "calibration execution identity missing")
    require(bool(data["protected_files"]), "calibration provenance missing")
    for filename, digest in data["protected_files"].items():
        require(sha256_bytes(Path(filename).read_bytes()) == digest, "protected evidence changed")
    return data, old


def validate_output(output, old):
    require(not any(output[k] for k in (
        "timed_out", "truncated", "deadline_exhausted", "cleanup_failed")),
        "public execution incomplete")
    require(output["image_digest"] == runner.probe_profile(old.probe_dependencies)["image_digest"]
            and output["profile_hash"] == runner.probe_profile_hash(old.probe_dependencies)
            and output["setup_checks"]["status"] == "passed"
            and output["execution_policy_hash"] == sha256_json(output["execution_policy"])
            and output["execution_policy"]["cleanup_status"] == "confirmed",
            "public execution identity differs")


def feedback(calibration, arm):
    require(arm in ORDER, "unknown arm")
    output = calibration["output"]
    return {"observed_on_diff_hash": calibration["candidate_diff_hash"],
            "requirement": calibration["question"], "python_source": calibration["python_source"],
            "execution_receipt_hash": sha256_json(output),
            "stdout": WITHHELD if arm == "A" else canonical_json({k: output[k] for k in (
                "stdout", "stderr", "exit_code", "setup_checks")}),
            "limitations": "The program and assertions were authored by the source agent from "
                "the public task. Independently interpret their expected behavior. Both arms "
                "receive this program; execution observations may be withheld. This external "
                "execution describes only the initial candidate, not subsequent edits, a "
                "registered check verdict, an acceptance result or a repair instruction."}


def request(plan, root):
    old = DevJournal(Path(plan["source"]["root"]), plan["source"]["run_id"]).load_envelope()
    return DevRunRequest(provider="openai", task=Path(plan["task"]),
        model=plan["model"], env_file=Path(plan["env_file"]), state_root=root,
        max_cost_usd=ROW_CAP, reasoning_effort="xhigh", max_output_tokens=25000,
        limits=DevLimits(max_model_calls=40, max_tool_actions=100, max_accepted_mutations=4,
                         wall_time_seconds=1800), evaluation_reserve_seconds=330,
        context_policy="segmented-v1", retained_source_chars=24000,
        segment_boundary_policy="result-or-size-v1", planning_policy="brief-v1",
        repair_recheck=True, repair_inspection_policy="protected-v1",
        completion_cost_policy="per-call-v1", enable_probes=True,
        probe_policy="none", probe_recheck="none",
        prepared_source=Path(old.prepared_source_path),
        prepared_probe_dependencies=Path(old.prepared_probe_dependencies_path))


def controls(case, env_file, result_root):
    data, old = load_calibration(case)
    require(old.model == "gpt-5.4-mini-2026-03-17", "exact mini source required")
    require(sha256_bytes(str(env_file.resolve()).encode()) == old.credential_file_path_hash,
            "credential path changed")
    source = Source.from_record(case["source"])
    disjoint(result_root.resolve(), (repository_root(), source.root, source.public_path.parent,
                                    Path(case["calibration"]["path"]).parent))
    plan = {"schema": "current-counterexample-v1", "official": False,
            "paid_execution_authorized": False, "case": case, "source": case["source"],
            "task": str(local_task(old)),
            "model": old.model, "env_file": str(env_file.resolve()),
            "result_root": str(result_root.resolve()), "order": list(ORDER),
            "row_cap_nanos": usd_to_nanos(ROW_CAP), "new_cap_nanos": usd_to_nanos(CAP),
            "runtime_hash": runner._runtime_hash(), "git_commit": git_commit(),
            "implementation_hash": exposure.implementation_hash(),
            "rubric_hash": sha256_bytes((repository_root() / RUBRIC).read_bytes()),
            "task_content_hash": old.task_content_hash,
            "public_spec_hash": old.public_spec_hash,
            "calibration_hash": case["calibration"]["hash"],
            "candidate_diff_hash": data["candidate_diff_hash"],
            "executing_probe_identity": {
                "image_digest": runner.probe_profile(old.probe_dependencies)["image_digest"],
                "profile_hash": runner.probe_profile_hash(old.probe_dependencies)},
            "pricing": {k: str(v) for k, v in asdict(pricing_for_model(old.model)).items()},
            "sdk_retries": 0, "automatic_resume": False, "fresh_solve": False}
    plan["request"] = request(plan, result_root / "ROW").model_dump(mode="json")
    return plan


def environment(plan):
    try:
        current = controls(plan["case"], Path(plan["env_file"]), Path(plan["result_root"]))
        current["git_commit"] = plan["git_commit"]
        require(current == {k: v for k, v in plan.items() if k != "first_request_hashes"},
                "frozen controls changed before row admission")
        runner._require_tracked_clean_paths(repository_root(), [RUBRIC])
        local = {**plan, "source": {**plan["source"], "public_path": plan["task"]}}
        return live.check_environment(local, Path(plan["env_file"]))
    except Exception as exc:
        return {"status": "PREFLIGHT_FAILED", "error_type": type(exc).__name__}


def run_seeded(plan, arm, root):
    data, _ = load_calibration(plan["case"])
    return seeded.run_seeded(request(plan, root), seed_patch=data["candidate_patch"],
        seed_hash=data["candidate_diff_hash"], base_commit=data["base_commit"], source_code=[],
        review=None, experiment_hash=sha256_json(plan), source_run_id=plan["source"]["run_id"],
        branch=arm, public_feedback=feedback(data, arm))


def preview(plan, arm, root):
    """Exercise one ordinary input with a finite stop response and no external execution."""
    client = ScriptedClient([[{"name": "stop_task", "action_id": "prepare_stop",
        "arguments": {"reason_code": "insufficient_public_evidence", "summary": "Offline only.",
            "turn_decision": {"mode": "stop", "basis": "Synthetic preparation only.",
                "evidence_goal": None, "memory_update": None, "plan_update": None}}}]])
    _, old = load_calibration(plan["case"])

    def forbidden(*_, **__):
        raise ContractError("network or evaluation forbidden during preparation")

    with (patch("socket.socket.connect", forbidden),
          patch.object(runner, "load_exact_openai_api_key", lambda _: "offline-unused"),
          patch.object(runner, "_live_source_preflight", lambda *a, **k: None),
          patch.object(runner, "_live_sandbox_preflight", lambda *a, **k: LocalSandbox()),
          patch.object(LocalSandbox, "run_check", forbidden),
          patch.object(runner.EvaluationEngine, "evaluate", forbidden),
          patch.object(runner, "DockerProbeSandbox", lambda **kw: UnexecutedProbe(old, **kw)),
          patch.object(runner, "OpenAIResponsesAdapter", lambda config, **kw:
                       OpenAIResponsesAdapter(config, api_key="offline-unused", client=client))):
        result = run_seeded(plan, arm, root)
    require(len(client.counted) == len(client.created) == 1
            and result["runs"][0]["terminal"] == "AGENT_STOPPED", "offline preview failed")
    return normalized(client.created[0])


def prepare(case, env_file, result_root, output):
    plan = controls(case, env_file, result_root)
    disjoint(output.resolve(), (repository_root(), result_root.resolve(),
                               Path(case["source"]["root"]),
                               Path(case["calibration"]["path"]).parent))
    require(not result_root.exists(), "result root already used")
    output.mkdir()
    journal, store = DevJournal(output, "run_dev_counterexamplepreparation"), ArtifactStore(output)
    requests = {arm: preview(plan, arm, output / arm) for arm in ORDER}
    expected = copy.deepcopy(requests["B"])
    view = json.loads(expected["input"][-1]["content"])
    view["state"][seeded.FEEDBACK_FIELD]["stdout"] = WITHHELD
    expected["input"][-1]["content"] = canonical_json(view)
    require(requests["A"] == expected, "pair differs beyond public execution output")
    plan["first_request_hashes"] = {arm: sha256_json(value) for arm, value in requests.items()}
    for arm, value in requests.items():
        store.write_text_immutable(output / f"{arm}-first.json", canonical_json(value) + "\n")
    raw = canonical_json(plan) + "\n"
    store.write_text_immutable(output / "manifest.json", raw)
    preflight = environment(plan)
    receipt = {"manifest": str(output / "manifest.json"),
               "manifest_hash": sha256_bytes(raw.encode()), "preflight": preflight,
               "provider_calls": 0, "cost_nanos": 0, "paid_execution_authorized": False}
    journal.append("preparation_finished", receipt)
    return receipt


def validate(manifest_path, expected_hash=None):
    raw = manifest_path.read_bytes()
    require(expected_hash is None or sha256_bytes(raw) == expected_hash, "manifest changed")
    plan = json.loads(raw)
    expected = controls(plan["case"], Path(plan["env_file"]), Path(plan["result_root"]))
    # Documentation-only commits may follow freezing; executable hashes remain exact.
    expected["git_commit"] = plan["git_commit"]
    require({k: v for k, v in plan.items() if k != "first_request_hashes"} == expected,
            "frozen controls changed")
    require(set(plan["first_request_hashes"]) == set(ORDER), "first inputs missing")
    for arm in ORDER:
        first = json.loads((manifest_path.parent / f"{arm}-first.json").read_bytes())
        require(sha256_json(first) == plan["first_request_hashes"][arm], "first input changed")
    return plan


def run_row(plan, arm, root, journal, first_hash):
    counted, dispatched, captured = [], [], []
    store, original = ArtifactStore(root.parent / "artifacts"), runner._run_one

    class RecordedAdapter(OpenAIResponsesAdapter):
        def count_input_tokens_v2(self, payload, **kwargs):
            self.pending = None
            if not counted:
                require(sha256_json(normalized(payload)) == first_hash,
                        "first input differs from approved preparation")
            journal.append("input_count_started", {"row": arm, "request":
                store.put_json(payload).model_dump(mode="json")})
            counted.append(copy.deepcopy(payload))
            result = super().count_input_tokens_v2(payload, **kwargs)
            self.pending = copy.deepcopy(payload)
            return result

        def execute_request(self, payload, **kwargs):
            expected, self.pending = getattr(self, "pending", None), None
            require(expected is not None, "dispatch lacks a fresh successful count")
            require(0 < payload["max_output_tokens"] <= expected["max_output_tokens"],
                    "output ceiling grew after counting")
            expected["max_output_tokens"] = payload["max_output_tokens"]
            require(payload == expected, "count and dispatch input differ")
            journal.append("dispatch_started", {"row": arm, "request":
                store.put_json(payload).model_dump(mode="json")})
            dispatched.append(True)
            return super().execute_request(payload, **kwargs)

    def one(**kwargs):
        result = original(**kwargs)
        captured.append(result)
        return result

    with (patch.object(runner, "OpenAIResponsesAdapter", RecordedAdapter),
          patch.object(runner, "_run_one", one)):
        result = run_seeded(plan, arm, root)
    require(len(captured) == 1 and len(result["runs"]) == 1, "one row required")
    public = result["runs"][0]
    row_journal = DevJournal(root, public["run_id"])
    known = runner._provider_usage_failure(row_journal) is None
    cost = result["cost_nanos"] if known else None
    require(cost is None or 0 <= cost <= plan["row_cap_nanos"], "row cap exceeded")
    return {"row": arm, "status": "EXECUTED", "result": public, "billing_known": known,
            "new_cost_nanos": cost, "input_counts": len(counted), "dispatches": len(dispatched),
            "stop_remaining": not known or public["terminal"] == "PREFLIGHT_FAILED"
                or (captured[0].stop_remaining and public["terminal"] != "COST_CAP_REACHED")}


def audit_candidate(plan, row, root, journal):
    data, old = load_calibration(plan["case"])
    row_id = row["result"]["run_id"]
    submissions = [e["payload"] for e in DevJournal(root, row_id).events()
                   if e["event_type"] == "submission_recorded"]
    if not submissions:
        return {"verdict": "NOT_RUN", "reason": "no submitted candidate",
                "agent_verification_credit": False}
    require(len(submissions) == 1, "ambiguous submitted candidate")
    workspace = root / "workspaces" / row_id / "repo"
    deadline = ExecutionDeadline.from_remaining(90)
    before = WorkspaceManager.diff_summary(workspace, deadline=deadline)
    require(submissions[0]["patch_hash"] == before.patch_hash,
            "audit workspace differs from submitted candidate")
    _, package = runner._resolve_task_file(Path(plan["task"]))
    deps = runner.load_dependencies(Path(old.prepared_probe_dependencies_path), package.public,
                                    old.probe_dependencies)
    sandbox = runner.DockerProbeSandbox(dependencies=deps)
    require(sandbox.preflight(deadline=deadline) == plan["executing_probe_identity"],
            "audit probe identity changed")
    identity = {"run_id": journal.run_id, "action_id": "audit_" + row["row"],
                "input_hash": sha256_json({"source_hash": data["source_hash"],
                                           "diff_hash": before.patch_hash})}
    journal.append("public_audit_started", {"row": row["row"], "identity": identity,
                                            "candidate_diff_hash": before.patch_hash})
    output = sandbox.run_probe(workspace, data["question"], data["python_source"],
                               deadline=deadline, execution_identity=identity)
    artifact = ArtifactStore(root.parent / "artifacts").put_json(output)
    journal.append("public_audit_finished", {"row": row["row"],
                                            "output": artifact.model_dump(mode="json")})
    validate_output(output, old)
    require(output["source_hash"] == data["source_hash"]
            and WorkspaceManager.diff_summary(workspace, deadline=deadline).patch_hash
            == before.patch_hash, "audit source or candidate changed")
    require(output["exit_code"] == 0 or
            (output["exit_code"] == 1 and "AssertionError" in output["stderr"]),
            "public audit is not an assessable assertion result")
    return {"candidate_diff_hash": before.patch_hash,
            "verdict": "PASS" if output["exit_code"] == 0 else "FAIL",
            "artifact": artifact.model_dump(mode="json"), "agent_verification_credit": False}


def collect(manifest_path, approved_hash, approved_cap_usd):
    require(usd_to_nanos(approved_cap_usd) == usd_to_nanos(CAP), "exact new USD 2.40 required")
    plan = validate(manifest_path, approved_hash)
    root = Path(plan["result_root"])
    disjoint(root.resolve(), (manifest_path.parent.resolve(),))
    require(not root.exists(), "result root already used; no resume")
    root.mkdir()
    journal = DevJournal(root, "run_dev_currentcounterexample")
    rows, known, spent, stop = [], True, 0, None
    with journal.execution_lock():
        journal.append("comparison_authorized", {"manifest_hash": approved_hash, "plan": plan})
        for arm in ORDER:
            preflight = environment(plan)
            journal.append("environment_checked", {"row": arm, **preflight})
            if preflight["status"] != "READY":
                stop = "PREFLIGHT_FAILED"
                break
            try:
                row = run_row(plan, arm, root / arm, journal, plan["first_request_hashes"][arm])
                known = known and row["billing_known"]
                if row["new_cost_nanos"] is not None:
                    spent += row["new_cost_nanos"]
                require(spent <= plan["new_cap_nanos"], "invocation cap exceeded")
            except Exception as exc:
                # A thrown collector error can follow dispatch; never relabel uncertain spend zero.
                known = False
                row = {"row": arm, "status": "COLLECTOR_FAILED", "error_type": type(exc).__name__,
                       "billing_known": False, "new_cost_nanos": None, "stop_remaining": True}
            if not row["stop_remaining"]:
                try:
                    row["public_audit"] = audit_candidate(plan, row, root / arm, journal)
                except Exception as exc:
                    row["public_audit"] = {"verdict": "NOT_ASSESSABLE",
                                           "error_type": type(exc).__name__}
                    row["stop_remaining"] = True
                    row["stop_reason"] = "PUBLIC_AUDIT_UNCERTAIN"
            rows.append(row)
            journal.append("row_finished", row)
            if row["stop_remaining"]:
                stop = row.get("stop_reason", row.get("result", {}).get("terminal", row["status"]))
                break
        result = {"official": False, "rows": rows, "billing_known": known,
                  "new_cost_nanos": spent if known else None,
                  "new_cap_nanos": plan["new_cap_nanos"], "executing_git_commit": git_commit(),
                  "stop_reason": stop, "fresh_solve": False, "allocation": "CLOSED",
                  "automatic_followup": False, "efficacy_claim": "NOT_ESTABLISHED"}
        journal.append("comparison_finished", result)
        ArtifactStore(root).write_text_immutable(
            root / "result.json", canonical_json(result) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    for name in ("case", "env-file", "result-root", "output"):
        prep.add_argument("--" + name, type=Path, required=True)
    check = sub.add_parser("validate")
    check.add_argument("--manifest", type=Path, required=True)
    collect_parser = sub.add_parser("collect")
    collect_parser.add_argument("--manifest", type=Path, required=True)
    collect_parser.add_argument("--approved-manifest-hash", required=True)
    collect_parser.add_argument("--approved-new-cap-usd", type=Decimal, required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        result = prepare(json.loads(args.case.read_bytes()), args.env_file, args.result_root,
                         args.output)
    elif args.command == "validate":
        result = {"verified": bool(validate(args.manifest)), "provider_calls": 0}
    else:
        result = collect(args.manifest, args.approved_manifest_hash, args.approved_new_cap_usd)
    print(canonical_json(result))


if __name__ == "__main__":
    main()
