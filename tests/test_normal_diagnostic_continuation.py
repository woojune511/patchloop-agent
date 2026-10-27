"""Canonical diagnostic codes survive wording changes through normal completion."""

from __future__ import annotations

import json
import socket

import pytest
from test_dev_completion_v27 import _check
from test_dev_probe_cases import TEXT, ExecutingProbe
from test_dev_segments import assert_submitted, configured, records
from test_dev_tools import read_calls
from test_finish_reproduction import finish_call
from test_first_repair_integration import edit
from test_probe_purpose import probe

from patchloop.dev import probe_invocation, runner, segments
from patchloop.dev.contracts import DevModelTurn, RequestedTool
from patchloop.util import canonical_json, sha256_bytes

PATH = "mini_data_utils/csvlite.py"
OLD = "F0010: Unable to load file"
NEW = "F0010: Failed to import module project"
MARKER = "DIAGNOSTIC_PHASE = 'candidate'"


def original_probe(task):
    # Trusted fixture adapter changes wording with the first candidate while the
    # public CSV failure remains. Only host code rules determine the observation.
    source = (
        "import mini_data_utils.csvlite as module\n"
        "original = module.parse_rows\n"
        "def diagnostic(text):\n"
        "    rows = original(text)\n"
        "    if len(rows) > 2:\n"
        f"        print({NEW!r} if hasattr(module, 'DIAGNOSTIC_PHASE') else {OLD!r})\n"
        "    return rows\n"
        "module.parse_rows = diagnostic\n"
        "target = observed_target()\n"
        f"target({TEXT!r})\n"
        "target('h,v\\na,b\\n')\n"
    )
    call = probe(task, "canonical-original", source=source)
    call.arguments["purpose"].update({
        "reported_failure_json": canonical_json({"bug": True, "control": False}),
        "expected_json": canonical_json({"bug": False, "control": False}),
        "diagnostic_rules": [
            {"field": "bug", "call_id": "call-1", "code": "F0010"},
            {"field": "control", "call_id": "call-2", "code": "F0010"},
        ],
    })
    assert "record_observation" not in source
    return call


class ReviseAfterCurrentFailure:
    def __init__(self, task):
        repair = edit()
        for field in ("old_text", "new_text"):
            repair.arguments[field] = repair.arguments[field].replace(
                "import csv", "import csv\n" + MARKER, 1,
            )
        self.steps = iter([
            read_calls()[1], original_probe(task),
            RequestedTool(name="replace_text", action_id="wording-only-candidate", arguments={
                "path": PATH, "old_text": "import csv", "new_text": "import csv\n" + MARKER,
                "occurrence": 1,
                "hypothesis": "This fixture candidate changes wording but preserves F0010.",
                "expected_behavior": "The same captured code must remain a public failure.",
            }),
            repair, _check("existing-unit-tests", "final-public-check"),
            finish_call("normal-finish"),
        ])

    def next_turn(self, context, tools):
        state = json.loads(context)
        call = next(self.steps)
        offered = {tool["name"] for tool in tools}
        assert call.name in offered
        if call.action_id == "mutation-1":
            assert "finish_task" not in offered
            assert state["repair_stage"]["original_observations"][-1]["comparison"] == (
                "mismatched")
        return DevModelTurn(tool_calls=[call])


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("normal diagnostic continuation must remain offline")

    monkeypatch.setattr(socket.socket, "connect", forbidden)


