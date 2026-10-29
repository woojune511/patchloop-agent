"""Edit prerequisites survive actual thin repair requests, correction and recovery."""

from __future__ import annotations

import copy
from types import SimpleNamespace

import httpx
import pytest
from test_dev_mutation_attempt_budget import _state
from test_dev_planning import request as mock_request
from test_dev_probes import FakeProbe
from test_dev_runner import _crash_journal_once, _SimulatedCrash
from test_dev_segments import assert_submitted, configured, records

from patchloop.contracts import PublicTestSuite
from patchloop.dev import repair_context, runner, segments, thin_policy
from patchloop.dev.contracts import DevLimits
from patchloop.dev.conversation import reconstruct_state
from patchloop.dev.mutation_tools import MUTATION_TOOLS


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("edit-availability tests must not dispatch network requests")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbidden)


def _wire_fixture(monkeypatch, tmp_path, *, incomplete_at=()):
    request, inputs, counted, states = configured(
        monkeypatch, tmp_path, incomplete_at=incomplete_at,
    )
    # A registered optional test suite selects the same initial small repair view
    # as the observed failure. The script never runs it or a probe.
    task_dir, package = runner._resolve_task_file(request.task)
    package = package.model_copy(update={"public": package.public.model_copy(update={
        "test_suites": [PublicTestSuite(
            id="optional-tests", command=["python", "-m", "pytest"],
            test_roots=["tests"], timeout_seconds=5,
        )],
    })})
    monkeypatch.setattr(runner, "_resolve_task_file", lambda task: (task_dir, package))
    backend = FakeProbe()
    monkeypatch.setattr(runner, "DockerProbeSandbox", lambda: backend)
    request = request.model_copy(update={
        "agent_policy": "thin", "verification_policy": "public-checks-v1",
        "enable_probes": True,
    })
    adapter = runner.OpenAIResponsesAdapter
    count, dispatch = adapter.count_input_tokens_v2, adapter.execute_request
    counted_payloads, dispatched_payloads = [], []

    def capture_count(self, payload, **kwargs):
        counted_payloads.append(copy.deepcopy(payload))
        return count(self, payload, **kwargs)

    def capture_dispatch(self, payload, **kwargs):
        dispatched_payloads.append(copy.deepcopy(payload))
        return dispatch(self, payload, **kwargs)

    monkeypatch.setattr(adapter, "count_input_tokens_v2", capture_count)
    monkeypatch.setattr(adapter, "execute_request", capture_dispatch)
    return (request, inputs, counted, states, counted_payloads, dispatched_payloads, backend)


def _assert_source_prerequisite(state, tools):
    names = {tool["name"] for tool in tools}
    guidance = state["completion_guidance"]
    assert "replace_text" not in names
    assert guidance["edit_availability"] == {
        "tool": "replace_text", "status": "not_offered", "reason": "needs_current_source",
        "prerequisite": {
            "tools": sorted(names & {"read_file", "search_files"}),
            "scope": "current_allowed_editable_source",
            "effect": "reevaluate_edit_availability_with_remaining_budgets",
        },
    }
    assert guidance["edit_availability"]["prerequisite"]["tools"]
    assert "message" not in guidance and "next_action" not in guidance


