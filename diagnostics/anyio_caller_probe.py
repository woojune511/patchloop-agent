"""Provider-free caller-state discriminator on a fresh, unchanged public source."""

from __future__ import annotations

import argparse
import ast
import json
import shutil
import subprocess
from pathlib import Path

from diagnostics.checkpoint_comparison import source_state
from diagnostics.decision_sampler import require
from diagnostics.declaration_checkpoint import disjoint
from patchloop.artifacts import ArtifactStore
from patchloop.deadline import ExecutionDeadline
from patchloop.dev import runner
from patchloop.dev.state import DevJournal
from patchloop.repository import WorkspaceManager
from patchloop.runtime import git_commit, repository_root, runtime_content_hash
from patchloop.sandbox.probes import DockerProbeSandbox
from patchloop.task_loader import load_public_task
from patchloop.util import canonical_json, sha256_bytes, sha256_json

MODES = ("callback_interrupt", "explicit_caller_cancel")
PROGRAM = Path(__file__).parent / "probes/anyio_caller_state.py"


def program(mode):
    require(mode in MODES, "unknown probe mode")
    return f"MODE = {mode!r}\n" + PROGRAM.read_text(encoding="utf-8")


def interpret(rows):
    """Require a working positive control before interpreting the zero observation."""
    by_mode = {row["mode"]: {o["stage"]: o for o in row["observations"]} for row in rows}
    require(set(by_mode) == set(MODES), "both observations are required")
    interrupt, control = (by_mode[mode] for mode in MODES)
    requested = control["after_cancel_request"]
    raised = control["run_test_raised"]
    require(requested["cancel_returned"] is True
            and requested["caller"] == {"done": False, "cancelled": False, "cancelling": 1}
            and raised["exception"] == "CancelledError"
            and raised["caller"] == {"done": True, "cancelled": True, "cancelling": 1},
            "explicit cancellation control did not validate the observation")
    require(interrupt["run_test_raised"]["exception"] == "KeyboardInterrupt",
            "callback interruption was not reproduced")
    pending = {"done": False, "cancelled": False, "cancelling": 0}
    checkpoints = ("before_trigger", "run_test_raised", "before_teardown")
    not_cancelled = all(interrupt[stage]["caller"] == pending for stage in checkpoints)
    cancelled = any(interrupt[stage]["caller"]["cancelled"]
                    or interrupt[stage]["caller"]["cancelling"] > 0 for stage in checkpoints)
    return {"verdict": "INTERRUPT_WITHOUT_CALLER_CANCELLATION" if not_cancelled else
            "CALLER_CANCELLATION_OBSERVED" if cancelled else "INCONCLUSIVE",
            "caller_cancellation_observed_after_interrupt": cancelled,
            "waiting_caller_was_pending_without_cancellation": not_cancelled,
            "positive_control_verified": True,
            "scope": "This callback-triggered KeyboardInterrupt on the unchanged task base only.",
            "agent_improvement": "NOT_RUN", "acceptance": "NOT_RUN", "safety": "NOT_RUN"}


def parity(original_stdout, observation):
    """Compare original public lifecycle observations, ignoring process-local task IDs."""
    original = [ast.literal_eval(line) for line in original_stdout.splitlines()]
    current = {o["stage"]: o for o in observation["observations"]}
    for old in original:
        new = current[old["stage"]]
        require([e[0] for e in old["events"]] == [e["name"] for e in new["events"]]
                and old["runner_task_done"] == new["runner"]["done"],
                "instrumented lifecycle differs from the saved original observation")
        if "type" in old:
            require(old["type"] == new["exception"], "interruption type changed")
        owner_id = old["events"][0][1]
        require([e[1] == owner_id for e in old["events"]]
                == [e["same_fixture_task"] for e in new["events"]], "task ownership changed")
    return {"matched_stages": len(original), "same_event_order_and_task_ownership": True,
            "limit": "Matches saved discrete observations; not proof of all timing equivalence."}


