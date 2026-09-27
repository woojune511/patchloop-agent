"""Ten provider-free normal/caller-cancel probes on base and four saved final patches."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path

from diagnostics.anyio_cleanup_probe import restore_first
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

PROGRAM = Path(__file__).parent / "probes/anyio_caller_cancel_preservation.py"
TARGET = "src/anyio/_backends/_asyncio.py"


def final_mutations(root, run_id, expected_journal_hash):
    journal = DevJournal(root, run_id)
    require(
        sha256_bytes(journal.path.read_bytes()) == expected_journal_hash,
        "saved candidate journal changed",
    )
    events = journal.events()
    mutations = []
    for event in events:
        if (
            event["event_type"] != "action_started"
            or event["payload"].get("tool") != "replace_text"
        ):
            continue
        started = event["payload"]
        result = next(
            e["payload"]["result"]
            for e in events
            if e["event_type"] == "action_finished"
            and e["payload"]["action_id"] == started["action_id"]
        )
        require(
            started["mutation_target_path"] == TARGET
            and result["error_code"] is None
            and result["input_hash"] == started["input_hash"]
            and result["output"]["mutation"]["diff_hash"]
            == started["mutation_expected_worktree_diff_hash"],
            "accepted mutation differs",
        )
        mutations.append(started)
    require(len(mutations) == 2, "one inherited and one new repair required")
    require(
        events[-1]["event_type"] == "terminal"
        and events[-1]["payload"]["terminal"] == "EVALUATOR_PASS",
        "accepted final run required",
    )
    return mutations


def run(manifest_path, audit_path, live_root, output):
    plan, audit = (json.loads(p.read_bytes()) for p in (manifest_path, audit_path))
    require(
        sha256_bytes(manifest_path.read_bytes()) == audit["manifest_hash"]
        and live_root.resolve() == Path(plan["result_root"]).resolve(),
        "closed run binding differs",
    )
    audit_store = ArtifactStore(audit_path.parent / "artifacts")
    audit_events = DevJournal(audit_path.parent, "run_dev_checkpointcomparisonaudit").events()
    audit_ref = audit_events[-1]["payload"]["artifact"]
    require(
        json.loads(audit_store.read_bytes(Artifact.model_validate(audit_ref))) == audit,
        "audit differs from its journal artifact",
    )
    _, source, envelope = source_state(Path(plan["packet"]), plan["packet_hash"])
    disjoint(
        output.resolve(),
        (
            repository_root(),
            live_root.resolve(),
            source.root,
            manifest_path.parent.resolve(),
            audit_path.parent.resolve(),
        ),
    )
    public = load_public_task(source.public_path)
    labels = ("BASE", "A1", "A2", "B1", "B2")
    mutations = {
        label: final_mutations(
            live_root / label,
            source.run_id,
            next(r["journal_hash"] for r in audit["rows"] if r["row"] == label),
        )
        for label in labels
        if label != "BASE"
    }
    output.mkdir()
    journal = DevJournal(output, "run_dev_callerpreservation")
    store = ArtifactStore(output / "artifacts")
    programs = {
        flag: f"CANCEL = {flag!r}\n" + PROGRAM.read_text(encoding="utf-8") for flag in (False, True)
    }
    journal.append(
        "cleanup_probe_prepared",
        {
            "official": False,
            "origin": "operator",
            "head": git_commit(),
            "runtime_hash": runtime_content_hash(),
            "manifest_hash": audit["manifest_hash"],
            "audit_hash": sha256_bytes(audit_path.read_bytes()),
            "driver_hash": sha256_bytes(Path(__file__).read_bytes()),
            "cases": ["normal_release", "waiting_caller_cancel"],
            "programs": {
                str(k): store.put_text(v).model_dump(mode="json") for k, v in programs.items()
            },
            "mutations": mutations,
            "max_probe_executions": 2 * len(labels),
        },
    )
    dependencies = runner.load_dependencies(
        Path(envelope.prepared_probe_dependencies_path), public, envelope.probe_dependencies
    )
    probe = DockerProbeSandbox(dependencies=dependencies)
    identity = probe.preflight(deadline=ExecutionDeadline.from_remaining(120))
    require(
        identity
        == {
            "image_digest": envelope.probe_image_digest,
            "profile_hash": envelope.probe_profile_hash,
        },
        "probe identity changed",
    )
    journal.append("cleanup_environment_ready", identity)
    manager = WorkspaceManager(
        repository_root() / "fixtures/repositories",
        output / "workspaces",
        prepared_source=Path(envelope.prepared_source_path),
        prepared_source_hash=envelope.prepared_source_hash,
    )
    rows, containers = [], []
    for label in labels:
        workspace = manager.create(
            "cleanup_" + label,
            public.repository.url,
            public.repository.base_commit,
            deadline=ExecutionDeadline.from_remaining(120),
        )
        for mutation in mutations.get(label, []):
            restore_first(workspace, mutation)
        before = manager.diff_summary(workspace)
        journal.append(
            "candidate_materialized",
            {
                "row": label,
                "diff_hash": before.patch_hash,
                "patch": store.put_text(before.patch).model_dump(mode="json"),
                "source_hash": sha256_bytes((workspace / TARGET).read_bytes()),
            },
        )
        for cancel, program in programs.items():
            execution = {
                "run_id": journal.run_id,
                "action_id": label + "_" + str(cancel),
                "input_hash": sha256_json({"source": program, "diff": before.patch_hash}),
            }
            journal.append(
                "cleanup_probe_started",
                {"row": label, "cancel": cancel, "execution_identity": execution},
            )
            receipt = probe.run_probe(
                workspace,
                "Does cancelling the waiting caller stop its task and preserve fixture teardown?",
                program,
                deadline=ExecutionDeadline.from_remaining(120),
                execution_identity=execution,
            )
            ref = store.put_json(receipt)
            journal.append(
                "cleanup_probe_finished",
                {"row": label, "cancel": cancel, "artifact": ref.model_dump(mode="json")},
            )
            require(
                receipt["status"] == "passed"
                and receipt["exit_code"] == 0
                and not any(
                    receipt.get(k)
                    for k in ("cleanup_failed", "timed_out", "truncated", "deadline_exhausted")
                )
                and receipt["source_hash"] == sha256_bytes(program.encode()),
                "probe receipt is incomplete; stop without retry",
            )
            rows.append(
                {
                    "row": label,
                    "cancel": cancel,
                    "diff_hash": before.patch_hash,
                    "observation": json.loads(receipt["stdout"]),
                    "receipt": ref.model_dump(mode="json"),
                }
            )
            containers.append(probe.container_name(execution))
            require(manager.diff_summary(workspace) == before, "probe changed candidate workspace")
    inventory = subprocess.run(
        [shutil.which("docker"), "container", "ls", "--all", "--format", "{{.Names}}"],
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    require(
        not set(containers) & set(inventory.stdout.splitlines()), "owned probe container remains"
    )
    result = {
        "official": False,
        "origin": "operator",
        "rows": rows,
        "cases": ["normal_release", "waiting_caller_cancel"],
        "owned_containers_absent": containers,
        "model_calls": 0,
        "input_counts": 0,
        "new_billed_cost_nanos": 0,
        "acceptance": "NOT_RUN",
        "safety": "NOT_RUN",
    }
    ref = store.put_json(result)
    journal.append("cleanup_observation_completed", {"artifact": ref.model_dump(mode="json")})
    (output / "result.json").write_text(canonical_json(result) + "\n", encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("manifest", "audit", "live-root", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    result = run(args.manifest, args.audit, args.live_root, args.output)
    print(
        json.dumps(
            {
                "rows": [
                    {"row": r["row"], "cancel": r["cancel"], "outcome": r["observation"]["outcome"]}
                    for r in result["rows"]
                ],
                "model_calls": 0,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
