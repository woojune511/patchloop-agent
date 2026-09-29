"""Fixed-candidate repair: identical public probe, withheld versus observed output."""
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from time import monotonic
from unittest.mock import patch

from diagnostics import boundary_pair_panel as panel
from diagnostics import candidate_review_repair as seeded
from diagnostics import discriminating_case_selection as selection
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact
from patchloop.deadline import ExecutionDeadline
from patchloop.dev import runner
from patchloop.dev.contracts import DevLimits
from patchloop.dev.conversation import reconstruct_state
from patchloop.dev.state import DevJournal
from patchloop.repository import WorkspaceManager
from patchloop.runtime import repository_root, runtime_content_hash
from patchloop.sandbox.probes import DockerProbeSandbox
from patchloop.util import canonical_json, sha256_bytes, sha256_json, utc_now

ORDER = ('A1', 'B1', 'B2', 'A2')
CAP, ROW_CAP = Decimal('8'), Decimal('2')
EVIDENCE = Path('C:/pt/analyses/selected-probe-execution-20260929-v2')
WITHHELD = 'Execution observations are withheld in this condition; no result is supplied.'
require, save = panel.require, panel.save


def feedback(seed_hash, requirement, program, receipt_hash, output, arm):
    require(arm in ('A', 'B'), 'unknown arm')
    return dict(observed_on_diff_hash=seed_hash, requirement=requirement,
                python_source=program, execution_receipt_hash=receipt_hash,
                stdout=WITHHELD if arm == 'A' else canonical_json({
                    k: output[k] for k in ('stdout', 'stderr', 'exit_code', 'setup_checks')}),
                limitations='The program and expected values were model-authored. Both conditions '
                'receive the same program; execution observations may be withheld. Independently '
                'interpret the public requirement. This is an external replay on the initial '
                'candidate, not a check verdict for subsequent edits or a repair instruction.')


def payload():
    loaded, bindings = selection.sources()
    requests, _, source, envelope = loaded['H']
    state = reconstruct_state(requests['A']['input'], context_policy='segmented-v1')
    journal = DevJournal(EVIDENCE / 'state', 'run_dev_selectedprobeexecution')
    events = journal.events()
    refs = [e['payload']['artifact'] for e in events
            if e['event_type'] == 'selected_probe_finished']
    raw = ArtifactStore(EVIDENCE).read_bytes(Artifact.model_validate(refs[5]))
    receipt = json.loads(raw)
    plan = json.loads((EVIDENCE / 'plan.json').read_bytes())
    row = plan['rows'][5]
    require(receipt['case'] == row['case'] == 'H' and receipt['repeat'] == 2,
            'fixed H B2 observation required')
    output = receipt['receipt']['output']
    program = row['raw_call']['arguments']['python_source']
    require(output['source_hash'] == sha256_bytes(program.encode())
            and output['diff_hash'] == state['current_diff']['patch_hash']
            and output['exit_code'] == 1 and output['setup_checks']['status'] == 'passed'
            and not any(output[k] for k in ('cleanup_failed', 'timed_out', 'truncated')),
            'observation identity or completeness changed')
    bindings[str(EVIDENCE / 'plan.json')] = sha256_bytes((EVIDENCE / 'plan.json').read_bytes())
    bindings[str(journal.path)] = sha256_bytes(journal.path.read_bytes())
    return {'seed': state['current_diff'], 'source_run_id': source['run_id'],
            'base_commit': envelope.base_commit, 'program': program, 'sources': bindings,
            'feedback': {arm: feedback(state['current_diff']['patch_hash'],
                state['public_task']['issue']['description'], program, sha256_bytes(raw),
                output, arm) for arm in ('A', 'B')}}


def request(root):
    return panel.request('H', root).model_copy(update={'max_cost_usd': ROW_CAP,
        'limits': DevLimits(wall_time_seconds=900, max_protocol_recoveries=0)})


def bindings():
    return {str(p.resolve()): sha256_bytes(p.read_bytes()) for p in (
        Path(__file__), Path(seeded.__file__), Path(panel.__file__),
        repository_root() / '.agent/observation-repair-panel.md')}


def freeze(root):
    require(not root.exists() and not root.resolve().is_relative_to(repository_root()),
            'fresh external root required')
    data = payload()
    _, package = runner._resolve_task_file(request(root / 'unused').task)
    packet = {'schema': 'observation-repair-panel-v1', 'order': ORDER,
              'cap_usd': str(CAP), 'row_cap_usd': str(ROW_CAP), 'global_seconds': 4200,
              'runtime_hash': runtime_content_hash(), 'implementation': bindings(),
              'task_hash': package.task_content_hash, 'payload': data,
              'request': request(root / 'unused').model_dump(mode='json'),
              'pricing_source': 'https://developers.openai.com/api/docs/models/gpt-5.4',
              'pricing_verified_on': utc_now().date().isoformat(), 'official': False}
    root.mkdir(parents=True)
    save(root, 'packet.json', packet)
    digest = sha256_bytes((root / 'packet.json').read_bytes())
    DevJournal(root, 'run_dev_observationrepair').append('prepared', {'packet_hash': digest})
    return digest


