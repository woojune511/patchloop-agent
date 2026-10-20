"""Frozen allocation and independent public-observation boundaries."""

import copy
import json

import pytest

from diagnostics import probe_recheck_panel as panel
from diagnostics import probe_recheck_public as public
from patchloop.dev import working_plan
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError
from patchloop.task_loader import load_task_package
from patchloop.util import sha256_json


def test_roster_limits_and_only_intended_arm_differences(tmp_path):
    assert len(panel.ORDER) == 18 and len(set(panel.ORDER)) == 18
    texts = {}
    for arm in 'ABC':
        with panel.instructions(arm):
            texts[arm] = working_plan.instructions('brief-v1')
    assert texts['B'] == texts['C'] != texts['A']
    for case in panel.TASKS:
        requests = [panel.request(case, arm, tmp_path).model_dump(mode='json') for arm in 'ABC']
        for row in requests:
            assert row['model'] == panel.MODEL and row['max_cost_usd'] == '3'
            assert row['limits']['max_model_calls'] == 40
            assert row['limits']['max_tool_actions'] == 100
            row.pop('probe_policy')
            row.pop('probe_recheck', None)
        assert requests[0] == requests[1] == requests[2]


def complete_rows():
    return [{'label': f'{c}{a}{n}', 'case': c, 'arm': a, 'repetition': n,
             'settled': True, 'within_cap': True, 'elapsed_seconds': 10,
             'result': {'cost_nanos': 100, 'runs': [{'terminal': 'EVALUATOR_FAIL'}]}}
            for c, a, n in panel.ORDER]


def test_adoption_requires_correctness_mechanism_no_regression_and_overhead():
    rows = complete_rows()
    for row in rows:
        if row['case'] == '1694' or row['arm'] == 'C':
            row['result']['runs'][0]['terminal'] = 'EVALUATOR_PASS'
    assert panel.decide(rows, mechanism_supported=True, contracts_passed=True)[
        'decision'] == 'SELECT_FOR_EXPOSED_TASK_GROUP'
    for mechanism, contracts in [(False, True), (True, False)]:
        assert panel.decide(rows, mechanism_supported=mechanism, contracts_passed=contracts)[
            'decision'] == 'KEEP_BASELINE'
    costly = copy.deepcopy(rows)
    for row in costly:
        if row['arm'] == 'C':
            row['result']['cost_nanos'] = 126
    assert panel.decide(costly, mechanism_supported=True, contracts_passed=True)[
        'decision'] == 'KEEP_BASELINE'
    with pytest.raises(ContractError, match='complete exact panel'):
        panel.decide(rows[:-1], mechanism_supported=True, contracts_passed=True)


def test_sql_complete_output_controls_are_not_symptom_checks(tmp_path):
    req = panel.request('1733', 'A', tmp_path)
    issue = load_task_package(req.task.parent).public.issue.description
    spec = public.design('1733', issue)
    from diagnostics.output_predicate_controls import controls
    for row in controls(issue):
        result = {'exit_code': 0, 'stdout': json.dumps({'output': row['actual']})}
        assert (public.classify(result, spec)['status'] == 'PASS') == row['expected_accept']
    assert 'Linter' in spec['program'] and 'lint_string' in spec['program']


def test_pydicom_constructor_and_entrypoint_checks_do_not_accept_setup_or_partial_output():
    spec = public.design('1694', 'public issue')
    rows = [{'suppress': flag, 'raw_before': True, 'raw_value': '2.0 ',
             'conversion_rejected': True, 'completed': flag, 'invalid_omitted': True,
             'valid_preserved': True, 'error': 'ValueError'} for flag in [True, False]]
    result = {'exit_code': 0, 'stdout': json.dumps(rows)}
    assert public.classify(result, spec)['status'] == 'PASS'
    rows[0]['conversion_rejected'] = False
    assert public.classify({**result, 'stdout': json.dumps(rows)}, spec)['status'] == 'UNASSESSED'
    assert public.classify({**result, 'exit_code': 1}, spec)['status'] == 'UNASSESSED'
    write = public.design('1413', 'public issue')
    assert 'ds.save_as' in write['program'] and 'dcmread' in write['program']
    assert public.classify({'exit_code': 0, 'stdout': '[]'}, write)['status'] == 'UNASSESSED'