@pytest.mark.parametrize("force_token_handoff", [False, True])
def test_changed_failure_text_reaches_next_request_then_repair_checks_and_normal_finish(
    tmp_path, monkeypatch, smoke_package, force_token_handoff,
):
    backend = ExecutingProbe()
    request, inputs, counted, views = configured(
        monkeypatch, tmp_path, script=ReviseAfterCurrentFailure(smoke_package.public),
        boundary_policy="size-only-v1" if force_token_handoff else "result-or-size-v1",
    )
    monkeypatch.setattr(runner, "DockerProbeSandbox", lambda: backend)
    request = request.model_copy(update={"enable_probes": True})
    original_limits = request.limits.model_dump()
    if force_token_handoff:
        count = runner.OpenAIResponsesAdapter.count_input_tokens_v2
        forced = False

        def count_with_one_boundary(self, payload, **options):
            nonlocal forced
            tokens = count(self, payload, **options)
            if len(inputs) == 3 and not forced:
                forced = True
                return 60_001
            return tokens

        monkeypatch.setattr(runner.OpenAIResponsesAdapter, "count_input_tokens_v2",
                            count_with_one_boundary)
    result = runner.run_dev(request)["runs"][0]
    assert_submitted(result)
    assert result["accepted_mutations"] == 2
    assert result["call_counts"]["model"] == len(inputs) == 6
    assert len(counted) == 6 + force_token_handoff
    assert inputs == (counted[:3] + counted[4:] if force_token_handoff else counted)
    assert request.limits.model_dump() == original_limits
    assert backend.calls == 3 and backend.sources[0] == backend.sources[1] == backend.sources[2]

    journal, store = records(request)
    events = journal.events()
    results = [event["payload"]["result"] for event in events
               if event["event_type"] == "action_finished"]
    originals = [row for row in results if row["tool"] == "run_probe"]
    assert len(originals) == 3
    evidence = [row["output"]["reproduction"] for row in originals]
    assert [row["comparison"] for row in evidence] == ["mismatched", "mismatched", "matched"]
    assert [row["declared_failure_comparison"] for row in evidence] == [
        "matched", "matched", "mismatched"]
    assert evidence[0]["binding"] == evidence[1]["binding"] == evidence[2]["binding"]
    assert evidence[0]["binding"]["definition"]["observation_channel"] == probe_invocation.CHANNEL
    for row in evidence:
        assert row["judgment"]["policy"] == "captured-diagnostic-v2"
        assert row["judgment"]["status"] == "computed" and row["judgment"]["source"] == "host"
        assert row["observed_json"] == row["judgment"]["host_json"]
        assert all(call["capture"]["status"] == "complete"
                   for call in row["call_observation"]["calls"])
    first_capture = evidence[0]["call_observation"]["calls"][0]["capture"]["stdout"]
    changed_capture = evidence[1]["call_observation"]["calls"][0]["capture"]["stdout"]
    assert OLD in first_capture and NEW in changed_capture and OLD not in changed_capture
    assert json.loads(evidence[1]["observed_json"]) == {"bug": True, "control": False}
    assert json.loads(evidence[2]["observed_json"]) == {"bug": False, "control": False}

    first_edit = next(row for row in results if row["action_id"] == "wording-only-candidate")
    failed_request = views[3]
    assert failed_request["current_diff"]["patch_hash"] == first_edit["workspace_diff_hash"]
    delivered = failed_request["repair_stage"]["original_observations"][-1]
    assert delivered["action_id"] == originals[1]["action_id"]
    assert delivered["diff_hash"] == first_edit["workspace_diff_hash"]
    assert delivered["observed_json"] == evidence[1]["observed_json"]
    assert NEW in delivered["call_observation"]["calls"][0]["capture"]["stdout"]
    assert "finish_task" not in failed_request["available_tool_names"]
    delivered_edit = next(row for row in failed_request["latest_tool_results"]
                          if row["action_id"] == "wording-only-candidate")
    source = delivered_edit["output"]["mutation_evidence"]
    assert source["path"] == PATH and MARKER in source["content"].splitlines()
    assert source["file_hash"] == first_edit["output"]["mutation_evidence"]["file_hash"]
    assert source["source_diff_hash"] == first_edit["workspace_diff_hash"]
    assert any("for physical_line in text.splitlines():" in span.get("content", "")
               for span in delivered_edit["output"]["revalidated_spans"])
    if force_token_handoff:
        assert failed_request["segment_handoff"]["reason"] == "input_tokens"

    finished = next(row for row in results if row["action_id"] == "normal-finish")
    checked = next(row for row in results if row["action_id"] == "final-public-check")
    assert finished["status"] == "succeeded"
    assert finished["output"]["delivery_state"] == "cases_verified_delivery"
    assert finished["output"]["submission_verification"]["status"] == "cases_verified"
    assert checked["output"]["passed"] is True
    assert checked["workspace_diff_hash"] == originals[-1]["workspace_diff_hash"] == (
        finished["output"]["patch_hash"])
    assert not any(event["event_type"] == "protocol_correction" for event in events)
    assert not any(row.get("error_code") for row in results)
    workspace = request.state_root / "workspaces" / journal.run_id / "repo"
    current_hash = sha256_bytes((workspace / PATH).read_bytes())
    assert current_hash != first_edit["output"]["mutation_evidence"]["file_hash"]
    for event in events:
        if event["event_type"] == "turn_started":
            runner._load_active_model_input(event["payload"], store, context_policy=segments.POLICY)
