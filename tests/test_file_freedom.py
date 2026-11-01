"""Broader reads and atomic all-match edits keep source, scope and recovery contracts."""

import os

import pytest
from typer.testing import CliRunner

from patchloop.cli import app
from patchloop.dev.contracts import DevLimits, PublicTurnDecision, RequestedTool
from patchloop.dev.native_sources import project_mutation_result
from patchloop.dev.tools import DevToolGateway
from patchloop.git_execution import run_git
from patchloop.runtime import repository_root

PATH = "mini_data_utils/csvlite.py"


def read(gateway, action="read", start=None, end=None):
    return gateway.execute(RequestedTool(
        name="read_file", action_id=action,
        arguments={"path": PATH, "start_line": start, "end_line": end},
        turn_decision=PublicTurnDecision(mode="inspect", basis="Observe the exact edit targets.",
                                        evidence_goal="Locate all matching source anchors."),
    ))


def mutation(action="edit", old="physical_line", new="record_line"):
    return RequestedTool(name="replace_text", action_id=action, arguments={
        "path": PATH, "old_text": old, "new_text": new, "occurrence": "all",
        "hypothesis": "Rename a local variable consistently at its definition and use.",
        "expected_behavior": "CSV parsing behavior remains unchanged.",
    })


def restart(gateway):
    return DevToolGateway(workspace=gateway.workspace, public_task=gateway.public_task,
                          sandbox=gateway.sandbox, journal=gateway.journal, limits=gateway.limits)


def test_all_matches_are_one_atomic_edit_and_replay_does_not_repeat(gateway_factory):
    gateway, _, workspace = gateway_factory()
    before = (workspace / PATH).read_bytes()
    assert read(gateway).status == "succeeded"
    call = mutation(new="physical_line_value")  # New text itself includes the old anchor.
    result = gateway.execute(call)
    assert result.status == "succeeded", result.message
    assert (workspace / PATH).read_bytes() == before.replace(
        b"physical_line", b"physical_line_value")
    assert result.output["mutation"]["replacement_count"] == 2
    assert gateway.accepted_mutations == 1
    recovered = restart(gateway)
    assert recovered.execute(call).replayed is True
    assert recovered.accepted_mutations == 1
    # Multi-match native delivery retains exact bodies rather than misusing a
    # single-offset source alias. The durable output itself stays unchanged.
    admission = next(e["payload"] for e in gateway.journal.events()
                     if e["event_type"] == "action_started" and e["payload"]["action_id"] == "edit")
    projected = project_mutation_result(result.model_dump(mode="json"),
                                        history=[{"type": "unused"}], admission=admission)
    assert projected["output"]["mutation_evidence"] == result.output["mutation_evidence"]


def test_transaction_preview_preserves_racy_index_timestamp(gateway_factory):
    from patchloop.dev.file_transaction import FileChange, preview_transaction
    from patchloop.repository import WorkspaceManager

    gateway, _, workspace = gateway_factory()
    target = workspace / PATH
    original = target.read_bytes()
    timestamp = target.stat().st_mtime_ns
    # Keep the cached size/mtime but change bytes; the index timestamp must make
    # Git re-read this racy entry rather than trust its pre-edit cached blob.
    before = original.replace(b"physical_line", b"physical_linx")
    target.write_bytes(before)
    os.utime(target, ns=(timestamp, timestamp))
    index = workspace / ".git/index"
    os.utime(index, ns=(timestamp, timestamp))
    baseline = WorkspaceManager.diff_summary(workspace)
    assert baseline.patch
    os.utime(index, ns=(timestamp, timestamp))
    after = before.replace(b"physical_linx", b"physical_liny")
    expected, _ = preview_transaction(
        workspace, [FileChange(PATH, before, after)], baseline_diff_hash=baseline.patch_hash,
    )
    assert target.read_bytes() == before
    target.write_bytes(after)
    assert WorkspaceManager.diff_summary(workspace).patch_hash == expected.patch_hash


def test_all_matches_require_each_anchor_observed_and_current(gateway_factory):
    gateway, _, workspace = gateway_factory()
    text = (workspace / PATH).read_text(encoding="utf-8")
    first_line = text[:text.index("physical_line")].count("\n") + 1
    read(gateway, start=first_line, end=first_line)
    rejected = gateway.execute(mutation())
    assert rejected.status == "failed"
    assert "evidence spans" in rejected.message
    assert (workspace / PATH).read_text(encoding="utf-8") == text
    assert gateway.accepted_mutations == 0


