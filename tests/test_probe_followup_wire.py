"""A public helper observation survives edits and compact delivery without check credit."""

from __future__ import annotations

import copy
import json

import httpx
import pytest
from test_dev_probe_action_replay import QUESTION, probe, restore
from test_dev_probe_cases import REPRODUCER, ExecutingProbe
from test_dev_tools import mutation_call, read_calls

from patchloop.dev import completion_context, diagnosis_context, repair_context, runner, thin_policy
from patchloop.dev import probe_cases as cases
from patchloop.dev.contracts import PublicTurnDecision, RequestedTool
from patchloop.dev.conversation import assemble_model_input, reconstruct_state
from patchloop.dev.model_state import compact_model_state


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("probe follow-up controls must not send network requests")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbidden)


def test_helper_edit_followup_exact_replay_and_restart_do_not_grant_check_credit(
    gateway_factory, smoke_package,
):
    gateway, journal, workspace = gateway_factory()
    backend = gateway.probe_sandbox = ExecutingProbe()
    source = "print('PUBLIC_HELPER_OBSERVATION')\n" + REPRODUCER
    original = gateway.execute(probe("baseline-helper", source=source))
    assert original.status == "succeeded" and original.output["exit_code"] == 1
    assert gateway.execute_batch(read_calls())[-1].status == "succeeded"
    assert gateway.execute(mutation_call(gateway)).status == "succeeded"
    before = journal.path.read_bytes()
    review = gateway.reproduction_review(diff_hash=gateway.current_diff_hash)
    card = review["probe_followup"]
    baseline = card["baseline"]
    assert baseline["action_id"] == original.action_id
    assert baseline["input_hash"] == original.input_hash
    assert baseline["diff_hash"] == original.workspace_diff_hash
    assert baseline["source_hash"] == original.output["source_hash"]
    assert baseline["observation"]["stdout"] == original.output["stdout"]
    assert baseline["observation"]["stdout"].strip() == "PUBLIC_HELPER_OBSERVATION"
    assert "AssertionError" in baseline["observation"]["stderr"]
    assert baseline["observation"]["exit_code"] == 1
    assert card["question"] == QUESTION
    assert card["current_diff_hash"] == gateway.current_diff_hash != baseline["diff_hash"]
    assert card["candidate"] == {"status": "not_run", "observation": None}
    assert card["requirement_coverage"] == "not_assessed"
    assert card["replay"]["reference_valid"] is True
    assert card["replay"]["available"] is False and card["replay"]["arguments"] is None
    assert journal.path.read_bytes() == before and backend.calls == 1

    model_state = json.loads(runner._build_context(
        package=smoke_package, gateway=gateway, journal=journal,
        correction=None, latest_tool_results=[], counters=runner._RunCounters(),
        elapsed_seconds=0, limits=gateway.limits,
    ))
    projected_card = model_state["reproduction_review"]["probe_followup"]
    assert projected_card["baseline"] == baseline
    assert projected_card["replay"]["available"] is True
    assert "run_probe" in model_state["available_tool_names"]
    arguments = projected_card["replay"]["arguments"]
    assert arguments == {"replay_action_id": original.action_id, "question": None,
                         "python_source": None, "purpose": None, "call_path": None}
    assert review["probe_followup"]["replay"]["available"] is False
    assert backend.calls == 1 and journal.path.read_bytes() == before
    replay_call = RequestedTool(
        name="run_probe", action_id="candidate-helper", arguments=arguments,
        turn_decision=PublicTurnDecision(mode="verify", basis="Repeat the observed public helper."),
    )
    replay = gateway.execute(replay_call)
    assert replay.status == "succeeded" and replay.output["exit_code"] == 0
    assert backend.sources == [source, source]
    current_card = gateway.reproduction_review(diff_hash=gateway.current_diff_hash)[
        "probe_followup"]
    assert current_card["baseline"] == baseline
    assert current_card["candidate"]["status"] == "observed"
    candidate = current_card["candidate"]["observation"]
    assert candidate["action_id"] == replay.action_id
    assert candidate["diff_hash"] == gateway.current_diff_hash
    assert candidate["source_hash"] == baseline["source_hash"]
    assert candidate["observation"]["stdout"] == baseline["observation"]["stdout"]
    assert candidate["observation"]["exit_code"] == 0
    assert current_card["requirement_coverage"] == "not_assessed"
    assert not gateway.checks_by_diff and not cases.saved_cases(journal.events())
    assert all(row["status"] == "NOT_RUN" for row in gateway.visible_check_status())
    after = journal.path.read_bytes()
    restarted = restore(gateway, journal, workspace, smoke_package.public, backend)
    assert restarted.reproduction_review(diff_hash=restarted.current_diff_hash)[
        "probe_followup"] == current_card
    assert restarted.execute(replay_call).replayed
    assert journal.path.read_bytes() == after and backend.calls == 2
    assert not restarted.checks_by_diff


@pytest.mark.parametrize("projection", ["compact", "thin", "repair", "diagnosis", "completion"])
def test_probe_followup_preserves_observation_and_uncertainty_in_model_input(projection):
    card = {
        "baseline": {"action_id": "public-helper", "input_hash": "sha256:" + "a" * 64,
            "diff_hash": "sha256:" + "b" * 64, "source_hash": "sha256:" + "c" * 64,
            "observation": {"stdout": "PUBLIC_BASELINE_VALUE", "stderr": "public assertion",
                "stdout_omitted_chars": 7, "stderr_omitted_chars": 0,
                "exit_code": 1, "timed_out": False, "truncated": True}},
        "question": "Does the same public input preserve its value?",
        "current_diff_hash": "sha256:" + "d" * 64,
        "candidate": {"status": "not_run", "observation": None},
        "requirement_coverage": "not_assessed",
        "replay": {"reference_valid": True, "available": False, "arguments": None,
                   "reason": "probe_not_offered"},
    }
    state = {"public_task": {"task_id": "synthetic-public-task"},
             "workflow_gate": "ready_to_submit" if projection == "completion" else "needs_mutation",
             "completion_guidance": {"stage": "ready_to_submit"},
             "current_diff": {"patch_hash": card["current_diff_hash"], "patch": "public diff"},
             "available_tool_names": ["stop_task"],
             "reproduction_review": {"probe_followup": card}, "latest_tool_results": []}
    before = copy.deepcopy(state)
    if projection == "thin":
        state = thin_policy.project_state(state, "thin")
    elif projection == "repair":
        state = repair_context.project(state)
    elif projection == "diagnosis":
        state = diagnosis_context.project(state)
    elif projection == "completion":
        state = completion_context.project(state)
    state = compact_model_state(state, [])
    items = assemble_model_input(system_prompt="Public test", state=state, history=[],
                                 context_policy="segmented-v1")
    delivered = reconstruct_state(items, context_policy="segmented-v1")
    assert delivered["reproduction_review"]["probe_followup"] == card
    assert before["reproduction_review"]["probe_followup"] == card
    assert delivered["reproduction_review"]["probe_followup"]["candidate"]["status"] == "not_run"
    assert delivered["reproduction_review"]["probe_followup"]["requirement_coverage"] == (
        "not_assessed")
