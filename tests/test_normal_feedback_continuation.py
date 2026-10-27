"""Normal runner handoffs retain current public failures and delivered edit source."""

from __future__ import annotations

import json
import socket

import pytest
from test_dev_completion_v27 import _check
from test_dev_segments import configured, records
from test_dev_tools import read_calls
from test_first_repair_integration import edit

from patchloop.dev import runner, segments
from patchloop.dev.contracts import DevModelTurn, RequestedTool
from patchloop.dev.native_sources import PUBLIC_EVIDENCE_KIND, _SourceIndex
from patchloop.sandbox.runner import SandboxResult
from patchloop.util import sha256_bytes

PATH = "mini_data_utils/csvlite.py"
LATEST = "AssertionError: CURRENT_NORMAL_PUBLIC_REGRESSION"
UPDATED_LINE = "import csv  # current repair source"
UPDATED_LINE_NUMBER = 3


class FailedRecheckSandbox:
    backend = "local"
    supports_execution_deadline = True

    def __init__(self):
        self.executions = []

    def run_check(self, workspace, check, **options):
        self.executions.append({"check_id": check.id, **options})
        message = ("ValueError: PREVIOUS_NORMAL_PUBLIC_FAILURE"
                   if len(self.executions) == 1 else LATEST)
        stderr = ("Traceback (most recent call last):\n"
                  f'  File "{workspace / PATH}", line {UPDATED_LINE_NUMBER}, in parse_rows\n'
                  f"    {UPDATED_LINE}\n{message}\n")
        return SandboxResult(command=check.command, exit_code=1, stdout="public regression result",
            stderr=stderr, duration_ms=1, timed_out=False, truncated=False,
            original_output_bytes=len(stderr.encode()) + 24,
            execution_policy={"cleanup_status": "confirmed"})


class RepairThenStop:
    def __init__(self):
        self.steps = iter([
            read_calls()[1], edit(), _check("existing-unit-tests", "first-public-failure"),
            RequestedTool(name="replace_text", action_id="repair-current-failure", arguments={
                "path": PATH, "old_text": "import csv", "new_text": UPDATED_LINE,
                "occurrence": 1, "hypothesis": "Test current public feedback on a new diff.",
                "expected_behavior": "The mock registered check observes this candidate.",
            }),
            RequestedTool(name="stop_task", action_id="stop-with-current-failure", arguments={
                "reason_code": "insufficient_public_evidence",
                "summary": "The current public regression remains unresolved.",
            }),
        ])

    def next_turn(self, context, tools):
        del context
        call = next(self.steps)
        assert call.name in {tool["name"] for tool in tools}
        return DevModelTurn(tool_calls=[call])


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("normal feedback validation must remain offline")

    monkeypatch.setattr(socket.socket, "connect", forbidden)


