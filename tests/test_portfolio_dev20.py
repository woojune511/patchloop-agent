"""Frozen historical inputs, comparison semantics and one-shot evaluation; no provider."""
import copy
from pathlib import Path
from types import SimpleNamespace

import pytest

from diagnostics import portfolio_dev20 as panel
from diagnostics import probe_recheck_panel as driver
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError
from patchloop.runtime import repository_root
from patchloop.task_loader import load_task_package
from patchloop.util import sha256_bytes, sha256_json


def historical():
    return {'rows': [{'instance_id': f'case{i}', 'index': i + 1,
                      'original_resolved': i < 10, 'cost_nanos': 500,
                      'elapsed_seconds': 10} for i in range(20)]}


def outcomes(passes=11):
    return [{'case': f'case{i}', 'settled': True, 'within_cap': True, 'elapsed_seconds': 12,
             'assessment': {'ok': True, 'agreement': True,
                            'status': 'PASS' if i < passes else 'FAIL', 'elapsed_seconds': 3},
             'result': {'cost_nanos': 600, 'runs': [{
                 'run_id': f'run{i}',
                 'terminal': 'EVALUATOR_PASS' if i < passes else 'EVALUATOR_FAIL',
                 'artifact_hashes': {'submitted_patch': 'hash'},
                 'evaluator': {'task_acceptance': 'PASS' if i < passes else 'FAIL',
                               'safety_state': 'PASS'}}]}}
            for i in range(20)]


def test_request_preserves_old_settings_and_has_no_added_inputs(tmp_path):
    req = panel.request({'instance_id': 'sqlfluff__sqlfluff-1625',
                         'prepared_source': str(tmp_path / 'source.json')}, tmp_path / 'live')
    assert req.task == repository_root() / panel.FROZEN_TASK
    assert req.model == panel.MODEL and req.repeat == 1 and req.resume_run_id is None
    assert req.max_cost_usd == panel.ROW_CAP and panel.ROW_CAP * 20 == panel.CAP
    assert req.reasoning_effort == 'xhigh' and req.max_output_tokens == 25000
    assert req.context_policy == 'segmented-v1' and req.planning_policy == 'brief-v1'
    assert req.segment_boundary_policy == 'result-or-size-v1'
    assert req.enable_probes and req.probe_policy == req.probe_recheck == 'none'
    assert req.repair_recheck and req.repair_inspection_policy == 'protected-v1'
    assert req.completion_cost_policy == 'per-call-v1' and req.prepared_probe_dependencies is None
    assert [req.limits.max_model_calls, req.limits.max_tool_actions,
            req.limits.max_accepted_mutations, req.limits.wall_time_seconds] == [40, 100, 4, 1800]


def test_frozen_package_keeps_historical_bytes_and_current_task_is_unchanged():
    frozen = repository_root() / panel.FROZEN_TASK
    assert sha256_bytes(frozen.read_bytes()) == (
        'sha256:772aa940d8855e3268569e750ef8790b0019345118468568117470525c9528d8')
    task = load_task_package(frozen.parent)
    assert not task.public.test_suites
    current = repository_root() / 'tasks/dev-train/swebench-lite-dev-sqlfluff-sqlfluff-1625'
    assert load_task_package(current).public.test_suites


def test_first_input_is_fresh_and_public_only(gateway_factory):
    import json

    from patchloop.dev.runner import _build_context, _RunCounters

    gateway, journal, _ = gateway_factory()
    public = load_task_package((repository_root() / panel.FROZEN_TASK).parent).public
    gateway.public_task = public
    package = SimpleNamespace(public=public, private={'operator_answer': 'PRIVATE_CANARY'})
    text = _build_context(
        package=package, gateway=gateway, journal=journal, correction=None,
        latest_tool_results=[], counters=_RunCounters(), elapsed_seconds=0,
        limits=gateway.limits, planning_policy='brief-v1', repair_recheck=True)
    state = json.loads(text)
    assert 'PRIVATE_CANARY' not in text and 'operator_answer' not in text
    assert state['public_task'] == public.model_dump(mode='json')
    assert state['current_diff']['patch'] == '' and state['recent_checks'] == []
    assert state['latest_tool_results'] == [] and 'recent_tests' not in state


@pytest.mark.parametrize('count,decision', [
    (10, 'CLOSE_WITH_DOCUMENTATION'), (11, 'PREPARE_TEST300_NOT_AUTHORIZED_TO_RUN')])