def test_no_authorization_means_no_dispatch(tmp_path, monkeypatch):
    monkeypatch.setattr(panel, 'validate', lambda *args: {})
    monkeypatch.setattr(panel.runner, 'run_dev', lambda *args: pytest.fail('unauthorized dispatch'))
    with pytest.raises(FileNotFoundError):
        panel.run(tmp_path, sha256_json({}))


def test_false_or_wrong_packet_authorization_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(panel, 'validate', lambda *args: {})
    for approval in ({'approved': False}, {'approved': True, 'human_message': 'yes',
                                        'packet_hash': 'wrong'}):
        (tmp_path / 'authorization.json').write_text(json.dumps(approval))
        with pytest.raises(ContractError, match='exact human'):
            panel.run(tmp_path, sha256_json({}))


@pytest.mark.parametrize('uncertain_at', [None, 3])
def test_dispatch_roster_no_retries_and_stop_all_on_uncertainty(
    tmp_path, monkeypatch, uncertain_at,
):
    root = tmp_path / 'panel'
    root.mkdir()
    packet_hash = sha256_json({'frozen': True})
    panel.save(root, 'authorization.json', {'approved': True, 'human_message': 'exact test grant',
                                          'packet_hash': packet_hash})
    panel.save(root, 'preflight.json', {})
    journal = DevJournal(root, 'run_dev_proberecheckpanel')
    journal.append('preflight_passed', {
        'packet_hash': packet_hash, 'receipt_hash': sha256_json({}),
    })
    monkeypatch.setattr(panel, 'LIVE', tmp_path / 'live')
    monkeypatch.setattr(panel, 'validate', lambda *args: {})
    dispatched = []

    def execute(req):
        dispatched.append(req)
        return {'cost_nanos': 10, 'runs': [{'terminal': 'EVALUATOR_PASS'}]}

    monkeypatch.setattr(panel.runner, 'run_dev', execute)
    monkeypatch.setattr(panel, 'settled', lambda *args: len(dispatched) != uncertain_at)
    result = panel.run(root, packet_hash)
    count = uncertain_at or 18
    assert result['completed'] == count and result['recorded_cost_nanos'] == 10 * count
    assert [r.state_root.name for r in dispatched] == [
        f'{c}{a}{n}' for c, a, n in panel.ORDER[:count]]
    assert len(result['not_run']) == 18 - count
    assert result['allocation'] == 'CLOSED' and result['resume_allowed'] is False
    with pytest.raises(ContractError, match='no restart'):
        panel.run(root, packet_hash)


def test_packet_digest_rejects_changed_payload_before_dispatch(tmp_path):
    panel.save(tmp_path, 'preparation.json', {})
    panel.save(tmp_path, 'packet.json', {'changed': True})
    with pytest.raises(ContractError, match='packet changed'):
        panel.validate(tmp_path, sha256_json({'original': True}))


def test_failed_or_slow_validation_cannot_be_frozen(tmp_path, monkeypatch):
    from patchloop.util import sha256_bytes

    monkeypatch.setattr(panel, 'runtime_content_hash', lambda: 'runtime')
    for content, expected in [
        ('<testsuites><testsuite tests="1" failures="1" time="1"/></testsuites>', 'failed'),
        ('<testsuites><testsuite tests="1" failures="0" time="120"/></testsuites>', 'two minutes'),
    ]:
        report = tmp_path / 'test.xml'
        report.write_text(content)
        entry = {'path': str(report), 'hash': sha256_bytes(report.read_bytes())}
        evidence = {'runtime_hash': 'runtime', 'reports': {'focused': entry, 'full': entry,
                    'ruff': entry, 'mock': entry}}
        (tmp_path / 'validation.json').write_text(json.dumps(evidence))
        with pytest.raises(ContractError, match=expected):
            panel.validation_evidence(tmp_path)
