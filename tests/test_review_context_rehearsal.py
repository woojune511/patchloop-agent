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
@pytest.mark.parametrize("fork", [False, True])
def test_review_then_native_submission(correct_source, tmp_path, monkeypatch, arm, fork):
    if fork:
        from patchloop.contracts import TaskEnvironment
        original_envelope = r.runner._run_envelope

        def fixture_envelope(**kwargs):
            # The source fixture injected an evaluator environment without a YAML file.
            kwargs["package"] = kwargs["package"].model_copy(update={"environment":
                TaskEnvironment(evaluator_image="test/image@sha256:" + "a" * 64,
                                image_digest="sha256:" + "a" * 64)})
            return original_envelope(**kwargs)

        monkeypatch.setattr(r.runner, "_run_envelope", fixture_envelope)
    seq = boundary(correct_source)
    client = c.ScriptedClient([[call("finish_task", {}, "finish")]])
    result = r.rehearse(
        correct_source,
        seq,
        tmp_path / arm,
        arm,
        client,
        reviewer_client=None if arm == "C" else reviewer(correct_source, seq),
        current_runtime_fork=fork,
    )
    assert result["result"]["terminal"] == "EVALUATOR_PASS", result
    assert result["live_model_calls"] == result["new_billed_cost_nanos"] == 0
    state = json.loads(client.created[0]["input"][-1]["content"])["state"]
    assert ("review_handoff" in state) == (arm != "C")
    assert state["remaining_budget"]["model_calls"] == (16 if arm == "C" else 14)
    assert state["remaining_budget"]["tool_actions"] == (48 if arm == "C" else 47)
    assert state["remaining_budget"]["active_wall_time_seconds"] <= 901
    if fork:
        journal = DevJournal(tmp_path / arm, correct_source.run_id)
        target = journal.load_envelope()
        assert target.runtime_hash == r.runner._runtime_hash()
        assert target.limits.model_dump(mode="json") == next(
            e["payload"]["limits"] for e in journal.events()
            if e["event_type"] == "review_repair_allowance")
        marker = next(e["payload"] for e in journal.events()
                      if e["event_type"] == "review_current_runtime_fork")
        assert marker["parent"]["envelope_hash"] == correct_source.envelope_hash
        assert marker["historical_funds_reopened"] is False
    if arm != "C":
        assert state["review_handoff"]["is_execution_receipt"] is False
        review_log = next((tmp_path / arm / "review" / "runs").glob("*.jsonl"))
        settled = [e["payload"] for e in DevJournal(
            tmp_path / arm / "review", review_log.stem).events()
            if e["event_type"] == "review_usage_settled"]
        allowance = next(e["payload"] for e in DevJournal(tmp_path / arm,
            correct_source.run_id).events() if e["event_type"] == "review_repair_allowance")
        assert len(settled) == 2
        assert sum(e["cost_nanos"] for e in settled) == allowance["simulated_review_cost"]
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
        review_log = next((tmp_path / "first/review/runs").glob("*.jsonl"))
        events = DevJournal(tmp_path / "first/review", review_log.stem).events()
        kinds = [e["event_type"] for e in events]
        assert "review_count_started" in kinds
        assert "review_usage_settled" not in kinds
        assert ("review_simulated_dispatch" in kinds) == (failure != "count")
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


@pytest.mark.parametrize("outcome", ["pass", "counterexample", "cleanup", "recovery", "deadline"])
def test_review_probe_receipts_and_abort(correct_source, tmp_path, monkeypatch, outcome):
    from patchloop.errors import RecoveryError

    class Probe:
        identity = {"image_digest": "fixture", "profile_hash": "fixture"}

        def run_probe(self, workspace, question, python_source, **kwargs):
            assert kwargs["deadline"].remaining_seconds() <= 180
            if outcome == "recovery":
                raise RecoveryError("fixture uncertainty")
            return {"exit_code": int(outcome == "counterexample"),
                    "passed": outcome == "pass", "stdout": "observed fixture",
                    "cleanup_failed": outcome == "cleanup",
                    "deadline_exhausted": outcome == "deadline"}

    monkeypatch.setattr(r, "admitted_probe", lambda *args: Probe())
    seq = boundary(correct_source)
    review = reviewer(correct_source, seq)
    probe = call("run_probe", {"question": "Observe fixture", "python_source": "print(1)"},
                 "verify")
    review.steps[0] = [probe]
    repair = c.ScriptedClient(stop_steps())
    output = tmp_path / outcome
    if outcome in {"cleanup", "recovery", "deadline"}:
        with pytest.raises(ContractError):
            r.rehearse(correct_source, seq, output, "B", repair, reviewer_client=review,
                       execute_reviewer_probes=True)
        assert not repair.created
        assert DevJournal(tmp_path / "panel", "run_dev_reviewpanel").events()[-1][
            "event_type"] == "panel_stopped"
    else:
        result = r.rehearse(correct_source, seq, output, "B", repair, reviewer_client=review,
                            execute_reviewer_probes=True)
        assert result["result"]["terminal"] == "AGENT_STOPPED"
        receipt = json.loads(review.created[1]["input"][-1]["output"])
        assert receipt["output"]["diff_hash"] == r.offline.load(
            correct_source, seq).diff["patch_hash"]
        assert receipt["output"]["passed"] == (outcome == "pass")
        state = json.loads(repair.created[0]["input"][-1]["content"])["state"]
        assert state["remaining_budget"]["tool_actions"] == 47
        assert state["review_handoff"]["is_execution_receipt"] is False


def test_probe_admission_mismatch_stops_before_dispatch(correct_source, tmp_path, monkeypatch):
    def reject(*args):
        raise ContractError("review probe identity changed")

    monkeypatch.setattr(r, "admitted_probe", reject)
    seq = boundary(correct_source)
    review = reviewer(correct_source, seq)
    repair = c.ScriptedClient(stop_steps())
    with pytest.raises(ContractError, match="identity changed"):
        r.rehearse(correct_source, seq, tmp_path / "mismatch", "A", repair,
                   reviewer_client=review, execute_reviewer_probes=True)
    assert not review.created and not repair.created


@pytest.mark.parametrize("changed", [False, True])
def test_probe_preflight_matches_source_identity(monkeypatch, changed):
    from types import SimpleNamespace

    loaded = SimpleNamespace(envelope=SimpleNamespace(
        probe_image_digest="source-image", probe_profile_hash="source-profile",
        prepared_probe_dependencies_path=None,
    ))
    marker = object()

    class Probe:
        def __init__(self, *, dependencies):
            assert dependencies is None

        def preflight(self, *, deadline):
            assert deadline is marker
            return {"image_digest": "source-image",
                    "profile_hash": "changed" if changed else "source-profile"}

    monkeypatch.setattr(r, "DockerProbeSandbox", Probe)
    if changed:
        with pytest.raises(ContractError, match="identity changed"):
            r.admitted_probe(loaded, marker)
    else:
        assert isinstance(r.admitted_probe(loaded, marker), Probe)
