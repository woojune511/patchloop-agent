"""Frozen three-arm fresh-repair comparison; preparation never authorizes dispatch."""

from __future__ import annotations

import argparse
import json
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path
from time import monotonic
from unittest.mock import patch

from diagnostics import probe_recheck_public as public
from diagnostics.positive_verification_panel import REPLACED, require, save, settled
from patchloop import prepared_probe_dependencies as deps
from patchloop.artifacts import ArtifactStore
from patchloop.dev import runner, working_plan
from patchloop.dev.contracts import DevRunRequest
from patchloop.dev.cost import pricing_for_model, usd_to_nanos
from patchloop.dev.state import DevJournal
from patchloop.prepared_source import admission_hash, load_source
from patchloop.repository import WorkspaceManager
from patchloop.runtime import git_commit, repository_root, runtime_content_hash
from patchloop.sandbox.probes import DockerProbeSandbox
from patchloop.util import canonical_json, sha256_bytes, sha256_json

MODEL = 'gpt-5.4-2026-03-05'
ROW_CAP = Decimal('3')
CAP = Decimal('54')
TASKS = {'1733': ('sqlfluff', 18), '1413': ('pydicom', 8), '1694': ('pydicom', 9)}
ORDERS = (('ABC', 'BCA', 'CAB'), ('CBA', 'ACB', 'BAC'))
ORDER = tuple((case, arm, repetition + 1) for repetition, orders in enumerate(ORDERS)
              for case, arms in zip(TASKS, orders, strict=True) for arm in arms)
LIVE = Path('C:/pt/prlive01')
GUIDANCE = '''When the public task gives a concrete expected behavior, derive an independent
expectation from that requirement before interpreting candidate output. Prefer saving one
reusable public-API program with save_program=true before the first edit. Include the repair
case and a nearby preservation case, and observe that their actual inputs activate the intended
conditions. Check required positive output/content, not just absence of the old symptom.
Call the user's project entrypoint rather than only a new helper. Normalize only permitted
differences. Retain output from each case where practical. On changed code, use current-diff
observations to decide whether to revise the patch, revise an invalid test as a new saved
program, or submit. Program authorship and expectations remain unverified; setup failure and
normal process exit do not establish behavior correctness. This adds no mandatory annotation
or submission gate. Plans remain model-authored working data, not proof of correctness.'''


@contextmanager
def instructions(arm):
    require(arm in 'ABC' and len(arm) == 1, 'unknown arm')
    original = working_plan.instructions
    require(original('brief-v1').count(REPLACED) == 1, 'baseline guidance changed')

    def selected(policy='brief-v1'):
        value = original(policy)
        return value.replace(REPLACED, GUIDANCE) if policy == 'brief-v1' else value

    if arm == 'A':
        yield
    else:
        with patch.object(working_plan, 'instructions', selected):
            yield


def request(case, arm, state_root):
    project, index = TASKS[case]
    root = repository_root()
    return DevRunRequest(
        provider='openai', model=MODEL,
        task=root / f'tasks/dev-train/swebench-lite-dev-{project}-{project}-{case}/public.yaml',
        state_root=state_root, env_file=root / '.env', max_cost_usd=ROW_CAP, repeat=1,
        reasoning_effort='xhigh', max_output_tokens=25000, context_policy='segmented-v1',
        segment_boundary_policy='result-or-size-v1', planning_policy='brief-v1',
        enable_probes=True, probe_policy='none' if arm == 'A' else 'cases-v1',
        probe_recheck='saved-program-v1' if arm == 'C' else 'none', repair_recheck=True,
        repair_inspection_policy='protected-v1', completion_cost_policy='per-call-v1',
        prepared_source=Path(f'C:/pt/ld20p01/s/{index}/prepared-source.json'),
        prepared_probe_dependencies=(Path(
            'C:/pt/analyses/lite-probe-support-20261002-v1/dependencies-18/'
            'prepared-probe-dependencies.json') if case == '1733' else None),
    )


