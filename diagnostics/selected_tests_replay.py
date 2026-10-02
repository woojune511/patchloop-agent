"""Provider-free selected-test replay over saved public SQLFluff workspaces."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from patchloop.artifacts import ArtifactStore
from patchloop.deadline import ExecutionDeadline
from patchloop.dev.contracts import DevLimits, PublicTurnDecision, RequestedTool
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import DevToolGateway
from patchloop.repository import WorkspaceManager
from patchloop.runtime import git_commit, repository_root, runtime_content_hash
from patchloop.sandbox.runner import DockerSandbox
from patchloop.task_loader import load_public_task
from patchloop.util import canonical_json, sha256_bytes

TASK = "swebench-lite-dev-sqlfluff-sqlfluff-1625"
TARGET = "test/cli/commands_test.py::test__cli__command_directed"


def replay(root: Path, *, panel: Path, live: Path, base: Path) -> dict:
    if root.exists() or root.resolve().is_relative_to(repository_root()):
        raise ValueError("use a fresh external evidence root")
    task_root = repository_root() / "tasks/dev-train" / TASK
    public = load_public_task(task_root / "public.yaml")
    environment = yaml.safe_load((task_root / "environment.yaml").read_text())
    sandbox = DockerSandbox(environment["evaluator_image"])
    assert sandbox.image_identity() == environment["image_digest"], "existing image required"
    batch_bytes = panel.read_bytes()
    batch = json.loads(batch_bytes)
    sources = [("base", base, sha256_bytes(b""), "PASS")]
    for label, status in (("1625A1", "FAIL"), ("1625B1", "PASS")):
        row = next(row for row in batch["rows"] if row["label"] == label)
        run = row["result"]["runs"][0]
        sources.append((label, live / label / "workspaces" / run["run_id"] / "repo",
                        run["artifact_hashes"]["submitted_patch"], status))
    root.mkdir(parents=True)
    store = ArtifactStore(root)
    journal = DevJournal(root, "run_dev_selectedtestsreplay")
    journal.append("replay_prepared", {
        "question": "Can the registered selected-test tool expose the saved public CLI regression?",
        "head": git_commit(), "runtime_hash": runtime_content_hash(),
        "driver_hash": sha256_bytes(Path(__file__).read_bytes()),
        "public_spec_hash": sha256_bytes((task_root / "public.yaml").read_bytes()),
        "source_panel_hash": sha256_bytes(batch_bytes),
        "target": TARGET, "expected": {label: status for label, _, _, status in sources},
        "provider_calls": 0, "new_hidden_evaluations": 0,
        "scope": "operator-selected public test; no autonomous selection claim",
    })
    outcomes = []
    for label, workspace, expected_hash, expected_status in sources:
        before = WorkspaceManager.diff_summary(workspace)
        assert before.patch_hash == expected_hash and not before.untracked_files
        child = DevJournal(root / label, "run_dev_selectedtests")
        gateway = DevToolGateway(
            workspace=workspace, public_task=public, sandbox=sandbox, journal=child,
            limits=DevLimits(), deadline=ExecutionDeadline.from_remaining(120),
        )
        call = RequestedTool(
            name="run_tests", action_id="public-cli",
            arguments={"suite_id": "public-pytest", "targets": [TARGET]},
            turn_decision=PublicTurnDecision(
                mode="verify", basis="Check an existing public caller.",
            ),
        )
        journal.append("replay_started", {"label": label, "submitted_patch_hash": expected_hash})
        result = gateway.execute(call)
        receipt = store.put_json(result.model_dump(mode="json"))
        journal.append("replay_finished", {
            "label": label, "receipt": receipt.model_dump(mode="json"),
        })
        assert result.status == "succeeded", result.message
        assert not any(result.output[key] for key in (
            "timed_out", "truncated", "deadline_exhausted", "cleanup_failed",
        )), "execution uncertainty; stop"
        assert WorkspaceManager.diff_summary(workspace).patch_hash == expected_hash
        assert result.output["test_status"] == expected_status
        assert not gateway.checks_by_diff and gateway.remaining_visible_check_ids()
        previous_bytes = child.path.read_bytes()
        assert gateway.execute(call).replayed and child.path.read_bytes() == previous_bytes
        outcome = {
            "label": label, "submitted_patch_hash": expected_hash,
            "test_status": result.output["test_status"], "exit_code": result.output["exit_code"],
            "receipt_hash": receipt.content_hash, "required_check_credit": False,
            "child_journal_head": child.events()[-1]["event_hash"],
            "durable_result_replayed_without_execution": True,
        }
        outcomes.append(outcome)
        print(json.dumps(outcome), flush=True)
    result = {"rows": outcomes, "provider_calls": 0, "new_hidden_evaluations": 0,
              "official": False, "claim_eligible": False, "autonomous_selection": "NOT_RUN"}
    store.write_text_immutable(root / "result.json", canonical_json(result) + "\n")
    journal.append("replay_completed", {"result": store.put_json(result).model_dump(mode="json")})
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--live", type=Path, required=True)
    parser.add_argument("--base", type=Path, required=True)
    args = parser.parse_args()
    replay(args.output, panel=args.panel, live=args.live, base=args.base)
