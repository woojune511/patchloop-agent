"""Independent correction ceilings through counted dispatch and exact recovery."""

import pytest
from test_dev_completion_recovery import assert_accounting, paid_fixture
from test_dev_runner import _crash_journal_once, _SimulatedCrash
from test_dev_segments import assert_submitted, records

from patchloop.dev import runner
from patchloop.errors import ResumeContractMismatch


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("correction dispatch controls must not access the network")
    monkeypatch.setattr("socket.socket.connect", forbidden)


@pytest.mark.parametrize("normal,correction", [(40_000, 25_000), (8_000, 25_000)])
def test_correction_dispatch_and_count_use_independent_allowance(tmp_path, monkeypatch,
                                                              normal, correction):
    request, inputs, counts, views, ceilings = paid_fixture(monkeypatch, tmp_path, cap="1.20")
    request = request.model_copy(update={"max_output_tokens": normal,
                                         "max_correction_output_tokens": correction})
    counted_ceilings = []
    count = runner.OpenAIResponsesAdapter.count_input_tokens_v2

    def record_count(self, payload, **kwargs):
        counted_ceilings.append(payload["max_output_tokens"])
        return count(self, payload, **kwargs)

    monkeypatch.setattr(runner.OpenAIResponsesAdapter, "count_input_tokens_v2", record_count)
    result = runner.run_dev(request)["runs"][0]
    assert_submitted(result)
    assert inputs == counts and len(inputs) == 5
    assert counted_ceilings == [normal, normal, correction, normal, normal]
    assert ceilings[2] == correction
    assert all(value <= normal for i, value in enumerate(ceilings) if i != 2)
    detail = views[2]["remaining_budget"]["cost"]["completion_cost"]
    assert detail["correction_pending"] and detail["current_minimum_output_ceiling"] == correction
    assert detail["correction_cost_reserved_nanos"] == 0
    journal = assert_accounting(request, result)
    envelope = journal.load_envelope()
    assert envelope.max_output_tokens == normal
    assert envelope.max_correction_output_tokens == correction
    assert envelope.completion_cost_contract["correction_output_tokens"] == correction


def test_correction_allowance_is_bound_across_crash_and_resume(tmp_path, monkeypatch):
    request, inputs, counts, views, ceilings = paid_fixture(monkeypatch, tmp_path, cap="1.20")
    request = request.model_copy(update={"max_output_tokens": 40_000,
                                         "max_correction_output_tokens": 25_000})
    _crash_journal_once(monkeypatch, event_type="protocol_correction", when="after")
    with pytest.raises(_SimulatedCrash):
        runner.run_dev(request)
    journal, _ = records(request)
    resumed = request.model_copy(update={"resume_run_id": journal.run_id})
    for value in [None, 20_000]:
        changed = resumed.model_copy(update={"max_correction_output_tokens": value})
        assert runner._model_hash(changed, None) != runner._model_hash(resumed, None)
        with pytest.raises(ResumeContractMismatch):
            runner.run_dev(changed)
    result = runner.run_dev(resumed)["runs"][0]
    assert_submitted(result)
    assert inputs == counts and len(inputs) == 5 and ceilings[2] == 25_000
    assert views[2]["remaining_budget"]["cost"]["completion_cost"]["correction_pending"]
    journal = assert_accounting(request, result)
    assert sum(e["event_type"] == "protocol_correction" for e in journal.events()) == 1