def bindings():
    root = repository_root()
    return {name: sha256_bytes((root / name).read_bytes()) for name in (
        'diagnostics/probe_recheck_panel.py', 'diagnostics/probe_recheck_public.py',
        'diagnostics/positive_verification_panel.py', '.agent/probe-recheck.md',
    )}


def environment(req):
    directory, package = runner._resolve_task_file(req.task)
    runner._live_task_is_admitted(directory, package)
    evaluator = runner._live_sandbox_preflight(package)
    _, source = load_source(req.prepared_source, package.public.repository.url,
                            package.public.repository.base_commit,
                            expected_hash=admission_hash(req.prepared_source))
    dependencies = (deps.load_dependencies(req.prepared_probe_dependencies, package.public,
                    deps.admit(req.prepared_probe_dependencies))
                    if req.prepared_probe_dependencies else None)
    sandbox = DockerProbeSandbox(dependencies=dependencies)
    identity = {'probe': sandbox.preflight(), 'evaluator': evaluator.image_identity(),
                'source_hash': admission_hash(req.prepared_source)}
    return package, source, sandbox, identity


def execute_public(root, journal, sandbox, workspace, spec, label):
    journal.append('public_program_started', {'label': label, 'spec_hash': sha256_json(spec)})
    result = sandbox.run_probe(workspace, 'Observe the public task behavior and preservation case.',
                               spec['program'], deadline=None,
                               execution_identity={'run_id': journal.run_id, 'action_id': label})
    record = {'label': label, 'result': result, 'assessment': public.classify(result, spec)}
    journal.append('public_program_finished', {
        'label': label, 'artifact': ArtifactStore(root).put_json(record).model_dump(mode='json')})
    require(not result.get('cleanup_failed') and not result.get('timed_out'),
            'public execution uncertainty; stop')
    return record


def prepare(root):
    require(not root.exists() and not root.resolve().is_relative_to(repository_root()),
            'fresh external preparation root required')
    root.mkdir(parents=True)
    journal = DevJournal(root, 'run_dev_proberecheckprepare')
    journal.append('preparation_started', {'provider_calls': 0, 'implementation': bindings()})
    cases = {}
    for case in TASKS:
        req = request(case, 'A', LIVE / 'unused')
        package, source, sandbox, identity = environment(req)
        spec = public.design(case, package.public.issue.description)
        record = execute_public(root, journal, sandbox, source, spec, f'base{case}')
        require(record['assessment']['status'] == 'FAIL', 'base defect must be reproduced')
        cases[case] = {'spec': spec, 'base': record, 'environment': identity,
                       'task_hash': package.task_content_hash}
    save(root, 'preparation.json', cases)
    journal.append('preparation_finished', {'hash': sha256_json(cases), 'provider_calls': 0})
    return cases


def pricing_identity():
    pricing = pricing_for_model(MODEL)
    return {key: str(getattr(pricing, key)) for key in (
        'input_per_million_usd', 'cached_input_per_million_usd', 'output_per_million_usd')}