def test_advance_is_complete_agreement_and_eleven_not_a_claim(count, decision):
    result = panel.aggregate(outcomes(count), historical())
    assert result['decision'] == decision
    assert result['resolved'] == count and result['planned'] == 20
    assert result['recorded_cost_nanos'] == 12000
    assert result['solve_seconds'] == 240 and result['native_seconds'] == 60
    assert not result['official'] and not result['claim_eligible']
    assert not result['automatic_followup']


@pytest.mark.parametrize(
    'failure', ['unsubmitted', 'uncertain', 'error', 'disagreement', 'missing'])
def test_incomplete_or_uncertain_results_never_advance(failure):
    rows = outcomes(20)
    if failure == 'unsubmitted':
        rows[0]['result']['runs'][0] = {'terminal': 'COST_CAP_REACHED'}
        rows[0]['assessment'] = {'ok': True, 'status': 'NOT_RUN', 'elapsed_seconds': 0}
    elif failure == 'uncertain':
        rows[0]['settled'] = False
    elif failure == 'error':
        rows[0]['assessment'] = {'ok': False, 'status': 'ERROR'}
    elif failure == 'disagreement':
        rows[0]['assessment']['agreement'] = False
        rows[0]['assessment']['ok'] = False
    else:
        rows = rows[:19]
    result = panel.aggregate(rows, historical())
    assert result['decision'] == 'INCOMPLETE_NO_ADVANCE'
    assert result['recorded_cost_nanos'] > 0
    if failure == 'unsubmitted':
        assert result['unsubmitted'] == 1 and result['rows'][0]['native'] == 'NOT_RUN'
    if failure == 'missing':
        assert result['not_started'] == 1 and len(result['rows']) == 20
        assert result['rows'][-1]['cost_nanos'] is None


def test_wrong_order_and_duplicate_results_rejected():
    rows = outcomes()
    with pytest.raises(ContractError, match='frozen order'):
        panel.aggregate(list(reversed(rows)), historical())
    with pytest.raises(ContractError, match='frozen order'):
        panel.aggregate(rows + [copy.deepcopy(rows[0])], historical())


@pytest.mark.parametrize('stop', [False, True])
def test_existing_driver_stops_next_dispatch_and_restart(tmp_path, monkeypatch, stop):
    root, live = tmp_path / 'packet', tmp_path / 'live'
    root.mkdir()
    digest = 'frozen'
    panel.save(root, 'authorization.json', {'approved': True, 'packet_hash': digest,
                                           'human_message': 'synthetic approval'})
    panel.save(root, 'preflight.json', {})
    DevJournal(root, panel.JOURNAL).append('preflight_passed', {
        'packet_hash': digest, 'receipt_hash': sha256_json({})})
    monkeypatch.setattr(driver, 'settled', lambda *a: True)
    calls = []

    def execute(req):
        calls.append(req)
        return outcomes()[0]['result']

    monkeypatch.setattr(driver.runner, 'run_dev', execute)
    from contextlib import nullcontext

    def run():
        return driver.run_fresh_rows(
            root, digest, validate_packet=lambda *a: None,
            order=(('one', 'current', 1), ('two', 'current', 1)), live_root=live,
            request_for=lambda c, a, s: panel.request(
                {'instance_id': c, 'prepared_source': str(tmp_path / 'src')}, s),
            instruction_scope=lambda _: nullcontext(), row_cap=panel.ROW_CAP,
            total_cap=panel.CAP, journal_id=panel.JOURNAL,
            after_row=lambda *a: {'ok': not stop, 'status': 'ERROR' if stop else 'PASS'})

    result = run()
    assert len(calls) == (1 if stop else 2)
    assert result['rows'][0]['assessment']['ok'] is not stop
    assert result['allocation'] == 'CLOSED'
    with pytest.raises(ContractError, match='no restart'):
        run()


def test_changed_manifest_and_missing_approval_block_dispatch(tmp_path, monkeypatch):
    panel.save(tmp_path, 'manifest.json', {})
    with pytest.raises(ContractError, match='manifest changed'):
        panel.validate(tmp_path, 'different')
    monkeypatch.setattr(panel, 'validate', lambda *a: {
        'native_identity': {}, 'live_root': str(tmp_path / 'live')})
    monkeypatch.setattr(panel, 'native_identity', lambda: {})
    monkeypatch.setattr(panel, 'baseline', lambda: (historical(), historical()))
    monkeypatch.setattr(driver.runner, 'run_dev', lambda *a: pytest.fail('unapproved dispatch'))
    with pytest.raises(FileNotFoundError):
        panel.run(tmp_path, 'frozen')


