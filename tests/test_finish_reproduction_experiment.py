"""Development checks of the local diagnostic; distinct from its frozen final run."""

from __future__ import annotations

import pytest

from diagnostics import finish_reproduction_experiment as experiment
from patchloop.deadline import ExecutionDeadline
from patchloop.dev.state import DevJournal
from patchloop.runtime import repository_root


@pytest.mark.parametrize("condition", ["wrong_comment", "incomplete_current"])
def test_development_control_preserves_rejection_and_unknown_distinction(tmp_path, condition):
    with experiment.local_only():
        row = experiment.run_cell(
            repository_root(), tmp_path, condition, "ON",
            deadline=ExecutionDeadline.from_remaining(60), protocol_hash="development-only",
        )
    assert row["control_pass"], row
    assert row["completion_probe_executions"] == 1
    assert row["duplicate_probe_executions"] == 0
    assert row["duplicate_finish_replayed"]
    assert row["independent_acceptance"] == "NOT_RUN"
    events = DevJournal(tmp_path / row["row_id"], "run_dev_" + row["row_id"].replace(
        "_", "")).events()
    assert events[0]["event_type"] == "local_control_frozen"
    assert events[-1]["event_type"] == "local_control_finished"


def test_control_protocol_is_explicitly_scripted_and_does_not_claim_quality():
    protocol = experiment.protocol(repository_root())
    assert protocol["repeat_count"] == 1
    assert protocol["bounds"]["model_calls"] == 0
    assert protocol["bounds"]["provider_calls"] == 0
    assert "Same-current-runtime" in protocol["design"]
    assert "repair improvement" in protocol["limits"]
    assert protocol["expectations"]["no_original"]["ON"] == "accepted_unverified"