def controls(root):
    """Recheck public controls on saved agent submissions, never on reference patches."""
    prepared = json.loads((root / 'preparation.json').read_bytes())
    journal = DevJournal(root, 'run_dev_proberecheckcontrols')
    require(not journal.events(), 'controls already started; inspect receipts')
    roster = (
        ('1733', Path('C:/pt/pv1live01/1733B1'), 'run_dev_ee5f0eca9f634e7a', 'PASS'),
        ('1413', Path('C:/pt/ld20live01/8'), 'run_dev_24ac4f435fd04df4', 'FAIL'),
        ('1694', Path('C:/pt/ld20live01/9'), 'run_dev_143c3df7822d42f4', 'PASS'),
    )
    results = []
    for case, state, run_id, expected in roster:
        old = DevJournal(state, run_id)
        terminal = next(e['payload'] for e in reversed(old.events())
                        if e['event_type'] == 'terminal')
        submitted = terminal['artifact_hashes']['submitted_patch']
        workspace = state / 'workspaces' / run_id / 'repo'
        before = WorkspaceManager.diff_summary(workspace)
        require(before.patch_hash == submitted and not before.untracked_files,
                'control diff changed')
        _, _, sandbox, identity = environment(request(case, 'A', LIVE / 'unused'))
        require(identity == prepared[case]['environment'], 'control environment changed')
        record = execute_public(root, journal, sandbox, workspace, prepared[case]['spec'],
                                f'control{case}')
        require(record['assessment']['status'] == expected, 'public control disagrees')
        results.append({'case': case, 'run_id': run_id, 'patch_hash': submitted, 'record': record})
        if case == '1413':
            source = '''import io,json
from pydicom.dataset import Dataset
from pydicom.dataelem import DataElement
from pydicom.filebase import DicomBytesIO
from pydicom.filewriter import write_OLvalue, writers
fp=DicomBytesIO(); fp.is_little_endian=True; fp.is_implicit_VR=False
write_OLvalue(fp,DataElement(0x00660040,'OL',[1,2,3]))
row={'helper_bytes':len(fp.getvalue()), 'registered_writer':writers['OL'][0].__name__}
ds=Dataset(); ds.is_little_endian=True; ds.is_implicit_VR=False
ds.add_new(0x00660040,'OL',[1,2,3])
try: ds.save_as(io.BytesIO()); row['public_saved']=True
except Exception as exc: row.update(public_saved=False,error=type(exc).__name__)
print(json.dumps(row))
'''
            journal.append('entrypoint_control_started', {
                'source_hash': sha256_bytes(source.encode())})
            receipt = sandbox.run_probe(workspace, 'Compare helper-only and public save execution.',
                source, deadline=None, execution_identity={
                    'run_id': journal.run_id, 'action_id': 'entrypoint1413'})
            journal.append('entrypoint_control_finished', {
                'artifact': ArtifactStore(root).put_json(receipt).model_dump(mode='json')})
            require(receipt['exit_code'] == 0 and not any(receipt.get(k) for k in (
                'cleanup_failed', 'timed_out', 'truncated')), 'entrypoint control execution failed')
            observed = json.loads(receipt['stdout'])
            require(observed == {'helper_bytes': 12, 'registered_writer': 'write_OWvalue',
                                  'public_saved': False, 'error': 'TypeError'},
                    'entrypoint control changed')
            results[-1]['entrypoint_control'] = receipt
        require(WorkspaceManager.diff_summary(workspace) == before, 'control changed workspace')
    save(root, 'controls.json', results)
    return results


def freeze(root):
    prepared = json.loads((root / 'preparation.json').read_bytes())
    control_results = json.loads((root / 'controls.json').read_bytes())
    require([r['case'] for r in control_results] == list(TASKS), 'controls required')
    require(set(prepared) == set(TASKS), 'task roster changed')
    validation = validation_evidence(root)
    rows = {}
    for case in TASKS:
        for arm in 'ABC':
            req = request(case, arm, LIVE / 'unused')
            directory, package = runner._resolve_task_file(req.task)
            runner._live_source_preflight(directory, package)
            require(package.task_content_hash == prepared[case]['task_hash'], 'task changed')
            require(public.design(case, package.public.issue.description) == prepared[case]['spec'],
                    'public program changed; new preparation required')
            with instructions(arm):
                model_hash = runner._model_hash(req, pricing_for_model(MODEL))
            rows[case + arm] = {'request': req.model_dump(mode='json'), 'model_hash': model_hash,
                'external': {str(p): sha256_bytes(p.read_bytes()) for p in (
                    req.prepared_source, req.prepared_probe_dependencies) if p is not None}}
    runner._require_tracked_clean_paths(repository_root(), list(bindings()))
    packet = {'schema': 'probe-recheck-panel-v1', 'official': False, 'claim_eligible': False,
              'head': git_commit(), 'runtime_hash': runtime_content_hash(),
              'implementation': bindings(), 'preparation_hash': sha256_json(prepared),
              'controls_hash': sha256_json(control_results),
              'validation_hash': sha256_json(validation),
              'rows': rows, 'order': ORDER, 'cap_usd': str(CAP), 'row_cap_usd': str(ROW_CAP),
              'model': MODEL, 'pricing': pricing_identity(), 'guidance': GUIDANCE,
              'credential': str((repository_root() / '.env').resolve()), 'live_root': str(LIVE),
              'approval': 'PENDING_EXACT_HUMAN_SCOPE'}
    save(root, 'packet.json', packet)
    digest = sha256_json(packet)
    DevJournal(root, 'run_dev_proberecheckpanel').append('panel_prepared', {'packet_hash': digest})
    return digest


