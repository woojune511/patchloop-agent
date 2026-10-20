"""Follow-up patch provenance, cleanup ordering and conservative stop behavior."""

from decimal import Decimal
from types import SimpleNamespace

import pytest

from diagnostics import mini_swe_extended as panel
from diagnostics.mini_swe_runtime import OperationalStop
from patchloop.deadline import ExecutionDeadlineExceeded


@pytest.fixture
def scenario(monkeypatch, tmp_path):
    events = []
    state = SimpleNamespace(terminal="LimitsExceeded", submission="", failure=None,
                            uncertain=False, patch=b"working diff", cleanup_failure=False)
    task = tmp_path / "task.txt"
    task.write_text("PUBLIC ISSUE ONLY", encoding="utf-8")
    folder = tmp_path / "run"
    folder.mkdir()
    row = {"index": 8, "instance_id": "public-instance", "task_text": str(task)}

    def model(client, config, root, deadline, **limits):
        assert limits == {"cap_usd": Decimal("3"), "max_calls": 250,
                          "max_input_tokens": 250000}
        return SimpleNamespace(ledger=SimpleNamespace(spent_nanos=1000), calls=40,
                               uncertain=state.uncertain)

    class Environment:
        actions = 40

        def __init__(self, row, root, deadline, **limits):
            assert limits == {"max_actions": 1000, "lifetime_seconds": 3930}

        def cleanup(self):
            events.append("cleanup")
            if state.cleanup_failure:
                raise OperationalStop("unconfirmed cleanup")

    class Agent:
        def __init__(self, model, env, **config):
            pass

        def run(self, text):
            assert text == "PUBLIC ISSUE ONLY"
            if state.failure:
                raise state.failure
            return {"exit_status": state.terminal, "submission": state.submission}

        def serialize(self):
            return {"messages": []}

    def collect(env, folder):
        events.append("capture")
        path = folder / "operator-collected.patch"
        path.write_bytes(state.patch)
        return path

    def assess(folder, row, patch):
        assert events[-1] == "cleanup"
        events.append("grade")
        return {"scope": "PASS", "native": "FAIL", "native_cleanup": "CONFIRMED"}

    monkeypatch.setattr(panel, "CountedModel", model)
    monkeypatch.setattr(panel, "PublicContainer", Environment)
    monkeypatch.setattr(panel, "collect_working_diff", collect)
    monkeypatch.setattr(panel.baseline, "assess_patch", assess)
    return state, events, lambda: panel.execute_row(None, {"model": {}, "agent": {}},
                                                   row, folder, Agent)


def test_known_limit_collects_before_cleanup_and_grades_after(scenario):
    state, events, execute = scenario
    result = execute()
    assert events == ["capture", "cleanup", "grade", "cleanup"]
    assert result["terminal"] == "LimitsExceeded"
    assert result["candidate_origin"] == "operator_final_diff"
    assert result["candidate_available"] and not result["submitted"]
    assert result["native"] == "FAIL" and not result["stop_panel"]


def test_normal_submission_keeps_its_exact_origin(scenario):
    state, events, execute = scenario
    state.terminal, state.submission = "Submitted", "agent diff"
    result = execute()
    assert events == ["cleanup", "grade", "cleanup"]
    assert result["submitted"] and result["candidate_origin"] == "agent_submission"


@pytest.mark.parametrize("uncertain", [False, True])
def test_operational_failure_never_collects_or_grades(scenario, uncertain):
    state, events, execute = scenario
    state.uncertain = uncertain
    state.failure = OperationalStop("provider transport or shell timeout")
    result = execute()
    assert events == ["cleanup"]
    assert result["stop_panel"] and result["billing_known"] is not uncertain
    assert result["native"] == "NOT_RUN" and not result["candidate_available"]


def test_uncertainty_cannot_be_hidden_by_a_limit_terminal(scenario):
    state, events, execute = scenario
    state.uncertain = True
    result = execute()
    assert result["stop_panel"] and not result["billing_known"]
    assert events == ["cleanup"]


def test_deadline_after_settlement_allows_only_capture(scenario):
    state, events, execute = scenario
    state.failure = ExecutionDeadlineExceeded("solver finished")
    result = execute()
    assert result["terminal"] == "SolverDeadline"
    assert events[:3] == ["capture", "cleanup", "grade"]


def test_empty_working_diff_remains_honestly_ungraded(scenario):
    state, events, execute = scenario
    state.patch = b""
    result = execute()
    assert events == ["capture", "cleanup", "cleanup"]
    assert result["native"] == "NOT_RUN" and not result["candidate_available"]
    assert not result["submitted"] and not result["stop_panel"]


def test_cleanup_uncertainty_blocks_private_grading(scenario):
    state, events, execute = scenario
    state.cleanup_failure = True
    result = execute()
    assert "grade" not in events and result["stop_panel"]
    assert result["native"] == "NOT_RUN"


def test_all_five_caps_include_the_prior_billed_attempts():
    assert panel.INDICES == (8, 13, 16, 17, 18)
    maximum = Decimal(panel.PRIOR_NANOS) / 10**9 + panel.ROW_CAP * len(panel.INDICES)
    assert maximum == Decimal("18.2171004") and maximum < Decimal("24")
