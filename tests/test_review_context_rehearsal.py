import json

import pytest
from test_checkpoint_continuation import call, stop_steps
from test_deferred_scope_cue import correct_source as correct_source  # noqa: F401
from test_mutation_advice_checkpoint import source as source  # noqa: F401

from diagnostics import checkpoint_continuation as c
from diagnostics import review_context_rehearsal as r
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError


def boundary(source):
    events = DevJournal(source.root, source.run_id).events()
    return [e["sequence"] for e in events if e["event_type"] == "model_input_prepared"][-1]


def reviewer(source, sequence, failure=None):
    loaded = r.offline.load(source, sequence)
    report = {
        "suspected_behavior": "No new defect established",
        "evidence": "source read",
        "observation": "No new execution claim",
        "candidate_hash": loaded.diff["patch_hash"],
        "limitations": "Scripted fixture only",
    }
    read = call(
        "read_file",
        {"path": "mini_data_utils/csvlite.py", "start_line": 1, "end_line": 90},
        "inspect",
    )
    read["arguments"]["turn_decision"]["evidence_goal"] = "Inspect candidate behavior."
    return c.ScriptedClient(
        [
            [read],
            [{"name": "finish_review", "action_id": "offline_review_report", "arguments": report}],
        ],
        failure=failure,
    )


@pytest.mark.parametrize("arm", ["C", "A", "B"])
def test_review_then_native_submission(correct_source, tmp_path, arm):
    seq = boundary(correct_source)
    client = c.ScriptedClient([[call("finish_task", {}, "finish")]])
    result = r.rehearse(
        correct_source,
        seq,
        tmp_path / arm,
        arm,
        client,
        reviewer_client=None if arm == "C" else reviewer(correct_source, seq),
    )
    assert result["result"]["terminal"] == "EVALUATOR_PASS", result
    assert result["live_model_calls"] == result["new_billed_cost_nanos"] == 0
    state = json.loads(client.created[0]["input"][-1]["content"])["state"]
    assert ("review_handoff" in state) == (arm != "C")
    assert state["remaining_budget"]["model_calls"] == (16 if arm == "C" else 14)
    assert state["remaining_budget"]["tool_actions"] == (48 if arm == "C" else 47)
    assert state["remaining_budget"]["active_wall_time_seconds"] <= 901
    if arm != "C":
        assert state["review_handoff"]["is_execution_receipt"] is False
    with pytest.raises(ContractError, match="claimed"):
        r.rehearse(
            correct_source,
            seq,
            tmp_path / arm,
            arm,
            client,
            reviewer_client=None if arm == "C" else reviewer(correct_source, seq),
        )


@pytest.mark.parametrize("phase", ["review", "repair"])
@pytest.mark.parametrize("failure", ["count", "transport", "usage"])
def test_failure_stops_later_episodes(correct_source, tmp_path, phase, failure):
    seq = boundary(correct_source)
    client = c.ScriptedClient(stop_steps(), failure=failure if phase == "repair" else None)
    review = reviewer(correct_source, seq, failure if phase == "review" else None)
    if phase == "review":
        with pytest.raises((TimeoutError, ContractError)):
            r.rehearse(correct_source, seq, tmp_path / "first", "B", client, reviewer_client=review)
        assert not client.created
    else:
        result = r.rehearse(
            correct_source, seq, tmp_path / "first", "B", client, reviewer_client=review
        )
        assert result["stop_remaining"]
    with pytest.raises(ContractError, match="panel stopped"):
        r.rehearse(correct_source, seq, tmp_path / "second", "C", c.ScriptedClient(stop_steps()))


def test_unfinished_episode_cannot_be_skipped(correct_source, tmp_path):
    panel = DevJournal(tmp_path / "panel", "run_dev_reviewpanel")
    panel.append("episode_started", {"arm": "B", "output": "interrupted"})
    with pytest.raises(ContractError, match="unfinished episode"):
        r.rehearse(
            correct_source,
            boundary(correct_source),
            tmp_path / "next",
            "C",
            c.ScriptedClient(stop_steps()),
        )


def test_report_does_not_replace_current_diff_check(correct_source, tmp_path):
    seq = boundary(correct_source)
    read = call(
        "read_file",
        {"path": "mini_data_utils/csvlite.py", "start_line": 1, "end_line": 90},
        "inspect",
    )
    read["arguments"]["turn_decision"]["evidence_goal"] = "Read the exact current edit anchor."
    change = call(
        "replace_text",
        {
            "path": "mini_data_utils/csvlite.py",
            "old_text": "import csv",
            "new_text": "import csv\n# Rehearsed edit",
            "occurrence": 1,
            "hypothesis": "A comment preserves parser behavior.",
            "expected_behavior": "CSV behavior remains unchanged.",
            "causal_revision": None,
        },
        "mutate",
    )
    steps = [
        [read],
        [change],
        [call("run_check", {"check_id": "existing-unit-tests"}, "verify")],
        [call("finish_task", {}, "finish")],
    ]
    for batch in steps:
        for action in batch:
            action["action_id"] = "repair_" + action["action_id"]
    client = c.ScriptedClient(steps)
    result = r.rehearse(
        correct_source,
        seq,
        tmp_path / "edit",
        "B",
        client,
        reviewer_client=reviewer(correct_source, seq),
    )
    assert result["result"]["terminal"] == "EVALUATOR_PASS", result
    states = [json.loads(req["input"][-1]["content"])["state"] for req in client.created]
    assert "review_handoff" in states[0]
    assert all("review_handoff" not in state for state in states[1:])
    assert states[2]["current_diff"]["patch_hash"] != states[0]["current_diff"]["patch_hash"]