def validation_evidence(root):
    from xml.etree import ElementTree

    evidence = json.loads((root / 'validation.json').read_bytes())
    require(evidence['runtime_hash'] == runtime_content_hash(), 'validation runtime changed')
    require(set(evidence['reports']) == {'focused', 'full', 'ruff', 'mock'},
            'focused/full/Ruff/mock validation required')
    for kind, entry in evidence['reports'].items():
        raw = Path(entry['path']).read_bytes()
        require(sha256_bytes(raw) == entry['hash'], 'validation report changed')
        if kind in {'focused', 'full'}:
            tree = ElementTree.fromstring(raw)
            suites = list(tree.iter('testsuite'))
            require(bool(suites) and all(int(s.get('failures', '0')) == 0
                                        and int(s.get('errors', '0')) == 0 for s in suites),
                    'test validation failed')
            require(sum(int(s.get('tests', '0')) for s in suites) > 0, 'empty test report')
            if kind == 'focused':
                require(sum(float(s.get('time', '0')) for s in suites) < 120,
                        'focused validation must stay under two minutes')
        elif kind == 'ruff':
            require(json.loads(raw)['exit_code'] == 0, 'Ruff failed')
        else:
            result = json.loads(raw)
            require(result['completed_repetitions'] == 1
                    and result['runs'][0]['terminal'] == 'EVALUATOR_PASS', 'mock smoke failed')
    return evidence


def validate(root, packet_hash):
    packet = json.loads((root / 'packet.json').read_bytes())
    prepared = json.loads((root / 'preparation.json').read_bytes())
    require(sha256_json(packet) == packet_hash, 'packet changed')
    require(packet['head'] == git_commit() and packet['runtime_hash'] == runtime_content_hash()
            and packet['implementation'] == bindings(), 'implementation changed')
    require(packet['preparation_hash'] == sha256_json(prepared), 'preparation changed')
    require(packet['validation_hash'] == sha256_json(validation_evidence(root)),
            'validation evidence changed')
    require(packet['controls_hash'] == sha256_json(
        json.loads((root / 'controls.json').read_bytes())),
            'controls changed')
    require(packet['order'] == [list(row) for row in ORDER] and packet['cap_usd'] == str(CAP)
            and packet['row_cap_usd'] == str(ROW_CAP) and packet['guidance'] == GUIDANCE
            and packet['pricing'] == pricing_identity() and packet['model'] == MODEL
            and packet['live_root'] == str(LIVE), 'scope changed')
    for case in TASKS:
        for arm in 'ABC':
            row = packet['rows'][case + arm]
            req = request(case, arm, LIVE / 'unused')
            require(req.model_dump(mode='json') == row['request'], 'request changed')
            directory, package = runner._resolve_task_file(req.task)
            runner._live_source_preflight(directory, package)
            require(package.task_content_hash == prepared[case]['task_hash'], 'task changed')
            require(public.design(case, package.public.issue.description) == prepared[case]['spec'],
                    'public program changed; new preparation required')
            for path, digest in row['external'].items():
                require(sha256_bytes(Path(path).read_bytes()) == digest, 'prepared input changed')
            with instructions(arm):
                require(runner._model_hash(req, pricing_for_model(MODEL)) == row['model_hash'],
                        'model identity changed')
    return packet


