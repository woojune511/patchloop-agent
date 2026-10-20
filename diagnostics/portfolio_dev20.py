"""Frozen dev20 remeasurement using the existing solver and native evaluator."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
from collections import Counter
from contextlib import nullcontext
from decimal import Decimal
from pathlib import Path
from time import monotonic

from diagnostics import probe_recheck_panel as driver
from diagnostics.positive_verification_panel import require, save
from patchloop.artifacts import ArtifactStore
from patchloop.dev import runner
from patchloop.dev.contracts import DevLimits, DevRunRequest
from patchloop.dev.cost import pricing_for_model
from patchloop.dev.state import DevJournal
from patchloop.prepared_source import admission_hash
from patchloop.runtime import git_commit, repository_root, runtime_content_hash
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json, sha256_bytes, sha256_json

BASELINE = Path('C:/pt/analyses/lite-dev20-registration-20261002-v1')
BASELINE_HASHES = {
    'manifest.json': 'sha256:5ab8b340aedc739e290c4000a9dbb34a6e11288c4d8442ac6c3e201416122328',
    'summary.json': 'sha256:647846ac463d7cf090395de6c37aa282b413a7debf6c12c6eaa1ae3491be7fa0',
    'preflight.json': 'sha256:dc6c987a71f9b6e497368a1b2b9509b2054469dffe9e91ac93a166b1668f4b64',
}
NATIVE_PYTHON = Path('C:/pt/analyses/swebench-lite-dev-preparation-20261002-v1/'
                     'harness-venv/Scripts/python.exe')
MODEL = 'gpt-5.4-mini-2026-03-17'
HARNESS_REVISION = '02e7a74ffd0b707aab73d203fe87bdc7c76afc8e'
ROW_CAP, CAP = Decimal('1.20'), Decimal('24.00')
JOURNAL = 'run_dev_portfoliodev20'
FROZEN_TASK = 'tasks/dev-train/portfolio-dev20/sqlfluff-1625/public.yaml'


def baseline():
    data = {}
    for name, digest in BASELINE_HASHES.items():
        raw = (BASELINE / name).read_bytes()
        require(sha256_bytes(raw) == digest, 'historical input changed')
        data[name] = json.loads(raw)
    return data['manifest.json'], data['summary.json']


def request(entry, state_root):
    relative = ('tasks/dev-train/swebench-lite-dev-'
                + entry['instance_id'].replace('__', '-') + '/public.yaml')
    if entry['instance_id'] == 'sqlfluff__sqlfluff-1625':
        relative = FROZEN_TASK
    return DevRunRequest(
        provider='openai', task=repository_root() / relative, model=MODEL,
        state_root=state_root, env_file=repository_root() / '.env', repeat=1,
        max_cost_usd=ROW_CAP, reasoning_effort='xhigh', max_output_tokens=25000,
        context_policy='segmented-v1', segment_boundary_policy='result-or-size-v1',
        planning_policy='brief-v1', enable_probes=True, probe_policy='none',
        probe_recheck='none', repair_recheck=True, repair_inspection_policy='protected-v1',
        completion_cost_policy='per-call-v1', prepared_source=Path(entry['prepared_source']),
        prepared_probe_dependencies=None,
        limits=DevLimits(max_model_calls=40, max_tool_actions=100,
                         max_accepted_mutations=4, wall_time_seconds=1800),
    )


def bindings():
    names = ('diagnostics/portfolio_dev20.py', 'diagnostics/probe_recheck_panel.py',
             'diagnostics/positive_verification_panel.py', 'diagnostics/swebench_lite_native.py',
             '.agent/portfolio-v1.md')
    return {n: sha256_bytes((repository_root() / n).read_bytes()) for n in names}


def price():
    p = pricing_for_model(MODEL)
    return {n: str(getattr(p, n)) for n in (
        'input_per_million_usd', 'cached_input_per_million_usd', 'output_per_million_usd')}


def native_env():
    # Neither the credential file nor arbitrary host secrets enter evaluation.
    allowed = {'PATH', 'SYSTEMROOT', 'WINDIR', 'COMSPEC', 'TEMP', 'TMP', 'PATHEXT'}
    env = {k: v for k, v in os.environ.items() if k.upper() in allowed}
    return {**env, 'PYTHON_DOTENV_DISABLED': '1', 'PYTHONUTF8': '1'}


def native_identity():
    script = (
        "import hashlib,json,pathlib,swebench,importlib.metadata as m; "
        "r=pathlib.Path(swebench.__file__).parent; "
        "print(json.dumps({'origin':json.loads(m.distribution('swebench')"
        ".read_text('direct_url.json')), 'files':{p.relative_to(r).as_posix():"
        "hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(r.rglob('*.py'))}}))"
    )
    result = subprocess.run([str(NATIVE_PYTHON), '-c', script], check=True,
                            capture_output=True, timeout=30, env=native_env())
    identity = json.loads(result.stdout)
    require(identity['origin']['vcs_info']['commit_id'] == HARNESS_REVISION,
            'historical native harness revision changed')
    return {'python_hash': sha256_bytes(NATIVE_PYTHON.read_bytes()),
            'harness_revision': HARNESS_REVISION,
            'harness_files_hash': sha256_json(identity['files'])}


def verify_entry(entry, req, *, tracked=True):
    old = json.loads((BASELINE / 'preflight.json').read_bytes())['rows'][entry['index'] - 1]
    before = {k: v for k, v in old['request'].items() if k not in ('task', 'state_root')}
    after = {k: v for k, v in req.model_dump(mode='json').items()
             if k not in ('task', 'state_root')}
    require(before == after, 'historical request settings changed')
    for name, expected in entry['files'].items():
        require(sha256_bytes((req.task.parent / name).read_bytes()) == expected,
                f"historical task bytes differ: {entry['instance_id']}/{name}")
    package = load_task_package(req.task.parent)
    require(package.task_content_hash == entry['task_hash'], 'historical package changed')
    require(package.environment.image_digest == entry['image_digest'], 'image identity changed')
    require(admission_hash(req.prepared_source) == entry['source_hash'], 'source hash changed')
    require(sha256_bytes(Path(entry['native_row']).read_bytes()) == entry['native_row_hash'],
            'native row changed')
    if tracked:
        runner._live_source_preflight(req.task.parent, package)
    return package


def freeze(root, live):
    require(root.is_dir() and not (root / 'manifest.json').exists(), 'fresh packet required')
    require(not live.exists(), 'fresh live root required')
    repo = repository_root().resolve()
    require(not root.resolve().is_relative_to(repo) and not live.resolve().is_relative_to(repo),
            'generated state must be external')
    require(not root.resolve().is_relative_to(live.resolve())
            and not live.resolve().is_relative_to(root.resolve()), 'separate state roots required')
    evidence = driver.validation_evidence(root)
    old, history = baseline()
    runner._require_tracked_clean_paths(repo, list(bindings()))
    rows = []
    for entry in old['rows']:
        req = request(entry, live / str(entry['index']))
        verify_entry(entry, req)
        rows.append({'instance_id': entry['instance_id'], 'index': entry['index'],
                     'request': req.model_dump(mode='json'),
                     'model_hash': runner._model_hash(req, pricing_for_model(MODEL)),
                     'prepared_hash': sha256_bytes(req.prepared_source.read_bytes())})
    packet = {
        'schema': 'portfolio-dev20-v1', 'head': git_commit(),
        'runtime_hash': runtime_content_hash(),
        'implementation': bindings(), 'historical_hashes': BASELINE_HASHES,
        'historical_head': history['head'], 'historical_resolved': 10,
        'rows': rows, 'live_root': str(live.resolve()), 'model': MODEL, 'pricing': price(),
        'row_cap_usd': str(ROW_CAP), 'total_cap_usd': str(CAP),
        'native_identity': native_identity(), 'validation_hash': sha256_json(evidence),
        'official': False, 'claim_eligible': False, 'approval': 'PENDING_EXACT_HUMAN_SCOPE',
        'advance': '20 complete agreeing evaluations and >=11 resolved; preparation only',
        'automatic_retry_resume_replacement': False,
    }
    save(root, 'manifest.json', packet)
    save(root, 'result-format.json', aggregate([], history))
    digest = sha256_json(packet)
    DevJournal(root, JOURNAL).append('panel_prepared', {'packet_hash': digest, 'provider_calls': 0})
    return digest


def validate(root, digest):
    packet = json.loads((root / 'manifest.json').read_bytes())
    require(sha256_json(packet) == digest, 'manifest changed')
    require(packet['head'] == git_commit() and packet['runtime_hash'] == runtime_content_hash()
            and packet['implementation'] == bindings(), 'implementation changed')
    require(packet['pricing'] == price() and packet['model'] == MODEL
            and packet['row_cap_usd'] == str(ROW_CAP) and packet['total_cap_usd'] == str(CAP),
            'scope changed')
    require(packet['validation_hash'] == sha256_json(driver.validation_evidence(root)),
            'validation changed')
    require(packet['native_identity'] == native_identity(), 'native harness changed')
    old, _ = baseline()
    require(len(packet['rows']) == len(old['rows']) == 20, 'exact roster required')
    for entry, row in zip(old['rows'], packet['rows'], strict=True):
        req = request(entry, Path(packet['live_root']) / str(entry['index']))
        require(row['instance_id'] == entry['instance_id']
                and row['request'] == req.model_dump(mode='json'), 'request changed')
        require(row['model_hash'] == runner._model_hash(req, pricing_for_model(MODEL)),
                'model input identity changed')
        require(row['prepared_hash'] == sha256_bytes(req.prepared_source.read_bytes()),
                'prepared descriptor changed')
        verify_entry(entry, req)
    return packet


def preflight(root, digest):
    packet = validate(root, digest)
    require(not Path(packet['live_root']).exists(), 'no restart or replacement')
    identities = {}
    for row in packet['rows']:
        req = DevRunRequest.model_validate(row['request'])
        *_, identity = driver.environment(req)
        identities[row['instance_id']] = identity
    receipt = {'packet_hash': digest, 'provider_calls': 0, 'environments': identities}
    save(root, 'preflight.json', receipt)
    DevJournal(root, JOURNAL).append('preflight_passed', {
        'packet_hash': digest, 'receipt_hash': sha256_json(receipt)})
    return receipt


def native_assessment(root, entry, row, req, *, evaluation_patch=None):
    run = row['result']['runs'][0]
    patch_hash = run.get('artifact_hashes', {}).get('submitted_patch')
    if not patch_hash:
        return {'ok': True, 'status': 'NOT_RUN', 'reason': 'unsubmitted', 'elapsed_seconds': 0}
    folder = root / 'native' / str(entry['index'])
    folder.mkdir(parents=True, exist_ok=False)
    digest = patch_hash.removeprefix('sha256:')
    patch = (req.state_root / 'artifacts/objects/sha256' / digest[:2] / digest[2:]).read_bytes()
    require(sha256_bytes(patch) == patch_hash, 'submitted patch changed')
    (folder / 'submitted.patch').write_bytes(patch)
    assessed_patch = patch if evaluation_patch is None else evaluation_patch
    if evaluation_patch is not None:
        (folder / 'source-only.patch').write_bytes(assessed_patch)
    prediction = {'instance_id': entry['instance_id'], 'model_name_or_path': req.model,
                  'model_patch': assessed_patch.decode('utf-8')}
    save(folder, 'prediction.jsonl', prediction)
    started = monotonic()
    error = None
    try:
        with (folder / 'native.log').open('xb') as log:
            completed = subprocess.run([
                str(NATIVE_PYTHON), '-X', 'utf8', '-m', 'diagnostics.swebench_lite_native',
                '--rows', entry['native_row'], '--output', str(folder / 'output'),
                '--predictions', str(folder / 'prediction.jsonl'),
            ], cwd=repository_root(), env=native_env(), stdout=log, stderr=subprocess.STDOUT,
                timeout=600, check=False)
        code = completed.returncode
    except (OSError, subprocess.TimeoutExpired) as exc:
        code, error = None, type(exc).__name__
    controls = [json.loads(p.read_bytes()) for p in (folder / 'output').glob('control-*.json')]
    cleanup_path = folder / 'output/cleanup.json'
    cleanup = json.loads(cleanup_path.read_bytes()) if cleanup_path.exists() else None
    ok = (code == 0 and cleanup is not None and not cleanup['remaining']
          and len(controls) == 1 and controls[0]['instance_id'] == entry['instance_id']
          and controls[0]['complete'] and controls[0]['missing_count'] == 0
          and type(controls[0]['resolved']) is bool)
    status = ('PASS' if controls[0]['resolved'] else 'FAIL') if ok else 'ERROR'
    agreement = ok and status == (run.get('evaluator') or {}).get('task_acceptance')
    files = {p.relative_to(folder).as_posix(): sha256_bytes(p.read_bytes())
             for p in folder.rglob('*') if p.is_file()}
    result = {'ok': bool(ok and agreement), 'status': status, 'agreement': bool(agreement),
              'cleanup_confirmed': cleanup is not None and not cleanup['remaining'],
              'exit_code': code, 'error_type': error, 'patch_hash': patch_hash,
              'files': files, 'elapsed_seconds': round(monotonic() - started, 3)}
    if evaluation_patch is not None:
        result['evaluation_patch_hash'] = sha256_bytes(assessed_patch)
        result['test_projection'] = 'registered-additive-test-roots-omitted'
    save(folder, 'assessment.json', result)
    artifact = ArtifactStore(root).put_json(result)
    DevJournal(root, JOURNAL).append('native_evaluated', {
        'instance_id': entry['instance_id'], 'receipt': artifact.model_dump(mode='json')})
    return result


def aggregate(rows, history):
    expected = history['rows']
    require([r['case'] for r in rows] == [r['instance_id'] for r in expected[:len(rows)]],
            'rows must be unique and in frozen order')
    records = []
    for index, old in enumerate(expected):
        previous = 'PASS' if old['original_resolved'] else 'FAIL'
        record = {'instance_id': old['instance_id'], 'historical_acceptance': previous,
                  'historical_cost_nanos': old['cost_nanos'],
                  'historical_elapsed_seconds': old['elapsed_seconds'], 'started': False,
                  'submitted': False, 'registered': 'NOT_RUN', 'native': 'NOT_RUN',
                  'transition': None, 'terminal': 'NOT_STARTED', 'billing_known': None,
                  'cost_nanos': None, 'solve_seconds': None, 'native_seconds': None}
        if index < len(rows):
            row = rows[index]
            result = row['result']
            require(len(result['runs']) == 1, 'one run required')
            run = result['runs'][0]
            assessment = row.get('assessment') or {}
            registered = (run.get('evaluator') or {}).get('task_acceptance', 'NOT_RUN')
            native = assessment.get('status', 'NOT_RUN')
            record.update(started=True, submitted=bool(
                run.get('artifact_hashes', {}).get('submitted_patch')), terminal=run['terminal'],
                registered=registered, native=native,
                transition=f'{previous}->{native}' if assessment.get('ok')
                and assessment.get('agreement') and native in ('PASS', 'FAIL') else None,
                billing_known=row['settled'] and row['within_cap'],
                cost_nanos=result['cost_nanos'], solve_seconds=row['elapsed_seconds'],
                native_seconds=assessment.get('elapsed_seconds'),
                run_id=run.get('run_id'), artifact_hashes=run.get('artifact_hashes', {}),
                safety=(run.get('evaluator') or {}).get('safety_state', 'NOT_RUN'))
        records.append(record)
    valid = len(rows) == 20 and all(r['billing_known'] and r['transition']
                                  and r['safety'] == 'PASS' for r in records)
    resolved = sum(r['native'] == 'PASS' and r['transition'] is not None for r in records)
    return {'schema': 'portfolio-dev20-results-v1', 'official': False, 'claim_eligible': False,
            'rows': records, 'planned': 20, 'started': len(rows),
            'not_started': 20 - len(rows), 'submitted': sum(r['submitted'] for r in records),
            'unsubmitted': sum(r['started'] and not r['submitted'] for r in records),
            'resolved': resolved, 'historical_resolved': 10,
            'transitions': dict(Counter(r['transition'] for r in records if r['transition'])),
            'recorded_cost_nanos': sum(r['cost_nanos'] or 0 for r in records),
            'billing_known': all(r['settled'] and r['within_cap'] for r in rows),
            'solve_seconds': round(sum(r['solve_seconds'] or 0 for r in records), 3),
            'native_seconds': round(sum(r['native_seconds'] or 0 for r in records), 3),
            'complete_agreeing_evaluation': bool(valid),
            'decision': ('PREPARE_TEST300_NOT_AUTHORIZED_TO_RUN' if valid and resolved >= 11
                         else 'CLOSE_WITH_DOCUMENTATION' if valid else 'INCOMPLETE_NO_ADVANCE'),
            'automatic_followup': False}


def run(root, digest):
    packet = validate(root, digest)
    old, history = baseline()
    by_id = {r['instance_id']: r for r in old['rows']}
    live = Path(packet['live_root'])

    def make_request(case, arm, _state):
        entry = by_id[case]
        return request(entry, live / str(entry['index']))

    def assess(row, req):
        require(packet['native_identity'] == native_identity(), 'native harness changed')
        run_result = row['result']['runs'][0]
        events = DevJournal(req.state_root, run_result['run_id']).events()
        usage = [e['payload'] for e in events if e['event_type'] == 'provider_call_finished']
        require(len(usage) == len({u['call_id'] for u in usage})
                == run_result['call_counts']['model'], 'provider call accounting mismatch')
        require(sum(u['cost_nanos'] for u in usage) == row['result']['cost_nanos'],
                'settled cost accounting mismatch')
        return native_assessment(root, by_id[row['case']], row, req)

    outcome = driver.run_fresh_rows(
        root, digest, validate_packet=validate,
        order=tuple((r['instance_id'], 'current', 1) for r in old['rows']), live_root=live,
        request_for=make_request, instruction_scope=lambda _: nullcontext(),
        row_cap=ROW_CAP, total_cap=CAP, journal_id=JOURNAL,
        after_row=assess)
    summary = aggregate(outcome['rows'], history)
    save(root, 'summary.json', summary)
    DevJournal(root, JOURNAL).append('panel_summarized', {'summary_hash': sha256_json(summary)})
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['freeze', 'preflight', 'run'])
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--live-root', type=Path)
    parser.add_argument('--packet-hash')
    args = parser.parse_args()
    if args.command == 'freeze':
        require(args.live_root is not None, '--live-root required')
        value = freeze(args.root.resolve(), args.live_root.resolve())
    else:
        require(bool(args.packet_hash), '--packet-hash required')
        value = globals()[args.command](args.root.resolve(), args.packet_hash)
    print(canonical_json(value))


if __name__ == '__main__':
    main()