def test_all_matches_scope_failure_restores_entire_file(gateway_factory):
    gateway, _, workspace = gateway_factory()
    before = (workspace / PATH).read_bytes()
    gateway.public_task = gateway.public_task.model_copy(update={
        "constraints": gateway.public_task.constraints.model_copy(update={"max_diff_lines": 1})})
    read(gateway)
    result = gateway.execute(mutation())
    assert result.status == "failed"
    assert "scope" in result.message
    assert (workspace / PATH).read_bytes() == before
    assert gateway.accepted_mutations == 0


def test_all_match_expansion_uses_utf8_byte_bound_before_writing(gateway_factory):
    gateway, _, workspace = gateway_factory()
    before = (workspace / PATH).read_bytes()
    # 52 spaces times 20k three-byte characters exceeds 2 MB, while the
    # character count alone would incorrectly admit it.
    assert read(gateway).status == "succeeded"
    result = gateway.execute(mutation(old=" ", new="가" * 20_000))
    assert result.status == "failed" and "2 MB" in result.message
    assert (workspace / PATH).read_bytes() == before
    assert gateway.accepted_mutations == 0


@pytest.mark.parametrize("new", ["", "physical_line_value", "record\nline"])
def test_all_matches_crash_reconciles_using_admitted_offsets(gateway_factory, monkeypatch, new):
    gateway, _, workspace = gateway_factory()
    target = workspace / PATH
    # Preserve CRLF as well as positions in normalized source.
    before = target.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
    target.write_bytes(before)
    # CRLF is the fixture baseline, not an extra whole-file mutation that can
    # exceed the task's diff limit on a host whose checkout originally used LF.
    run_git(workspace, "config", "core.autocrlf", "false")
    run_git(workspace, "add", "--", PATH)
    run_git(workspace, "-c", "user.name=PatchLoop Test",
            "-c", "user.email=patchloop@example.invalid", "commit", "--allow-empty",
            "-qm", "CRLF recovery fixture baseline")
    assert gateway.current_diff.patch == ""
    assert read(gateway).status == "succeeded"
    call = mutation(new=new)

    class Crash(BaseException):
        pass

    def crash(**kwargs):
        raise Crash

    monkeypatch.setattr(gateway, "_mutation_result_output", crash)
    with pytest.raises(Crash):
        gateway.execute(call)
    candidate = target.read_bytes()
    assert candidate == before.replace(b"physical_line", new.replace("\n", "\r\n").encode())
    resumed = restart(gateway)
    result = resumed.execute(call)
    assert result.status == "succeeded", result.message
    assert result.output["recovered_after_crash"] is True
    assert target.read_bytes() == candidate
    assert resumed.accepted_mutations == 1


def test_default_edit_budget_exceeds_four_and_explicit_limit_is_preserved(gateway_factory):
    assert DevLimits().max_accepted_mutations == 12
    explicit = DevLimits(max_accepted_mutations=3)
    assert DevLimits.model_validate_json(explicit.model_dump_json()).max_accepted_mutations == 3
    gateway, _, _ = gateway_factory()
    for number in range(5):
        assert read(gateway, f"read-{number}").status == "succeeded"
        old, new = (("physical_line", "record_line") if number % 2 == 0
                    else ("record_line", "physical_line"))
        result = gateway.execute(mutation(f"edit-{number}", old, new))
        assert result.status == "succeeded", result.message
    assert gateway.accepted_mutations == 5


@pytest.mark.parametrize("requested,expected", [(None, 12), (3, 3), (20, 20)])
def test_cli_exposes_edit_budget_without_changing_other_limits(monkeypatch, requested, expected):
    captured = []
    monkeypatch.setattr("patchloop.dev.runner.run_dev",
                        lambda request: captured.append(request) or {})
    command = ["dev", "--provider", "mock", "--model", "mock", "--task",
               str(repository_root() / "tasks/smoke/csv-quoted-newline/public.yaml")]
    if requested is not None:
        command.extend(["--max-accepted-mutations", str(requested)])
    result = CliRunner().invoke(app, command)
    assert result.exit_code == 0, result.output
    assert captured[0].limits == DevLimits(max_accepted_mutations=expected)