@pytest.mark.parametrize("mode", [
    "ordinary", "initial_correction", "fresh_correction", "resume_after_read",
])
def test_count_and_dispatch_keep_edit_card_through_small_repair_path(
    monkeypatch, tmp_path, mode,
):
    request, inputs, counted, states, counts, dispatches, backend = _wire_fixture(
        monkeypatch, tmp_path,
        incomplete_at={"initial_correction": (0,), "fresh_correction": (1,)}.get(mode, ()),
    )
    if mode == "resume_after_read":
        _crash_journal_once(
            monkeypatch, event_type="action_finished", when="after",
            predicate=lambda payload: payload["result"]["tool"] == "read_file",
        )
        with pytest.raises(_SimulatedCrash):
            runner.run_dev(request)
        journal, _ = records(request)
        request = request.model_copy(update={"resume_run_id": journal.run_id})
    result = runner.run_dev(request)["runs"][0]
    assert_submitted(result)
    assert result["accepted_mutations"] == 1
    assert inputs == counted and counts == dispatches
    assert len(inputs) == (5 if mode.endswith("correction") else 4)
    assert backend.calls == 0
    assert inputs[0][0]["content"].startswith(repair_context.system_prompt(states[0]))
    _assert_source_prerequisite(states[0], dispatches[0]["tools"])
    offset = int(mode == "initial_correction")
    if mode == "initial_correction":
        corrected = states[1]
        _assert_source_prerequisite(corrected, dispatches[1]["tools"])
        assert corrected["protocol_correction"]
    elif mode == "fresh_correction":
        corrected = states[2]
        assert corrected["completion_guidance"]["edit_availability"] == (
            states[1]["completion_guidance"]["edit_availability"]
        )
        assert corrected["protocol_correction"]["repair_correction"]["kind"] == "no_action"
        assert corrected["segment_handoff"]["reason"] == "repair_no_action"
        assert not any(item.get("type") == "reasoning" for item in inputs[2])
    after_read = states[1 + offset]
    assert after_read["completion_guidance"]["edit_availability"] == {
        "tool": "replace_text", "status": "offered", "reason": None, "prerequisite": None,
    }
    assert "replace_text" in {tool["name"] for tool in dispatches[1 + offset]["tools"]}
    for state, payload in zip(states, dispatches, strict=True):
        card = state["completion_guidance"]["edit_availability"]
        assert (card["status"] == "offered") == (
            "replace_text" in {tool["name"] for tool in payload["tools"]}
        )
    assert states[-1]["completion_guidance"]["submission_ready"]
    assert states[-1]["visible_check_status"][0]["status"] == "PASS"
    # A successful public check does not remove the current source needed by an
    # offered final repair, even though the latest tool result is no longer a read.
    final = states[-1]
    assert MUTATION_TOOLS.intersection(final["available_tool_names"])
    assert final["current_sources"]
    assert any(group.get("inline_spans") for group in final["current_sources"])
    assert final["completion_stage"]["source_retrieval"]["source_bodies_delivered"]
    assert final["context_projection"]["retained_content_chars"] <= request.retained_source_chars
    journal, _ = records(request)
    actions = [event["payload"]["result"]["tool"] for event in journal.events()
               if event["event_type"] == "action_finished"]
    assert actions.count("read_file") == actions.count("replace_text") == 1
    assert actions[-3:] == ["replace_text", "run_check", "finish_task"]
    before = journal.path.read_bytes()
    dispatch_count = len(dispatches)
    assert runner.run_dev(request.model_copy(update={"resume_run_id": journal.run_id}))[
        "runs"][0] == result
    assert journal.path.read_bytes() == before and len(dispatches) == dispatch_count


def test_thin_card_reaches_real_local_mock_isolated_acceptance(tmp_path):
    request = mock_request(tmp_path, "none").model_copy(update={
        "agent_policy": "thin", "verification_policy": "public-checks-v1",
        "context_policy": segments.POLICY,
    })
    result = runner.run_dev(request)["runs"][0]
    assert result["terminal"] == "EVALUATOR_PASS"
    assert result["evaluator"]["safety_state"] == "NOT_RUN"
    assert result["accepted_mutations"] == 1
    journal, store = records(request)
    states = [reconstruct_state(runner._load_active_model_input(
        event["payload"], store, context_policy=segments.POLICY,
    ), context_policy=segments.POLICY) for event in journal.events()
        if event["event_type"] == "turn_started"]
    assert states[0]["completion_guidance"]["edit_availability"]["reason"] == (
        "needs_current_source"
    )
    assert states[1]["completion_guidance"]["edit_availability"]["status"] == "offered"
    assert states[-1]["completion_guidance"]["submission_ready"]
    assert all("edit_availability" in state["completion_guidance"] for state in states)


@pytest.mark.parametrize("limits,reason", [
    ({"model": 3}, "model_calls_insufficient_for_edit_completion"),
    ({"tools": 3}, "tool_actions_insufficient_for_edit_completion"),
    ({"mutations": 0}, "mutation_limit_reached"),
    ({"untracked": True}, "workspace_scope_invalid"),
])
def test_closed_budget_or_scope_does_not_promise_a_read_unlock(limits, reason):
    gateway, counters = _state(("FAIL", "NOT_RUN"), anchor=False, **limits)
    policy = runner._tool_policy(gateway, counters, DevLimits(max_accepted_mutations=4))
    assert policy.allowed_tools == {"stop_task"}
    snapshot = SimpleNamespace(
        diff=gateway.current_diff, ready_to_submit=gateway.ready_to_submit(),
        visible_check_status=gateway.visible_check_status(),
    )
    state = thin_policy.project_state({
        "completion_guidance": runner._completion_guidance(snapshot, policy),
    }, "thin")
    assert state["completion_guidance"]["edit_availability"] == {
        "tool": "replace_text", "status": "not_offered", "reason": reason,
        "prerequisite": None,
    }
