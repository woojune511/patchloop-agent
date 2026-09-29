from decimal import Decimal
from types import SimpleNamespace

import pytest

from diagnostics import candidate_review_repair as seeded
from diagnostics import observation_repair_panel as experiment
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError
from patchloop.util import utc_now


def test_only_observation_changes_and_currency_remains_diff_bound():
    output = dict(stdout='actual route', stderr='AssertionError', exit_code=1,
                  setup_checks={'status': 'passed'})
    arms = {a: experiment.feedback('sha256:seed', 'public requirement', 'assert x == y',
                                  'sha256:receipt', output, a) for a in ('A', 'B')}
    assert [k for k in arms['A'] if arms['A'][k] != arms['B'][k]] == ['stdout']
    assert arms['A']['stdout'] == experiment.WITHHELD
    for arm in arms.values():
        seeded.validate_feedback(arm, 'sha256:seed')
        view = seeded.feedback_overlay({'current_diff': {'patch_hash': 'sha256:new'}}, arm)
        assert view['currency'] == 'historical_candidate'
        assert view['observed_on_diff_hash'] == 'sha256:seed'


def test_fixed_order_total_and_no_implicit_approval(tmp_path):
    assert experiment.ORDER == ('A1', 'B1', 'B2', 'A2')
    assert len(experiment.ORDER) * experiment.ROW_CAP == experiment.CAP == Decimal('8')
    with pytest.raises(ContractError, match='exact new USD 8'):
        experiment.run(tmp_path, 'unused', approved_cap=Decimal('7'))
    assert list(tmp_path.iterdir()) == []


def test_request_preserves_exact_model_and_bounded_repair(tmp_path):
    request = experiment.request(tmp_path)
    assert request.model == 'gpt-5.4-2026-03-05'
    assert request.reasoning_effort == 'xhigh'
    assert request.max_cost_usd == Decimal('2')
    assert request.limits.wall_time_seconds == 900
    assert request.limits.max_protocol_recoveries == 0
    assert request.repeat == 1 and request.resume_run_id is None
    assert request.enable_probes and request.repair_recheck


def test_runtime_uncertainty_stops_all_before_audit(tmp_path, monkeypatch):
    packet = {'pricing_verified_on': utc_now().date().isoformat(), 'payload': {
        'seed': {'patch': 'patch', 'patch_hash': 'hash'}, 'base_commit': 'base',
        'source_run_id': 'run_dev_source', 'feedback': {'A': {}, 'B': {}}}}
    monkeypatch.setattr(experiment, 'validate', lambda *_: packet)
    monkeypatch.setattr(experiment.runner, '_require_tracked_clean_paths', lambda *_: None)
    monkeypatch.setattr(experiment.runner, '_run_one', lambda **_: SimpleNamespace(
        stop_remaining=True))
    calls = []

    def run_seeded(request, **kwargs):
        calls.append(kwargs['branch'])
        experiment.runner._run_one()
        return {'runs': [{'terminal': 'PROVIDER_TIMEOUT_OR_UNKNOWN'}]}

    monkeypatch.setattr(experiment.seeded, 'run_seeded', run_seeded)
    monkeypatch.setattr(experiment, 'DockerProbeSandbox',
                        lambda **_: pytest.fail('audit forbidden after uncertainty'))
    DevJournal(tmp_path, 'run_dev_observationrepair').append('preflight', {})
    result = experiment.run(tmp_path, 'hash', approved_cap=Decimal('8'))
    assert calls == ['A1'] and len(result) == 1
    with pytest.raises(ContractError, match='no resume'):
        experiment.run(tmp_path, 'hash', approved_cap=Decimal('8'))
    assert calls == ['A1']
