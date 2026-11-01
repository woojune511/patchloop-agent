"""Provider-free comparison of the saved second and third Astroid repair candidates."""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path

from diagnostics.cleanup_information_checkpoint import restore_candidate
from diagnostics.decision_sampler import require
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import ProbeDependencyIdentity
from patchloop.deadline import ExecutionDeadline
from patchloop.dev import reproduction
from patchloop.dev.state import DevJournal
from patchloop.prepared_probe_dependencies import load_dependencies
from patchloop.repository import WorkspaceManager
from patchloop.runtime import git_commit, repository_root, runtime_content_hash
from patchloop.sandbox.probes import DockerProbeSandbox
from patchloop.util import canonical_json, sha256_bytes, sha256_json

PARENT = Path("C:/pt/post-reproduction-repair-run-v1/repair")
RUN_ID = "run_dev_3e21775752a54cae"
PARENT_HASH = "sha256:3523fbf47b6b49cee0a40830a8efeeb69da9d233c8e1e6ee708373c35332b7d0"
TRACE = Path(__file__).parent / "probes/astroid_processing_trace.py"
SOURCE = Path("C:/pt/ld20p01/s/13/prepared-source.json")
DEPS = Path("C:/pt/calleruptake18/preparation-v2/B/prepared-probe-dependencies.json")
TASK = "tasks/dev-train/current-dev20/13/public.yaml"
MARKER = "PATCHLOOP-PROCESSING:"
ORDER = ("candidate2", "candidate3")


def program(source, binding):
    require(sha256_bytes(source.encode()) == binding["program_hash"], "original program changed")
    observer = ast.unparse(ast.parse(TRACE.read_text(encoding="utf-8")))
    execution = reproduction.program(source, binding)
    execution = (observer + "\ninstall_processing_trace()\n" + execution
                 + f"\nprint({MARKER!r} + _pt_json.dumps(finish_processing_trace(),"
                 "separators=(',', ':')))\n")
    compile(execution, "<operator-processing-comparison>", "exec")
    return execution


def parse(receipt, binding, saved):
    require(receipt["status"] == "passed" and receipt["exit_code"] == 0
            and not any(receipt.get(k) for k in
                        ("cleanup_failed", "timed_out", "truncated", "deadline_exhausted")),
            "incomplete probe; stop without retry")
    # This exact original program never calls check_setup. Its fixture identity
    # is verified by the complete original-call snapshot parity below.
    require(receipt.get("setup_checks", {}).get("status") == "not_checked"
            and receipt["setup_checks"].get("checks") == [], "original setup contract changed")
    require(receipt.get("execution_policy", {}).get("cleanup_status") == "confirmed",
            "cleanup not confirmed")
    lines = [line[len(MARKER):] for line in receipt["stdout"].splitlines()
             if line.startswith(MARKER)]
    require(len(lines) == 1, "missing or multiple processing reports")
    trace = json.loads(lines[0])
    require(trace["complete"], "incomplete processing trace")
    result = reproduction.compare(receipt, binding)["reproduction"]
    require(result["call_observation"]["calls"] == saved["call_observation"]["calls"],
            "instrumentation changed original call inputs or outcomes")
    require(result["observed_json"] == saved["observed_json"], "observation changed")
    require(result["comparison"] == saved["comparison"], "comparison changed")
    return {"trace": trace, "reproduction": result, "saved_call_parity": True}


def reuse_candidate2(root, execution, diff_hash):
    """Reuse only the settled first receipt from this diagnostic's parser stop."""
    events = DevJournal(root, "run_dev_fileprocessing").events()
    require([e["event_type"] for e in events] == [
        "processing_comparison_frozen", "processing_probe_started",
        "processing_probe_finished", "processing_comparison_stopped"],
        "reuse requires the single settled first probe")
    start, finish = events[1]["payload"], events[2]["payload"]
    require(start["condition"] == finish["condition"] == "candidate2"
            and start["diff_hash"] == diff_hash
            and start["identity"]["input_hash"] == sha256_json({
                "execution": execution, "diff": diff_hash})
            and events[3]["payload"]["reason"] == "setup not confirmed",
            "reused execution identity or parser stop changed")
    ref = finish["receipt"]
    data = Path(ref["path"]).read_bytes()
    require(sha256_bytes(data) == ref["content_hash"], "reused receipt changed")
    return json.loads(data), ref