def validate(root, digest):
    raw = (root / 'packet.json').read_bytes()
    require(sha256_bytes(raw) == digest, 'packet changed')
    p = json.loads(raw)
    require(p['implementation'] == bindings() and p['runtime_hash'] == runtime_content_hash()
            and p['payload'] == payload() and p['order'] == list(ORDER)
            and p['cap_usd'] == str(CAP) and p['row_cap_usd'] == str(ROW_CAP)
            and p['request'] == request(root / 'unused').model_dump(mode='json'), 'design drift')
    _, package = runner._resolve_task_file(request(root / 'unused').task)
    require(package.task_content_hash == p['task_hash'], 'task changed')
    return p


def preflight(root, digest):
    validate(root, digest)
    req = request(root / 'unused')
    directory, package = runner._resolve_task_file(req.task)
    runner._live_task_is_admitted(directory, package)
    runner._live_source_preflight(directory, package)
    sandbox = runner._live_sandbox_preflight(package)
    dependencies = panel.deps.load_dependencies(req.prepared_probe_dependencies, package.public,
                                                panel.deps.admit(req.prepared_probe_dependencies))
    probe = DockerProbeSandbox(dependencies=dependencies)
    receipt = {'evaluator': sandbox.image_identity(), 'probe': probe.preflight(),
               'provider_calls': 0, 'credential_reads': 0}
    save(root, 'preflight.json', receipt)
    DevJournal(root, 'run_dev_observationrepair').append('preflight', receipt)
    return receipt


def run(root, digest, *, approved_cap):
    require(Decimal(approved_cap) == CAP, 'exact new USD 8 approval required')
    p = validate(root, digest)
    require(p['pricing_verified_on'] == utc_now().date().isoformat(),
            'refresh pricing before a later UTC date')
    journal = DevJournal(root, 'run_dev_observationrepair')
    with journal.execution_lock():
        events = journal.events()
        require(any(e['event_type'] == 'preflight' for e in events), 'preflight required')
        require(not any(e['event_type'] == 'started' for e in events), 'no resume or replacement')
        runner._require_tracked_clean_paths(repository_root(), [
            'diagnostics/observation_repair_panel.py', '.agent/observation-repair-panel.md'])
        journal.append('started', {'approved_cap': str(CAP), 'packet_hash': digest})
        rows, started = [], monotonic()
        original = runner._run_one
        try:
            for label in ORDER:
                require(monotonic() - started < 3210,
                        'insufficient time for another 900s run and audit')
                captured = []

                def one(_captured=captured, **kwargs):
                    result = original(**kwargs)
                    _captured.append(result)
                    return result

                req = request(root / 'state' / label)
                data = p['payload']
                with patch.object(runner, '_run_one', one):
                    result = seeded.run_seeded(req, seed_patch=data['seed']['patch'],
                        seed_hash=data['seed']['patch_hash'], base_commit=data['base_commit'],
                        source_code=[], review=None, experiment_hash=digest,
                        source_run_id=data['source_run_id'], branch=label,
                        public_feedback=data['feedback'][label[0]])
                require(len(captured) == 1, 'one run required')
                row = {'label': label, 'result': result,
                       'stop_remaining': captured[0].stop_remaining}
                rows.append(row)
                journal.append('run_finished', row)
                if captured[0].stop_remaining:
                    break
                public = result['runs'][0]
                state = Path(req.state_root)
                run_journal = DevJournal(state, public['run_id'])
                env = run_journal.load_envelope()
                _, package = runner._resolve_task_file(req.task)
                deps = runner.load_dependencies(req.prepared_probe_dependencies, package.public,
                                                env.probe_dependencies)
                probe = DockerProbeSandbox(dependencies=deps)
                deadline = ExecutionDeadline.from_remaining(90)
                probe.preflight(deadline=deadline)
                workspace = state / 'workspaces' / public['run_id'] / 'repo'
                before = WorkspaceManager.diff_summary(workspace)
                identity = {'run_id': 'run_dev_observationrepair', 'action_id': label,
                            'input_hash': sha256_json({'program': data['program'],
                                                      'diff_hash': before.patch_hash})}
                journal.append('audit_started', {'label': label, 'identity': identity})
                audit = probe.run_probe(workspace, 'Frozen public endpoint reproduction',
                    data['program'], deadline=deadline, execution_identity=identity)
                save(root, f'audit-{label}.json', audit)
                journal.append('audit_finished', {'label': label, 'hash': sha256_json(audit)})
                after = WorkspaceManager.diff_summary(workspace)
                require(not audit.get('cleanup_failed') and not audit.get('deadline_exhausted')
                        and after.patch_hash == before.patch_hash,
                        'audit uncertainty or workspace drift')
            save(root, 'result.json', {'rows': rows, 'official': False, 'resume_allowed': False})
            journal.append('closed', {'completed': len(rows), 'unused_budget_closed': True})
        except BaseException as exc:
            journal.append('interrupted', {'type': type(exc).__name__, 'resume_allowed': False})
            raise
    return rows
