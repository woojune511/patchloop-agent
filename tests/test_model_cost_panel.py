"""Model-only configuration, single-use dispatch and outcome accounting; no provider."""
import copy
from decimal import Decimal

import pytest

from diagnostics import model_cost_panel as panel
from diagnostics import probe_recheck_panel as driver
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError
from patchloop.util import sha256_json


def test_roster_is_balanced_fresh_and_model_is_only_request_difference(tmp_path):
    assert len(panel.TASKS) == 6 and len(panel.ORDER) == len(set(panel.ORDER)) == 24
    assert [v[2] for v in panel.TASKS.values()].count('PASS') == 3
    assert all('1413' not in c and '1733' not in c for c in panel.TASKS)
    for case in panel.TASKS:
        requests = [panel.request(case, arm, tmp_path).model_dump(mode='json')
                    for arm in panel.MODELS]
        for req in requests:
            assert req.pop('model') in panel.MODELS.values()
            assert req['limits']['max_accepted_mutations'] == 4
            assert req['limits']['max_model_calls'] == 40
            assert req['limits']['max_tool_actions'] == 100
            assert req['limits']['wall_time_seconds'] == 1800
            assert req['max_cost_usd'] == '3' and req['repeat'] == 1
            assert req['resume_run_id'] is None and req['probe_policy'] == 'none'
            assert req.get('probe_recheck', 'none') == 'none'
        assert requests[0] == requests[1]
    assert panel.ROW_CAP * len(panel.ORDER) == panel.CAP == Decimal('72')
    for case in panel.TASKS:
        orders = [[a for c, a, r in panel.ORDER if c == case and r == rep] for rep in (1, 2)]
        assert orders[0] == list(reversed(orders[1]))


def rows():
    return [{'case': c, 'arm': a, 'repetition': rep, 'settled': True, 'within_cap': True,
             'elapsed_seconds': 10, 'result': {'cost_nanos': 100 if a == 'mini' else 300,
             'runs': [{'terminal': 'EVALUATOR_PASS', 'artifact_hashes': {'submitted_patch': 'hash'},
                       'evaluator': {'task_acceptance': 'PASS', 'safety_state': 'PASS'}}]}}
            for c, a, rep in panel.ORDER]


def test_aggregate_counts_acceptance_unsubmitted_not_started_and_real_spend():
    data = rows()
    summary = panel.aggregate(data)
    assert summary['decision'] == 'SELECT_MINI_FOR_THIS_DEVELOPMENT_PANEL'
    assert summary['models']['mini']['recorded_cost_nanos'] == 1200
    assert summary['models']['mini']['cost_per_acceptance_nanos'] == 100
    data[0]['result']['runs'][0] = {'terminal': 'COST_CAP_REACHED'}
    summary = panel.aggregate(data)
    assert summary['models']['mini']['acceptance']['NOT_RUN'] == 1
    assert summary['models']['mini']['acceptance']['FAIL'] == 0
    assert summary['models']['mini']['unsubmitted'] == 1
    assert summary['decision'] == 'KEEP_FULL_REVIEW_TRADEOFF'
    assert panel.aggregate(data[:1])['models']['full']['not_started'] == 12
    assert panel.aggregate([])['models']['mini']['cost_per_acceptance_nanos'] is None


def test_uncertainty_invalidates_comparison_and_never_becomes_zero_cost():
    data = rows()
    data[0]['settled'] = False
    result = panel.aggregate(data)
    assert not result['comparison_valid']
    assert result['models']['mini']['recorded_cost_nanos'] == 1200
    assert result['models']['mini']['cost_per_acceptance_nanos'] is None
    assert not result['automatic_followup']
    with pytest.raises(ContractError, match='frozen order'):
        panel.aggregate(data + [copy.deepcopy(data[0])])


@pytest.mark.parametrize('stop_at', [None, 3])
def test_reused_driver_runs_exact_roster_and_stops_all_without_retry(
    tmp_path, monkeypatch, stop_at,
):
    root, live = tmp_path / 'packet', tmp_path / 'live'
    root.mkdir()
    digest = sha256_json({'frozen': True})
    panel.save(root, 'authorization.json', {'approved': True, 'human_message': 'synthetic approval',
                                           'packet_hash': digest})
    panel.save(root, 'preflight.json', {})
    DevJournal(root, panel.JOURNAL).append('preflight_passed', {
        'packet_hash': digest, 'receipt_hash': sha256_json({})})
    monkeypatch.setattr(panel, 'validate', lambda *args: {'live_root': str(live)})
    calls = []

    def execute(req):
        calls.append(req)
        return rows()[len(calls) - 1]['result']

    monkeypatch.setattr(driver.runner, 'run_dev', execute)
    monkeypatch.setattr(driver, 'settled', lambda *args: len(calls) != stop_at)
    result = panel.run(root, digest)
    assert len(calls) == (stop_at or 24)
    assert len({c.state_root for c in calls}) == len(calls)
    assert all(c.resume_run_id is None for c in calls)
    assert result['complete'] == (stop_at is None)
    with pytest.raises(ContractError, match='no restart'):
        panel.run(root, digest)


def test_missing_approval_does_not_call_provider(tmp_path, monkeypatch):
    monkeypatch.setattr(panel, 'validate', lambda *args: {'live_root': str(tmp_path / 'live')})
    monkeypatch.setattr(driver.runner, 'run_dev', lambda *a: pytest.fail('unapproved dispatch'))
    with pytest.raises(FileNotFoundError):
        panel.run(tmp_path, 'frozen')


def test_changed_manifest_rejected_before_dispatch(tmp_path):
    panel.save(tmp_path, 'manifest.json', {'changed': True})
    with pytest.raises(ContractError, match='manifest changed'):
        panel.validate(tmp_path, sha256_json({}))


def test_validation_artifact_drift_blocks_freeze(tmp_path, monkeypatch):
    from patchloop.util import sha256_bytes

    monkeypatch.setattr(panel, 'bindings', lambda: {'driver': 'hash'})
    monkeypatch.setattr(panel, 'runtime_content_hash', lambda: 'runtime')
    artifact = tmp_path / 'test-result'
    artifact.write_text('passed')
    receipt = {'passed': True, 'provider_calls': 0, 'runtime_hash': 'runtime',
               'implementation': panel.bindings(),
               'files': {str(artifact): sha256_bytes(artifact.read_bytes())}}
    panel.save(tmp_path, 'validation.json', receipt)
    panel.validate_evidence(tmp_path / 'validation.json')
    artifact.write_text('changed')
    with pytest.raises(ContractError, match='validation artifact changed'):
        panel.validate_evidence(tmp_path / 'validation.json')


@pytest.mark.parametrize('failure', ['slow', 'acceptance_error', 'safety_fail'])
def test_selection_does_not_trade_away_time_or_valid_completion(failure):
    data = rows()
    if failure == 'slow':
        for row in data:
            if row['arm'] == 'mini':
                row['elapsed_seconds'] = 13
    elif failure == 'acceptance_error':
        data[0]['result']['runs'][0]['evaluator']['task_acceptance'] = 'ERROR'
    else:
        data[0]['result']['runs'][0]['evaluator']['safety_state'] = 'FAIL'
    assert panel.aggregate(data)['decision'] != 'SELECT_MINI_FOR_THIS_DEVELOPMENT_PANEL'
