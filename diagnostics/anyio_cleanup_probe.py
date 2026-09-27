"""Bounded operator-only cleanup discriminator on saved first public patches."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path

from diagnostics.checkpoint_comparison import source_state
from diagnostics.decision_sampler import require
from diagnostics.declaration_checkpoint import disjoint
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact
from patchloop.deadline import ExecutionDeadline
from patchloop.dev import runner
from patchloop.dev.state import DevJournal
from patchloop.repository import WorkspaceManager
from patchloop.runtime import git_commit, repository_root, runtime_content_hash
from patchloop.sandbox.probes import DockerProbeSandbox
from patchloop.task_loader import load_public_task
from patchloop.util import canonical_json, sha256_bytes, sha256_json

PROGRAM = Path(__file__).parent / "probes/anyio_cleanup_trace.py"
TARGET = "src/anyio/_backends/_asyncio.py"
REDUNDANT = ("            self._runner_task.cancel()\n"
             "            raise\n        finally:")


def omit_caller_cancel(text):
    require(text.count(REDUNDANT) == 1, "expected one caller-side cancellation site")
    return text.replace(REDUNDANT, "            raise\n        finally:", 1)


def first_mutation(root, run_id, expected_journal_hash):
    journal = DevJournal(root, run_id)
    require(sha256_bytes(journal.path.read_bytes()) == expected_journal_hash,
            "saved candidate journal changed")
    events = journal.events()
    fork = next(e for e in events if e["event_type"] == "diagnostic_checkpoint_fork")
    started = next(e["payload"] for e in events if e["sequence"] > fork["sequence"]
                   and e["event_type"] == "action_started"
                   and e["payload"]["tool"] == "replace_text")
    finished = next(e["payload"]["result"] for e in events if e["event_type"] == "action_finished"
                    and e["payload"]["action_id"] == started["action_id"])
    require(started["mutation_target_path"] == TARGET and started["baseline_changed_files"] == []
            and finished["error_code"] is None
            and finished["input_hash"] == started["input_hash"]
            and finished["output"]["mutation"]["diff_hash"]
            == started["mutation_expected_worktree_diff_hash"], "first repair identity differs")
    return started


def restore_first(workspace, mutation):
    target = workspace / TARGET
    before = target.read_bytes()
    require(sha256_bytes(before) == mutation["mutation_preimage_file_hash"],
            "prepared source differs from first repair preimage")
    args, newline = mutation["arguments"], mutation["mutation_preimage_newline"]
    old = args["old_text"].replace("\n", newline).encode()
    new = args["new_text"].replace("\n", newline).encode()
    require(before.count(old) == 1, "first repair anchor is not unique")
    after = before.replace(old, new, 1)
    require(sha256_bytes(after) == mutation["mutation_expected_postimage_file_hash"],
            "restored first repair postimage differs")
    target.write_bytes(after)
    require(WorkspaceManager.diff_summary(workspace).patch_hash
            == mutation["mutation_expected_worktree_diff_hash"],
            "restored first repair diff differs")


def run(manifest_path, audit_path, live_root, output, *, remove_caller_cancel=False):
    plan, audit = (json.loads(p.read_bytes()) for p in (manifest_path, audit_path))
    require(sha256_bytes(manifest_path.read_bytes()) == audit["manifest_hash"]
            and live_root.resolve() == Path(plan["result_root"]).resolve(),
            "closed run binding differs")
    audit_store = ArtifactStore(audit_path.parent / "artifacts")
    audit_events = DevJournal(audit_path.parent, "run_dev_checkpointcomparisonaudit").events()
    audit_ref = audit_events[-1]["payload"]["artifact"]
    require(json.loads(audit_store.read_bytes(Artifact.model_validate(audit_ref))) == audit,
            "audit differs from its journal artifact")
    _, source, envelope = source_state(Path(plan["packet"]), plan["packet_hash"])
    disjoint(output.resolve(), (repository_root(), live_root.resolve(), source.root,
                                manifest_path.parent.resolve(), audit_path.parent.resolve()))
    public = load_public_task(source.public_path)
    labels = ("B1",) if remove_caller_cancel else ("B1", "B2")
    mutations = {label: first_mutation(
        live_root / label, source.run_id,
        next(r["journal_hash"] for r in audit["rows"] if r["row"] == label)) for label in labels}
    output.mkdir()
    journal = DevJournal(output, "run_dev_cleanupprobe")
    store = ArtifactStore(output / "artifacts")
    programs = {flag: f"TRACE = {flag!r}\n" + PROGRAM.read_text(encoding="utf-8")
                for flag in (False, True)}
    journal.append("cleanup_probe_prepared", {
        "official": False, "origin": "operator", "head": git_commit(),
        "runtime_hash": runtime_content_hash(), "manifest_hash": audit["manifest_hash"],
        "audit_hash": sha256_bytes(audit_path.read_bytes()),
        "driver_hash": sha256_bytes(Path(__file__).read_bytes()),
        "remove_caller_cancel": remove_caller_cancel,
        "programs": {str(k): store.put_text(v).model_dump(mode="json")
                     for k, v in programs.items()},
        "mutations": mutations, "max_probe_executions": 2 * len(labels),
    })
    dependencies = runner.load_dependencies(Path(envelope.prepared_probe_dependencies_path),
                                             public, envelope.probe_dependencies)
    probe = DockerProbeSandbox(dependencies=dependencies)
    identity = probe.preflight(deadline=ExecutionDeadline.from_remaining(120))
    require(identity == {"image_digest": envelope.probe_image_digest,
                         "profile_hash": envelope.probe_profile_hash}, "probe identity changed")
    journal.append("cleanup_environment_ready", identity)
    manager = WorkspaceManager(repository_root() / "fixtures/repositories", output / "workspaces",
                               prepared_source=Path(envelope.prepared_source_path),
                               prepared_source_hash=envelope.prepared_source_hash)
    rows, containers = [], []
    for label in labels:
        workspace = manager.create("cleanup_" + label, public.repository.url,
                                   public.repository.base_commit,
                                   deadline=ExecutionDeadline.from_remaining(120))
        restore_first(workspace, mutations[label])
        if remove_caller_cancel:
            target = workspace / TARGET
            newline = mutations[label]["mutation_preimage_newline"]
            changed = omit_caller_cancel(target.read_text(encoding="utf-8"))
            target.write_bytes(changed.replace("\n", newline).encode())
        before = manager.diff_summary(workspace)
        journal.append("candidate_materialized", {
            "row": label, "diff_hash": before.patch_hash,
            "patch": store.put_text(before.patch).model_dump(mode="json"),
            "source_hash": sha256_bytes((workspace / TARGET).read_bytes()),
        })
        for traced, program in programs.items():
            execution = {"run_id": journal.run_id, "action_id": label + "_" + str(traced),
                         "input_hash": sha256_json({"source": program, "diff": before.patch_hash})}
            journal.append("cleanup_probe_started", {"row": label, "trace": traced,
                           "execution_identity": execution})
            receipt = probe.run_probe(workspace, "Where does interrupted fixture cleanup block?",
                                      program, deadline=ExecutionDeadline.from_remaining(120),
                                      execution_identity=execution)
            ref = store.put_json(receipt)
            journal.append("cleanup_probe_finished", {"row": label, "trace": traced,
                           "artifact": ref.model_dump(mode="json")})
            require(receipt["status"] == "passed" and receipt["exit_code"] == 0
                    and not any(receipt.get(k) for k in
                                ("cleanup_failed", "timed_out", "truncated", "deadline_exhausted"))
                    and receipt["source_hash"] == sha256_bytes(program.encode()),
                    "probe receipt is incomplete; stop without retry")
            rows.append({"row": label, "trace": traced, "diff_hash": before.patch_hash,
                         "observation": json.loads(receipt["stdout"]),
                         "receipt": ref.model_dump(mode="json")})
            containers.append(probe.container_name(execution))
            require(manager.diff_summary(workspace) == before, "probe changed candidate workspace")
    inventory = subprocess.run(
        [shutil.which("docker"), "container", "ls", "--all", "--format", "{{.Names}}"],
        capture_output=True, text=True, timeout=30, check=True)
    require(not set(containers) & set(inventory.stdout.splitlines()),
            "owned probe container remains")
    result = {"official": False, "origin": "operator", "rows": rows,
              "remove_caller_cancel": remove_caller_cancel,
              "owned_containers_absent": containers, "model_calls": 0, "input_counts": 0,
              "new_billed_cost_nanos": 0, "acceptance": "NOT_RUN", "safety": "NOT_RUN"}
    ref = store.put_json(result)
    journal.append("cleanup_observation_completed", {"artifact": ref.model_dump(mode="json")})
    (output / "result.json").write_text(canonical_json(result) + "\n", encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("manifest", "audit", "live-root", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--remove-caller-cancel", action="store_true")
    args = parser.parse_args()
    result = run(args.manifest, args.audit, args.live_root, args.output,
                 remove_caller_cancel=args.remove_caller_cancel)
    print(json.dumps({"rows": [{"row": r["row"], "trace": r["trace"],
                               "outcome": r["observation"]["outcome"]} for r in result["rows"]],
                      "model_calls": 0}, indent=2))


if __name__ == "__main__":
    main()