def run(packet_path, packet_hash, output):
    _, source, envelope = source_state(packet_path, packet_hash)
    disjoint(output.resolve(), (repository_root(), source.root, packet_path.parent))
    require(envelope.prepared_source_path is not None
            and envelope.prepared_probe_dependencies_path is not None, "prepared inputs required")
    public = load_public_task(source.public_path)
    output.mkdir()
    journal = DevJournal(output, "run_dev_callerstateprobe")
    store = ArtifactStore(output / "artifacts")
    frozen = {mode: program(mode) for mode in MODES}
    journal.append("operator_probe_prepared", {
        "official": False, "origin": "operator", "model_calls": 0,
        "head": git_commit(), "runtime_hash": runtime_content_hash(),
        "packet_hash": packet_hash,
        "public_task_hash": sha256_bytes(source.public_path.read_bytes()),
        "implementation_hash": sha256_bytes(Path(__file__).read_bytes()),
        "programs": {m: store.put_text(s).model_dump(mode="json") for m, s in frozen.items()},
    })
    deadline = ExecutionDeadline.from_remaining(120)
    dependencies = runner.load_dependencies(Path(envelope.prepared_probe_dependencies_path),
                                             public, envelope.probe_dependencies)
    probe = DockerProbeSandbox(dependencies=dependencies)
    identity = probe.preflight(deadline=deadline)
    require(identity == {"image_digest": envelope.probe_image_digest,
                         "profile_hash": envelope.probe_profile_hash}, "probe identity changed")
    manager = WorkspaceManager(repository_root() / "fixtures/repositories", output / "workspaces",
                               prepared_source=Path(envelope.prepared_source_path),
                               prepared_source_hash=envelope.prepared_source_hash)
    workspace = manager.create(journal.run_id, public.repository.url, public.repository.base_commit,
                               deadline=deadline)
    before = manager.diff_summary(workspace)
    require(not before.changed_files and not before.untracked_files, "task base must be unchanged")
    journal.append("operator_environment_ready", {
        **identity, "base_commit": public.repository.base_commit, "diff_hash": before.patch_hash})
    observations, receipts, containers = [], [], []
    for mode in MODES:
        execution = {"run_id": journal.run_id, "action_id": mode,
                     "input_hash": sha256_json({"source": frozen[mode], "diff": before.patch_hash})}
        journal.append("operator_probe_started", {"mode": mode, "execution_identity": execution})
        receipt = probe.run_probe(workspace, "Is the waiting caller cancelled at this boundary?",
                                  frozen[mode], deadline=ExecutionDeadline.from_remaining(120),
                                  execution_identity=execution)
        ref = store.put_json(receipt)
        journal.append("operator_probe_finished", {
            "mode": mode, "artifact": ref.model_dump(mode="json")})
        receipts.append({"mode": mode, "artifact": ref.model_dump(mode="json")})
        require(receipt["status"] == "passed" and receipt["exit_code"] == 0
                and not any(receipt.get(k) for k in
                            ("cleanup_failed", "timed_out", "truncated", "deadline_exhausted")),
                "probe did not complete cleanly; do not interpret or continue")
        require(receipt["source_hash"] == sha256_bytes(frozen[mode].encode()),
                "probe source changed")
        observations.append(json.loads(receipt["stdout"]))
        containers.append(probe.container_name(execution))
    original_events = DevJournal(source.root, source.run_id).events()
    original_probe = next(e["payload"]["result"]["output"] for e in original_events
                          if e["event_type"] == "action_finished"
                          and e["payload"]["result"]["tool"] == "run_probe")
    result = {"official": False, "origin": "operator", "model_calls": 0, "input_counts": 0,
              "new_billed_cost_nanos": 0, "observations": observations, "receipts": receipts,
              "lifecycle_parity": parity(original_probe["stdout"], observations[0]),
              "interpretation": interpret(observations)}
    require(manager.diff_summary(workspace) == before, "probe changed source workspace")
    inventory = subprocess.run(
        [shutil.which("docker"), "container", "ls", "--all", "--format", "{{.Names}}"],
        capture_output=True, text=True, timeout=30, check=True)
    result["containers"] = [{"name": name, "absent": name not in inventory.stdout.splitlines()}
                            for name in containers]
    require(all(c["absent"] for c in result["containers"]), "owned container remains")
    ref = store.put_json(result)
    journal.append("operator_observation_completed", {"artifact": ref.model_dump(mode="json")})
    (output / "result.json").write_text(canonical_json(result) + "\n", encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--packet-hash", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.packet, args.packet_hash, args.output), indent=2))


if __name__ == "__main__":
    main()