def preflight(root, packet_hash):
    validate(root, packet_hash)
    require(not LIVE.exists(), 'live root exists; no restart')
    prepared = json.loads((root / 'preparation.json').read_bytes())
    identities = {}
    for case in TASKS:
        _, _, _, identity = environment(request(case, 'A', LIVE / 'unused'))
        require(identity == prepared[case]['environment'], 'tested environment changed')
        identities[case] = identity
    save(root, 'preflight.json', identities)
    DevJournal(root, 'run_dev_proberecheckpanel').append('preflight_passed', {
        'packet_hash': packet_hash, 'receipt_hash': sha256_json(identities), 'provider_calls': 0})
    return identities


def run(root, packet_hash):
    return run_fresh_rows(
        root, packet_hash, validate_packet=validate, order=ORDER, live_root=LIVE,
        request_for=request, instruction_scope=instructions, row_cap=ROW_CAP,
        total_cap=CAP, journal_id='run_dev_proberecheckpanel',
    )


def run_fresh_rows(root, packet_hash, *, validate_packet, order, live_root, request_for,
                   instruction_scope, row_cap, total_cap, journal_id, after_row=None):
    """Shared bounded fresh-run driver; all inputs remain manifest-bound by caller."""
    validate_packet(root, packet_hash)
    approval = json.loads((root / 'authorization.json').read_bytes())
    require(approval.get('approved') is True and bool(approval.get('human_message'))
            and approval.get('packet_hash') == packet_hash, 'exact human scope approval required')
    journal = DevJournal(root, journal_id)
    with journal.execution_lock():
        events = journal.events()
        require(not any(e['event_type'] == 'panel_started' for e in events), 'no restart or resume')
        receipt = json.loads((root / 'preflight.json').read_bytes())
        require(any(e['event_type'] == 'preflight_passed'
                    and e['payload']['packet_hash'] == packet_hash
                    and e['payload']['receipt_hash'] == sha256_json(receipt) for e in events),
                'preflight required')
        require(not live_root.exists(), 'live root exists; no replacement')
        live_root.mkdir(parents=True)
        journal.append('panel_started', {'packet_hash': packet_hash,
                                         'authorization_hash': sha256_json(approval)})
        rows, spent = [], 0
        try:
            for case, arm, repetition in order:
                validate_packet(root, packet_hash)
                require(spent + usd_to_nanos(row_cap) <= usd_to_nanos(total_cap),
                        'panel cap exhausted')
                label = f'{case}{arm}{repetition}'
                req = request_for(case, arm, live_root / label)
                require(not req.state_root.exists(), 'row exists; no retry')
                journal.append('row_started', {'label': label,
                                               'request': req.model_dump(mode='json')})
                started = monotonic()
                with instruction_scope(arm):
                    result = runner.run_dev(req)
                cost = result['cost_nanos']
                spent += cost
                known = settled(result, req.state_root)
                within_cap = 0 <= cost <= usd_to_nanos(row_cap) and spent <= usd_to_nanos(total_cap)
                row = {'label': label, 'case': case, 'arm': arm, 'repetition': repetition,
                       'result': result, 'settled': known, 'within_cap': within_cap,
                       'elapsed_seconds': round(monotonic() - started, 3)}
                rows.append(row)
                journal.append('row_finished', row)
                print(canonical_json({'finished': label, 'settled': known, 'cost_nanos': cost}),
                      flush=True)
                if not known or not within_cap:
                    break
                if after_row is not None:
                    row['assessment'] = after_row(row, req)
                    journal.append('row_assessed', {'label': label,
                                                    'assessment': row['assessment']})
                    if not row['assessment']['ok']:
                        break
        except BaseException as error:
            journal.append('panel_interrupted', {'error_type': type(error).__name__,
                                                 'completed': len(rows), 'resume_allowed': False})
            raise
        outcome = {'rows': rows, 'completed': len(rows), 'planned': len(order),
                   'not_run': [f'{c}{a}{r}' for c, a, r in order[len(rows):]],
                   'recorded_cost_nanos': spent, 'official': False, 'claim_eligible': False,
                   'allocation': 'CLOSED', 'resume_allowed': False}
        save(root, 'result.json', outcome)
        journal.append('panel_closed', {'result_hash': sha256_json(outcome)})
        return outcome


