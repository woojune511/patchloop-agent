"""Opt-in collector validation: one real Docker check and one real Docker probe.

Requires separate approval, PATCHLOOP_TEST_REAL_EXECUTION=1 and a new external
pytest --basetemp. Never starts Docker or acquires images; stops on first failure.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
import uuid

import pytest

from patchloop.contracts import (
    IssueSpec,
    PublicTask,
    RegisteredCheck,
    RepositorySpec,
    TaskConstraints,
)
from patchloop.deadline import ExecutionDeadline
from patchloop.dev.contracts import (
    DevLimits,
    PublicTurnDecision,
    RequestedTool,
    dev_tool_surface_hash,
)
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import DevToolGateway
from patchloop.runtime import git_commit, repository_root, runtime_content_hash
from patchloop.sandbox.probes import PROBE_IMAGE, PROBE_IMAGE_DIGEST, DockerProbeSandbox
from patchloop.sandbox.runner import DockerSandbox
from patchloop.util import canonical_json, sha256_bytes, sha256_json

pytestmark = pytest.mark.skipif(
    os.environ.get("PATCHLOOP_TEST_REAL_EXECUTION") != "1",
    reason="real check/probe requires explicit PATCHLOOP_TEST_REAL_EXECUTION=1",
)

SOURCE = (
    b"def choose(flag):\n"
    b"    if flag:\n"
    b"        return 7\n"
    b"    raise ValueError('PUBLIC_EDGE_SENTINEL')\n"
    b"# comment is not a line-entry obligation\n"
)


def _git(root, *arguments):
    return subprocess.run(
        ["git", "-C", str(root), *arguments], capture_output=True,
        check=True, timeout=10, text=True,
    ).stdout.strip()


def _receipt(path, payload):
    # A reused evidence path must never silently replace an earlier attempt.
    with path.open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2)


def _no_container(name):
    inspected = subprocess.run(
        [DockerSandbox.cli_path(), "container", "inspect", name],
        capture_output=True, check=False, timeout=10,
    )
    return bool(
        inspected.returncode and name.encode() in inspected.stderr
        and any(token in inspected.stderr for token in (b"No such container", b"No such object"))
    )


def test_real_check_probe_line_feedback_and_completed_replay(tmp_path, monkeypatch):
    evidence = tmp_path.resolve()
    assert not evidence.is_relative_to(repository_root().resolve()), "use an external --basetemp"
    assert DockerSandbox.available(), "Docker must already be running"
    check_backend, probe_backend = DockerSandbox(PROBE_IMAGE), DockerProbeSandbox()
    identity = probe_backend.preflight()  # Inspection only; no pull/build fallback.
    _receipt(evidence / "preflight.json", {
        "official": False, "provider_calls": 0, "input_count_calls": 0,
        "runtime_hash": runtime_content_hash(), "tool_hash": dev_tool_surface_hash(),
        "git_commit": git_commit(), **identity,
    })

    workspace = evidence / "public-repo"
    workspace.mkdir()
    _git(workspace, "init")
    _git(workspace, "config", "core.autocrlf", "false")
    (workspace / "sample.py").write_bytes(b"# public baseline\n")
    _git(workspace, "add", "--", "sample.py")
    _git(
        workspace, "-c", "user.name=PatchLoop Collector Test",
        "-c", "user.email=collector-test@example.invalid", "commit", "-m", "Public fixture",
    )
    revision = _git(workspace, "rev-parse", "HEAD")
    (workspace / "sample.py").write_bytes(SOURCE)
    public = PublicTask(
        task_id="public-line-entry-fixture", split="smoke",
        repository=RepositorySpec(url=str(workspace), base_commit=revision),
        issue=IssueSpec(
            title="Public line-entry fixture", description="Observe both public paths.",
        ),
        constraints=TaskConstraints(
            allowed_paths=["sample.py"], max_changed_files=1, max_diff_lines=50,
        ),
        visible_checks=[RegisteredCheck(
            id="public", command=["python", "-c",
                "import sample; assert sample.choose(True) == 7; print('PUBLIC_PASS')"],
            timeout_seconds=20,
        )],
    )
    journal = DevJournal(evidence / "state", "run_dev_linevalidation_" + uuid.uuid4().hex[:16])

    def gateway():
        return DevToolGateway(
            workspace=workspace, public_task=public, sandbox=check_backend, journal=journal,
            limits=DevLimits(), probe_sandbox=probe_backend,
            deadline=ExecutionDeadline.from_remaining(90),
        )

    active = gateway()
    diff_hash = active.current_diff_hash
    file_hash = sha256_bytes(SOURCE)
    launches = {"run_check": 0, "run_probe": 0}

    def counted(name, implementation):
        def run(*args, **kwargs):
            assert launches[name] == 0, "a second execution requires separate approval"
            launches[name] += 1
            return implementation(*args, **kwargs)
        return run

    monkeypatch.setattr(check_backend, "run_check", counted("run_check", check_backend.run_check))
    monkeypatch.setattr(probe_backend, "run_probe", counted("run_probe", probe_backend.run_probe))
    calls = [
        RequestedTool(
            name="run_check", action_id="public-check", arguments={"check_id": "public"},
            turn_decision=PublicTurnDecision(
                mode="verify", basis="Observe the public return path.",
            ),
        ),
        RequestedTool(
            name="run_probe", action_id="public-probe",
            arguments={
                "question": "Does the alternative public path enter the changed raising line?",
                "python_source": "import sample\nsample.choose(False)\n",
            },
            turn_decision=PublicTurnDecision(mode="verify", basis="Observe the public error path."),
        ),
    ]
    results = []
    for call in calls:
        execution_identity = {"run_id": journal.run_id, "action_id": call.action_id}
        name = (
            probe_backend.container_name(execution_identity) if call.name == "run_probe"
            else "patchloop-" + sha256_json(execution_identity)[7:31]
        )
        _receipt(evidence / f"{call.action_id}-attempt.json", {
            "official": False, "execution_identity": execution_identity, "container_name": name,
            "input": call.model_dump(mode="json"), "diff_hash": diff_hash, "file_hash": file_hash,
        })
        started = time.monotonic()
        result = active.execute(call)
        absent = _no_container(name)
        _receipt(evidence / f"{call.action_id}-result.json", {
            "official": False, "provider_calls": 0, "input_count_calls": 0,
            "elapsed_seconds": time.monotonic() - started, "container_absent": absent,
            "journal_path": str(journal.path), "result": result.model_dump(mode="json"),
        })
        assert absent and not result.output.get("cleanup_failed"), "stop: cleanup uncertain"
        assert result.status == "succeeded", result.message
        output = result.output
        assert output["execution_policy"]["cleanup_status"] == "confirmed"
        assert output["execution_policy_hash"] == sha256_json(output["execution_policy"])
        assert output["diff_hash"] == result.workspace_diff_hash == diff_hash
        assert active.current_diff_hash == diff_hash
        assert (workspace / "sample.py").read_bytes() == SOURCE
        assert _git(workspace, "ls-files", "--others", "--exclude-standard") == ""
        observed = output["public_execution"]
        assert observed["status"] == "collected" and observed["diagnostic_only"]
        assert observed["diff_hash"] == diff_hash
        targets = active._execution_targets(execution_identity)
        assert observed["request_hash"] == targets["request_hash"]
        assert len(canonical_json(observed).encode()) <= 12_000
        row, = observed["files"]
        assert row["path"] == "sample.py" and row["file_hash"] == file_hash
        assert row["changed_ranges"] == [[1, 5]] and row["no_line_event_ranges"] == [[5, 5]]
        assert "PATCHLOOP-LINES" not in output["stdout"] + output["stderr"]
        assert "PUBLIC_EDGE_SENTINEL" not in canonical_json(observed)
        if call.name == "run_check":
            assert output["passed"] and output["stdout"].splitlines() == ["PUBLIC_PASS"]
            assert output["stderr"] == ""
            assert row["executed_changed_ranges"] == [[1, 3]]
            assert row["not_observed_changed_ranges"] == [[4, 4]]
        else:
            assert output["status"] == "failed" and output["exit_code"] == 1
            assert "ValueError: PUBLIC_EDGE_SENTINEL" in output["stderr"]
            assert output["image_digest"] == PROBE_IMAGE_DIGEST
            assert output["profile_hash"] == identity["profile_hash"]
            assert output["snapshot_hash"] == sha256_json([
                {"path": "sample.py", "content_hash": file_hash},
            ])
            assert row["executed_changed_ranges"] == [[1, 2], [4, 4]]
            assert row["not_observed_changed_ranges"] == [[3, 3]]
        assert active.spans == {}  # Execution feedback grants no source evidence.
        assert active.visible_checks_pass()  # A failed diagnostic cannot invalidate public PASS.
        results.append(result)

    summary = active.public_execution_summary(diff_hash=diff_hash)
    assert summary["files"][0]["executed_changed_ranges"] == [[1, 4]]
    assert summary["files"][0]["not_observed_changed_ranges"] == []
    assert summary["recent_action_ids"] == [call.action_id for call in calls]
    before_replay = journal.path.read_bytes()
    restored = gateway()
    for call, result in zip(calls, results, strict=True):
        replayed = restored.execute(call)
        assert replayed.replayed and replayed.output == result.output
    assert restored.public_execution_summary(diff_hash=diff_hash) == summary
    assert journal.path.read_bytes() == before_replay
    assert launches == {"run_check": 1, "run_probe": 1}
    _receipt(evidence / "validation.json", {
        "official": False, "claim_eligible": False, "provider_calls": 0, "input_count_calls": 0,
        "run_id": journal.run_id, "launches": launches, "completed_replay_unchanged": True,
        "diff_hash": diff_hash, "file_hash": file_hash, "public_execution_summary": summary,
        "scope": "synthetic public fixture; not a live agent or private evaluator run",
    })