@pytest.mark.parametrize('native_error_at', [None, 3])
def test_panel_wiring_accounts_then_evaluates_before_next_solve(
    tmp_path, monkeypatch, native_error_at,
):
    root, live = tmp_path / 'packet', tmp_path / 'live'
    root.mkdir()
    history = historical()
    old = copy.deepcopy(history)
    for entry in old['rows']:
        entry['prepared_source'] = str(tmp_path / 'source.json')
    monkeypatch.setattr(panel, 'baseline', lambda: (old, history))
    monkeypatch.setattr(panel, 'validate', lambda *a: {
        'native_identity': {}, 'live_root': str(live)})
    monkeypatch.setattr(panel, 'native_identity', lambda: {})
    monkeypatch.setattr(driver, 'settled', lambda *a: True)
    panel.save(root, 'authorization.json', {'approved': True, 'packet_hash': 'frozen',
                                           'human_message': 'synthetic approval'})
    panel.save(root, 'preflight.json', {})
    DevJournal(root, panel.JOURNAL).append('preflight_passed', {
        'packet_hash': 'frozen', 'receipt_hash': sha256_json({})})
    sequence = []

    def solve(req):
        assert not sequence or sequence[-1] == 'native'
        index = len(sequence) // 2
        result = outcomes()[index]['result']
        result['runs'][0].update(run_id='run_dev_synthetic', call_counts={'model': 1})
        DevJournal(req.state_root, 'run_dev_synthetic').append('provider_call_finished', {
            'call_id': 'one', 'cost_nanos': result['cost_nanos']})
        sequence.append('solve')
        return result

    def assess(root, entry, row, req):
        sequence.append('native')
        return {'ok': entry['index'] != native_error_at,
                'agreement': entry['index'] != native_error_at,
                'status': ('ERROR' if entry['index'] == native_error_at else
                           row['result']['runs'][0]['evaluator']['task_acceptance']),
                'elapsed_seconds': 1}

    monkeypatch.setattr(driver.runner, 'run_dev', solve)
    monkeypatch.setattr(panel, 'native_assessment', assess)
    result = panel.run(root, 'frozen')
    assert result['started'] == (native_error_at or 20)
    assert result['decision'] == ('INCOMPLETE_NO_ADVANCE' if native_error_at else
                                  'PREPARE_TEST300_NOT_AUTHORIZED_TO_RUN')
    assert len(sequence) == result['started'] * 2


@pytest.mark.parametrize('mode', ['pass', 'fail', 'missing', 'cleanup', 'timeout'])
def test_native_assessment_preserves_candidate(tmp_path, monkeypatch, mode):
    import subprocess

    entry = {'index': 1, 'instance_id': 'case', 'native_row': str(tmp_path / 'native-row.json')}
    patch = b'diff --git a/a.py b/a.py\n'
    patch_hash = sha256_bytes(patch)
    sha = patch_hash.split(':')[1]
    state = tmp_path / 'live'
    path = state / 'artifacts/objects/sha256' / sha[:2] / sha[2:]
    path.parent.mkdir(parents=True)
    path.write_bytes(patch)
    row = outcomes()[0]
    row['result']['runs'][0]['artifact_hashes']['submitted_patch'] = patch_hash
    if mode == 'fail':
        row['result']['runs'][0]['evaluator']['task_acceptance'] = 'FAIL'

    def execute(command, **kwargs):
        assert '--predictions' in command
        assert 'OPENAI_API_KEY' not in kwargs['env']
        if mode == 'timeout':
            raise subprocess.TimeoutExpired(command, 600)
        output = Path(command[command.index('--output') + 1])
        output.mkdir()
        panel.save(output, 'cleanup.json',
                   {'remaining': ['container'] if mode == 'cleanup' else []})
        if mode != 'missing':
            panel.save(output, 'control-1.json', {'instance_id': 'case', 'complete': True,
                                                'missing_count': 0, 'resolved': mode != 'fail'})
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(panel.subprocess, 'run', execute)
    monkeypatch.setenv('OPENAI_API_KEY', 'must-not-leak')
    result = panel.native_assessment(tmp_path, entry, row, SimpleNamespace(state_root=state))
    assert result['ok'] is (mode in ('pass', 'fail'))
    assert result['status'] == ('PASS' if mode == 'pass' else 'FAIL' if mode == 'fail' else 'ERROR')
    assert path.read_bytes() == patch
    with pytest.raises(FileExistsError):
        panel.native_assessment(tmp_path, entry, row, SimpleNamespace(state_root=state))
