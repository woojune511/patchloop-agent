"""Offline preparation and bounded mini/full comparison of the unchanged agent."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from contextlib import nullcontext
from decimal import Decimal
from pathlib import Path

from diagnostics import probe_recheck_panel as driver
from diagnostics.positive_verification_panel import require, save
from patchloop.dev import runner
from patchloop.dev.contracts import DevRunRequest
from patchloop.dev.cost import pricing_for_model
from patchloop.dev.state import DevJournal
from patchloop.runtime import git_commit, repository_root, runtime_content_hash
from patchloop.util import canonical_json, sha256_bytes, sha256_json

MODELS = {'mini': 'gpt-5.4-mini-2026-03-17', 'full': 'gpt-5.4-2026-03-05'}
# Historical outcomes only stratify selection. They never enter requests or scoring.
TASKS = {
    'marshmallow1343': (1, 'marshmallow-code-marshmallow-1343', 'PASS'),
    'pydicom1694': (9, 'pydicom-pydicom-1694', 'PASS'),
    'astroid1196': (11, 'pylint-dev-astroid-1196', 'PASS'),
    'pydicom1139': (7, 'pydicom-pydicom-1139', 'FAIL'),
    'astroid1268': (12, 'pylint-dev-astroid-1268', 'FAIL'),
    'sqlfluff1517': (16, 'sqlfluff-sqlfluff-1517', 'FAIL'),
}
ORDER = tuple((case, arm, rep) for rep in (1, 2)
              for index, case in enumerate(TASKS)
              for arm in (('mini', 'full') if (index + rep) % 2 else ('full', 'mini')))
ROW_CAP = Decimal('3')
CAP = Decimal('72')
JOURNAL = 'run_dev_modelcostpanel'
NOTE = '.agent/model-cost-comparison.md'


def request(case, arm, state_root):
    index, task, _ = TASKS[case]
    root = repository_root()
    return DevRunRequest(
        provider='openai', model=MODELS[arm],
        task=root / f'tasks/dev-train/swebench-lite-dev-{task}/public.yaml',
        state_root=state_root, env_file=root / '.env', max_cost_usd=ROW_CAP, repeat=1,
        reasoning_effort='xhigh', max_output_tokens=25000, context_policy='segmented-v1',
        segment_boundary_policy='result-or-size-v1', planning_policy='brief-v1',
        enable_probes=True, probe_policy='none', repair_recheck=True,
        repair_inspection_policy='protected-v1', completion_cost_policy='per-call-v1',
        prepared_source=Path(f'C:/pt/ld20p01/s/{index}/prepared-source.json'),
        prepared_probe_dependencies=(Path(
            'C:/pt/analyses/lite-probe-support-20261002-v1/dependencies-16/'
            'prepared-probe-dependencies.json') if index == 16 else None),
    )


def bindings():
    root = repository_root()
    return {name: sha256_bytes((root / name).read_bytes()) for name in (
        'diagnostics/model_cost_panel.py', 'diagnostics/probe_recheck_panel.py',
        'diagnostics/positive_verification_panel.py', NOTE,
    )}


def price(arm):
    p = pricing_for_model(MODELS[arm])
    return {k: str(getattr(p, k)) for k in (
        'input_per_million_usd', 'cached_input_per_million_usd', 'output_per_million_usd')}


def validate_evidence(path):
    receipt = json.loads(path.read_bytes())
    require(receipt['passed'] and receipt['provider_calls'] == 0
            and receipt['runtime_hash'] == runtime_content_hash()
            and receipt['implementation'] == bindings(), 'offline validation identity changed')
    require(bool(receipt['files']), 'validation artifacts required')
    for name, digest in receipt['files'].items():
        require(sha256_bytes(Path(name).read_bytes()) == digest, 'validation artifact changed')
    return receipt


def freeze(root, live_root, validation):
    require(not root.exists() and not live_root.exists(), 'fresh roots required')
    require(not root.resolve().is_relative_to(repository_root())
            and not live_root.resolve().is_relative_to(repository_root()),
            'external roots required')
    validate_evidence(validation)
    runner._require_tracked_clean_paths(repository_root(), list(bindings()))
    cases = {}
    for case in TASKS:
        req = request(case, 'mini', live_root / 'unused')
        package, _, _, environment = driver.environment(req)
        runner._live_source_preflight(req.task.parent, package)
        cases[case] = {
            'task_id': package.public.task_id, 'task_hash': package.task_content_hash,
            'public_hash': package.public_spec_hash, 'environment': environment,
            'historical_stratum_only': TASKS[case][2],
            'external': {str(p): sha256_bytes(p.read_bytes()) for p in
                         (req.prepared_source, req.prepared_probe_dependencies) if p is not None},
        }
    rows = [{
        'label': f'{case}{arm}{rep}', 'case': case, 'arm': arm, 'repetition': rep,
        'request': request(case, arm, live_root / f'{case}{arm}{rep}').model_dump(mode='json'),
        'model_hash': runner._model_hash(request(case, arm, live_root / f'{case}{arm}{rep}'),
                                         pricing_for_model(MODELS[arm])),
    } for case, arm, rep in ORDER]
    packet = {
        'schema': 'model-cost-panel-v1', 'official': False, 'claim_eligible': False,
        'head': git_commit(), 'runtime_hash': runtime_content_hash(), 'implementation': bindings(),
        'cases': cases, 'rows': rows, 'order': ORDER, 'models': MODELS,
        'pricing': {arm: price(arm) for arm in MODELS}, 'row_cap_usd': str(ROW_CAP),
        'per_task_cap_usd': '12', 'per_model_cap_usd': '36', 'total_cap_usd': str(CAP),
        'live_root': str(live_root), 'credential': str(repository_root() / '.env'),
        'validation': {'path': str(validation), 'hash': sha256_bytes(validation.read_bytes())},
        'approval': 'PENDING_EXACT_HUMAN_SCOPE', 'start': 'fresh base per row; no imported history',
        'retries_resume_replacements_transfer': False,
    }
    root.mkdir(parents=True)
    save(root, 'manifest.json', packet)
    digest = sha256_json(packet)
    save(root, 'result-format.json', aggregate([]))
    DevJournal(root, JOURNAL).append('panel_prepared', {'packet_hash': digest, 'provider_calls': 0})
    return digest


def validate(root, packet_hash):
    packet = json.loads((root / 'manifest.json').read_bytes())
    require(sha256_json(packet) == packet_hash, 'manifest changed')
    require(packet['head'] == git_commit() and packet['runtime_hash'] == runtime_content_hash()
            and packet['implementation'] == bindings(), 'implementation changed')
    require(packet['order'] == [list(r) for r in ORDER] and packet['models'] == MODELS
            and packet['row_cap_usd'] == str(ROW_CAP) and packet['total_cap_usd'] == str(CAP)
            and packet['pricing'] == {arm: price(arm) for arm in MODELS}, 'scope changed')
    v = packet['validation']
    require(sha256_bytes(Path(v['path']).read_bytes()) == v['hash'], 'validation changed')
    validate_evidence(Path(v['path']))
    live = Path(packet['live_root'])
    require(len(packet['rows']) == len(ORDER), 'incomplete manifest')
    for row, (case, arm, rep) in zip(packet['rows'], ORDER, strict=True):
        req = request(case, arm, live / f'{case}{arm}{rep}')
        require(req.model_dump(mode='json') == row['request'], 'request changed')
        require(row['model_hash'] == runner._model_hash(req, pricing_for_model(MODELS[arm])),
                'model identity changed')
        _, package = runner._resolve_task_file(req.task)
        require(package.task_content_hash == packet['cases'][case]['task_hash'], 'task changed')
        runner._live_source_preflight(req.task.parent, package)
        for path, digest in packet['cases'][case]['external'].items():
            require(sha256_bytes(Path(path).read_bytes()) == digest, 'prepared descriptor changed')
    return packet


def preflight(root, packet_hash):
    packet = validate(root, packet_hash)
    require(not Path(packet['live_root']).exists(), 'no restart or replacement')
    for case in TASKS:
        req = request(case, 'mini', Path(packet['live_root']) / 'unused')
        *_, identity = driver.environment(req)
        require(identity == packet['cases'][case]['environment'], 'environment changed')
    receipt = {'packet_hash': packet_hash, 'provider_calls': 0,
               'environments': {k: v['environment'] for k, v in packet['cases'].items()}}
    save(root, 'preflight.json', receipt)
    DevJournal(root, JOURNAL).append('preflight_passed', {
        'packet_hash': packet_hash, 'receipt_hash': sha256_json(receipt)})
    return receipt


def aggregate(rows):
    expected = [(c, a, r) for c, a, r in ORDER]
    require([(r['case'], r['arm'], r['repetition']) for r in rows] == expected[:len(rows)],
            'rows must be unique and in frozen order')
    records = []
    for row in rows:
        result = row['result']
        require(len(result['runs']) == 1, 'one fresh solve per row required')
        run = result['runs'][0]
        ev = run.get('evaluator') or {}
        records.append({
            'case': row['case'], 'arm': row['arm'], 'repetition': row['repetition'],
            'terminal': run['terminal'], 'acceptance': ev.get('task_acceptance', 'NOT_RUN'),
            'safety': ev.get('safety_state', 'NOT_RUN'),
            'submitted': bool(run.get('artifact_hashes', {}).get('submitted_patch')),
            'known_cost': row['settled'] and row['within_cap'],
            'recorded_cost_nanos': result['cost_nanos'], 'elapsed_seconds': row['elapsed_seconds'],
        })
    summaries = {}
    for arm in MODELS:
        selected = [r for r in records if r['arm'] == arm]
        counts = Counter(r['acceptance'] for r in selected)
        known = all(r['known_cost'] for r in selected)
        cost = sum(r['recorded_cost_nanos'] for r in selected)
        summaries[arm] = {
            'planned': 12, 'executed': len(selected), 'not_started': 12 - len(selected),
            'acceptance': {key: counts[key] for key in ('PASS', 'FAIL', 'ERROR', 'NOT_RUN')},
            'unsubmitted': sum(not r['submitted'] for r in selected),
            'safety': dict(Counter(r['safety'] for r in selected)),
            'recorded_cost_nanos': cost, 'billing_known': known,
            'elapsed_seconds': round(sum(r['elapsed_seconds'] for r in selected), 3),
            'cost_per_acceptance_nanos': (
                cost / counts['PASS'] if known and counts['PASS'] else None),
            'passes_by_repetition': [sum(r['acceptance'] == 'PASS' and r['repetition'] == rep
                                         for r in selected) for rep in (1, 2)],
        }
    complete = len(records) == len(ORDER)
    valid = complete and all(r['known_cost'] and r['acceptance'] != 'ERROR'
                             and r['safety'] != 'ERROR' for r in records)
    mini, full = summaries['mini'], summaries['full']
    choose_mini = (valid and all(a >= b for a, b in zip(
        mini['passes_by_repetition'], full['passes_by_repetition'], strict=True))
        and mini['acceptance']['PASS'] > 0 and mini['unsubmitted'] <= full['unsubmitted']
        and mini['recorded_cost_nanos'] < full['recorded_cost_nanos']
        and mini['elapsed_seconds'] <= 1.25 * full['elapsed_seconds']
        and all(r['safety'] == 'PASS' for r in records if r['submitted']))
    return {'schema': 'model-cost-result-v1', 'official': False, 'rows': records,
            'models': summaries, 'complete': complete, 'comparison_valid': valid,
            'decision': ('SELECT_MINI_FOR_THIS_DEVELOPMENT_PANEL' if choose_mini else
                         'KEEP_FULL_REVIEW_TRADEOFF' if valid else 'INCOMPLETE_KEEP_BASELINE'),
            'automatic_followup': False}


def run(root, packet_hash):
    packet = validate(root, packet_hash)
    outcome = driver.run_fresh_rows(
        root, packet_hash, validate_packet=validate, order=ORDER,
        live_root=Path(packet['live_root']), request_for=request,
        instruction_scope=lambda arm: nullcontext(), row_cap=ROW_CAP, total_cap=CAP,
        journal_id=JOURNAL,
    )
    summary = aggregate(outcome['rows'])
    save(root, 'summary.json', summary)
    DevJournal(root, JOURNAL).append('comparison_summarized', {
        'summary_hash': sha256_json(summary)})
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['freeze', 'preflight', 'run'])
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--live-root', type=Path)
    parser.add_argument('--validation', type=Path)
    parser.add_argument('--packet-hash')
    args = parser.parse_args()
    if args.command == 'freeze':
        require(args.live_root is not None and args.validation is not None,
                'freeze inputs required')
        result = freeze(args.root, args.live_root, args.validation)
    else:
        require(bool(args.packet_hash), 'exact packet hash required')
        result = globals()[args.command](args.root, args.packet_hash)
    print(canonical_json(result))


if __name__ == '__main__':
    main()