@pytest.mark.parametrize("force_token_handoff", [False, True])
def test_actual_request_keeps_latest_recheck_parent_and_updated_source_after_handoff(
    tmp_path, monkeypatch, force_token_handoff,
):
    request, inputs, counted, views = configured(
        monkeypatch, tmp_path,
        boundary_policy="size-only-v1" if force_token_handoff else "result-or-size-v1",
        script=RepairThenStop(),
    )
    if force_token_handoff:
        count = runner.OpenAIResponsesAdapter.count_input_tokens_v2
        forced = False

        def count_with_one_boundary(self, payload, **options):
            nonlocal forced
            tokens = count(self, payload, **options)
            if len(inputs) == 4 and not forced:
                forced = True
                return 60_001
            return tokens

        monkeypatch.setattr(runner.OpenAIResponsesAdapter, "count_input_tokens_v2",
                            count_with_one_boundary)
    sandbox = FailedRecheckSandbox()
    monkeypatch.setattr(runner, "_live_sandbox_preflight", lambda *args, **kwargs: sandbox)
    request = request.model_copy(update={"repair_recheck": True})
    result = runner.run_dev(request)["runs"][0]
    assert result["terminal"] == "AGENT_STOPPED" and result["accepted_mutations"] == 2
    assert len(sandbox.executions) == 2 and len(inputs) == 5
    assert len(counted) == 5 + force_token_handoff
    assert inputs == [*counted[:4], counted[-1]]
    journal, store = records(request)
    events = journal.events()
    recheck = next(event["payload"] for event in events
                   if event["event_type"] == "repair_recheck_finished")
    result_by_id = {event["payload"]["result"]["action_id"]: event["payload"]["result"]
                    for event in events if event["event_type"] == "action_finished"}
    actual_check = result_by_id[recheck["action_id"]]
    repair = result_by_id["repair-current-failure"]
    assert actual_check["output"]["passed"] is False
    assert actual_check["workspace_diff_hash"] == repair["output"]["worktree_diff_hash"]
    for index in range(4, len(inputs)):
        view = views[index]
        assert view["workflow_gate"] == "needs_visible_checks"
        assert view["current_diff"]["patch_hash"] == actual_check["workspace_diff_hash"]
        assert view["last_successful_mutation"]["action_id"] == "repair-current-failure"
        latest = next(check for check in view["recent_checks"]
                      if check["action_id"] == recheck["action_id"])
        assert latest["diff_hash"] == actual_check["workspace_diff_hash"]
        assert latest["evidence_currency"] == "current" and not latest["passed"]
        assert latest["stderr"] == actual_check["output"]["stderr"]
        assert LATEST in latest["stderr"]
        assert view["current_public_failure"]["diff_hash"] == actual_check["workspace_diff_hash"]
        assert view["visible_check_status"][0]["status"] == "FAIL"
        # This small host receipt links failure -> repair -> new failing check.
        link = view["repair_recheck"]["last_result"]
        assert link["parent_action_id"] == "repair-current-failure"
        assert link["previous_check_action_id"] == "first-public-failure"
        assert link["action_id"] == recheck["action_id"]
        assert link["candidate_diff_hash"] == actual_check["workspace_diff_hash"]
        source = _SourceIndex(inputs[index], archive_kind=PUBLIC_EVIDENCE_KIND)
        hashes = [key for key in source.observed if key[0] == PATH]
        assert any(rows[UPDATED_LINE_NUMBER][0] == UPDATED_LINE
                   for key, rows in source.observed.items()
                   if key in hashes and UPDATED_LINE_NUMBER in rows)
        assert not any(item.get("call_id") == recheck["action_id"] for item in inputs[index])
        assert not any(item.get("type") == "reasoning" for item in inputs[index])
        assert "PRIVATE_SENTINEL" not in json.dumps(inputs[index])
    # Actual request source is bound to the current file, not a stale diff or source hash.
    final_source = _SourceIndex(inputs[-1], archive_kind=PUBLIC_EVIDENCE_KIND)
    workspace = request.state_root / "workspaces" / journal.run_id / "repo"
    current_hash = sha256_bytes((workspace / PATH).read_bytes())
    assert final_source.observed[(PATH, current_hash)][UPDATED_LINE_NUMBER][0] == UPDATED_LINE
    binding, handoff = segments.active(
        journal, store, committed_only=True, boundary_policy=request.segment_boundary_policy)
    assert binding["segment_id"] == views[-1]["segment_handoff"]["segment_id"]
    handoff_check = next(check for check in handoff["state"]["recent_checks"]
                         if check["action_id"] == recheck["action_id"])
    assert handoff_check["stderr"] == actual_check["output"]["stderr"]
    assert handoff["state"]["repair_recheck"]["last_result"]["parent_action_id"] == (
        "repair-current-failure")
    handoff_sources = _SourceIndex(handoff["base"], archive_kind=PUBLIC_EVIDENCE_KIND)
    assert handoff_sources.observed[(PATH, current_hash)][UPDATED_LINE_NUMBER][0] == UPDATED_LINE
    if force_token_handoff:
        assert views[-1]["segment_handoff"]["reason"] == "input_tokens"
        assert result["call_counts"]["model"] == 5
    for event in events:
        if event["event_type"] == "turn_started":
            runner._load_active_model_input(event["payload"], store, context_policy=segments.POLICY)