def assess(root, packet_hash):
    validate(root, packet_hash)
    prepared = json.loads((root / 'preparation.json').read_bytes())
    outcome = json.loads((root / 'result.json').read_bytes())
    journal = DevJournal(root, 'run_dev_proberecheckassessment')
    require(not journal.events(), 'assessment already started; inspect immutable receipts')
    results = []
    for row in outcome['rows']:
        run_result = row['result']['runs'][0]
        submitted = run_result.get('artifact_hashes', {}).get('submitted_patch')
        if submitted is None:
            results.append({'label': row['label'], 'assessment': {'status': 'NOT_RUN'}})
            continue
        req = request(row['case'], row['arm'], LIVE / row['label'])
        _, _, sandbox, _ = environment(req)
        workspace = req.state_root / 'workspaces' / run_result['run_id'] / 'repo'
        before = WorkspaceManager.diff_summary(workspace)
        require(before.patch_hash == submitted and not before.untracked_files,
                'submitted diff changed')
        results.append(execute_public(root, journal, sandbox, workspace,
                       prepared[row['case']]['spec'], row['label']))
        require(WorkspaceManager.diff_summary(workspace)
                == before, 'assessment changed submitted workspace')
    save(root, 'public-final.json', results)
    return results


def decide(rows, *, mechanism_supported, contracts_passed):
    require(len(rows) == 18 and {r['label'] for r in rows}
            == {f'{c}{a}{n}' for c, a, n in ORDER}, 'complete exact panel required')
    accepted = {r['label']: r['result']['runs'][0]['terminal'] == 'EVALUATOR_PASS' for r in rows}
    totals = {a: sum(accepted[r['label']] for r in rows if r['arm'] == a) for a in 'ABC'}
    repeated = all(
        sum(accepted[f'{c}C{n}'] for c in TASKS) > sum(accepted[f'{c}A{n}'] for c in TASKS)
        and sum(accepted[f'{c}C{n}'] for c in TASKS) >= sum(accepted[f'{c}B{n}'] for c in TASKS)
        for n in (1, 2))
    no_loss = all(not (accepted[f'{c}A{n}'] or accepted[f'{c}B{n}']) or accepted[f'{c}C{n}']
                  for c in TASKS for n in (1, 2))
    costs = {a: sum(r['result']['cost_nanos'] for r in rows if r['arm'] == a) for a in 'ABC'}
    times = {a: sum(Decimal(str(r['elapsed_seconds'])) for r in rows if r['arm'] == a)
             for a in 'ABC'}
    overhead = costs['C'] * 4 <= costs['A'] * 5 and times['C'] * 4 <= times['A'] * 5
    checks = {'repetition_gain': repeated, 'incremental_gain': totals['C'] > totals['B'],
              'no_success_lost': no_loss, 'overhead_within_25_percent': overhead,
              'mechanism_supported': mechanism_supported, 'contracts_passed': contracts_passed,
              'all_settled': all(r['settled'] and r['within_cap'] for r in rows)}
    decision = 'SELECT_FOR_EXPOSED_TASK_GROUP' if all(checks.values()) else 'KEEP_BASELINE'
    return {'decision': decision,
            'checks': checks, 'accepted': totals, 'generalization_claim': False,
            'default_change': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',
                        choices=['prepare', 'controls', 'freeze', 'preflight', 'run', 'assess'])
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--packet-hash')
    args = parser.parse_args()
    if args.action in {'prepare', 'controls', 'freeze'}:
        result = globals()[args.action](args.root)
    else:
        result = globals()[args.action](args.root, args.packet_hash)
    print(canonical_json(result))