def run(output, reuse_first=None):
    from patchloop.task_loader import load_public_task

    require(not output.exists() and not output.resolve().is_relative_to(repository_root()),
            "fresh external output root required")
    parent = DevJournal(PARENT, RUN_ID)
    parent_path = PARENT / "runs" / f"{RUN_ID}.jsonl"
    require(sha256_bytes(parent_path.read_bytes()) == PARENT_HASH, "saved journal changed")
    events = parent.events()
    require(len(events) == 259, "unexpected parent event count")
    envelope = parent.load_envelope()
    original = events[78]["payload"]
    binding = original["reproduction_binding"]
    source = original["arguments"]["python_source"]
    execution = program(source, binding)
    public = load_public_task(repository_root() / TASK)
    require(public.task_id == envelope.task_id, "public task changed")
    output.mkdir(parents=True)
    journal = DevJournal(output, "run_dev_fileprocessing")
    store = ArtifactStore(output / "artifacts")
    manifest = {
        "schema": "file-processing-comparison-v1", "official": False, "claim_eligible": False,
        "question": "At which stage is file.py omitted, and does the last edit change that stage?",
        "baseline": "candidate2 after accepted mutation at parent seq156",
        "intervention": "candidate3 additionally applies accepted builder mutation at seq248",
        "alternatives": ["omitted during file selection", "selected but omitted during AST/check"],
        "adoption": "diagnostic only; no repair or policy adoption",
        "controls": "exact original program, binding, fixtures, argv, image and dependencies",
        "limits": {"probe_runs": 2, "seconds": 120, "provider_calls": 0},
        "stop": "any incomplete capture, identity drift, observer overflow or cleanup uncertainty",
        "order": list(ORDER), "head": git_commit(), "runtime_hash": runtime_content_hash(),
        "parent": {"path": str(parent_path), "hash": PARENT_HASH},
        "task": TASK, "case_id": binding["case_id"],
        "original_program_hash": binding["program_hash"],
        "prepared_inputs": {str(p): sha256_bytes(p.read_bytes()) for p in (SOURCE, DEPS)},
        "execution": store.put_text(execution).model_dump(mode="json"),
        "implementation": {str(p.relative_to(repository_root())): sha256_bytes(p.read_bytes())
                           for p in (Path(__file__).resolve(), TRACE.resolve())},
        "authorization": "User requested the proposed saved-candidate local path comparison.",
        "reuse_first": str(reuse_first) if reuse_first else None,
    }
    ArtifactStore(output).write_text_immutable(
        output / "manifest.json", canonical_json(manifest) + "\n")
    journal.append("processing_comparison_frozen", manifest)
    try:
        deadline = ExecutionDeadline.from_remaining(120)
        deps = load_dependencies(DEPS, public, ProbeDependencyIdentity.model_validate(
            envelope.probe_dependencies))
        probe = DockerProbeSandbox(dependencies=deps)
        identity = probe.preflight(deadline=deadline)
        require(identity["image_digest"] == envelope.probe_image_digest
                and identity["profile_hash"] == envelope.probe_profile_hash,
                "probe identity changed")
        manager = WorkspaceManager(repository_root() / "fixtures/repositories",
                                   output / "workspaces", prepared_source=SOURCE,
                                   prepared_source_hash=envelope.prepared_source_hash)
        observations = {}
        for name, mutations, replay in (("candidate2", (138, 156), 164),
                                        ("candidate3", (138, 156, 248), 256)):
            workspace = manager.create(name, public.repository.url,
                                       public.repository.base_commit, deadline=deadline)
            for seq in mutations:
                mutation = events[seq - 1]["payload"]
                require(events[seq]["event_type"] == "action_finished"
                        and events[seq]["payload"]["result"]["status"] == "succeeded",
                        "mutation was not accepted")
                restore_candidate(workspace, mutation)
            before = manager.diff_summary(workspace)
            saved = events[replay - 1]["payload"]["result"]["output"]
            require(before.patch_hash == saved["diff_hash"], "candidate diff changed")
            action = {"run_id": journal.run_id, "action_id": name, "input_hash": sha256_json({
                "execution": execution, "diff": before.patch_hash})}
            if name == "candidate2" and reuse_first is not None:
                receipt, original_ref = reuse_candidate2(reuse_first, execution, before.patch_hash)
                ref = store.put_json(receipt).model_dump(mode="json")
                journal.append("processing_probe_reused", {"condition": name, "receipt": ref,
                    "original_receipt": original_ref,
                    "reason": "Original has no check_setup; parse its settled capture, no rerun."})
            else:
                journal.append("processing_probe_started", {"condition": name, "identity": action,
                                                             "diff_hash": before.patch_hash})
                receipt = probe.run_probe(workspace, manifest["question"], execution,
                                          deadline=deadline, execution_identity=action)
                ref = store.put_json(receipt).model_dump(mode="json")
                journal.append("processing_probe_finished", {"condition": name, "receipt": ref})
            require(all(receipt[k] == saved[k] for k in ("image_digest", "profile_hash"))
                    and receipt["execution_policy"]["dependencies"]
                    == saved["execution_policy"]["dependencies"], "saved environment changed")
            require(receipt["source_hash"] == sha256_bytes(execution.encode())
                    and receipt["snapshot_hash"] == saved["snapshot_hash"],
                    "executed source or snapshot changed")
            require(manager.diff_summary(workspace) == before, "probe changed source")
            observations[name] = {**parse(receipt, binding, saved["reproduction"]),
                                  "receipt": ref, "diff_hash": before.patch_hash,
                                  "duration_ms": receipt["duration_ms"]}
        require(sha256_bytes(parent_path.read_bytes()) == PARENT_HASH, "parent changed")
        result = {"status": "COMPLETED", "official": False, "claim_eligible": False,
                  "provider_calls": 0, "new_billed_usd": "0", "observations": observations,
                  "probe_identity": identity, "benchmark_evaluation": "NOT_RUN"}
        ArtifactStore(output).write_text_immutable(
            output / "result.json", canonical_json(result) + "\n")
        journal.append("processing_comparison_completed", {
            "result": store.put_json(result).model_dump(mode="json")})
        return {"status": "COMPLETED", "output": str(output), "provider_calls": 0}
    except Exception as exc:
        journal.append("processing_comparison_stopped", {
            "error_type": type(exc).__name__, "reason": str(exc), "retry": False})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--reuse-candidate2", type=Path)
    args = parser.parse_args()
    print(canonical_json(run(args.output, args.reuse_candidate2)))


if __name__ == "__main__":
    main()
