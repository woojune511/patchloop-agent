"""Provider-free question-priority replay of immutable public handoff snapshots.

Declarations are operator-authored capacity examples, never historical model output.
No task checkout, task execution, future action selection or evaluator access.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from types import SimpleNamespace

from diagnostics.evidence_handoff_replay import Inputs, digest, inventory, ranges, surrogate
from patchloop.contracts import PublicTask
from patchloop.dev.context import build_observed_source_index
from patchloop.dev.contracts import DevLimits, DevToolResult
from patchloop.dev.conversation import assemble_model_input
from patchloop.dev.evidence_focus import bind_question
from patchloop.dev.public_history import SnapshotRules
from patchloop.dev.runner import _segment_current_view, _segment_public_base
from patchloop.dev.state import DevJournal
from patchloop.dev.thin_policy import system_prompt
from patchloop.dev.tools import DevToolGateway
from patchloop.errors import ContractError
from patchloop.runtime import runtime_content_hash
from patchloop.util import canonical_json, sha256_json

RULES = SnapshotRules('harness_current_state', 'harness_historical_public_evidence_v1', '',
                      initial_state_index=1)


class SavedGateway(DevToolGateway):
    """Hydrate observations, replacing only live filesystem currency reads."""

    def __init__(self, state, prefix, root):
        self._snapshot_diff = state['current_diff']['patch_hash']
        super().__init__(workspace=root / 'unmaterialized',
                         public_task=PublicTask.model_validate(state['public_task']),
                         sandbox=None, journal=SimpleNamespace(events=lambda: prefix),
                         limits=DevLimits())
        self._working_findings = copy.deepcopy(state['working_notes']['findings'])
        spans = list(self.spans.values())
        versions = {}
        for s in spans:
            if s['path'] not in versions or s.get('last_observed_seq', 0) > versions[s['path']][0]:
                versions[s['path']] = s.get('last_observed_seq', 0), s['file_hash']
        self._snapshot_spans = [s for s in spans if s['file_hash'] == versions[s['path']][1]]

    @property
    def current_diff_hash(self):
        return self._snapshot_diff

    def _refresh_working_source_notes(self):
        # Exact snapshot versions were already selected; no current task checkout exists.
        pass

    def _validated_source_spans(self):
        return copy.deepcopy(self._snapshot_spans)

    def _tracked_path(self, path, **_):
        selected = [s for s in self._snapshot_spans if s['path'] == path]
        if not selected:
            raise ContractError('no observed public source')
        lines = {s['start_line'] + i: line for s in selected
                 for i, line in enumerate(s['content'].split('\n'))}
        # Only locates prior failed mutation anchors. Sentinels never become observations.
        body = '\n'.join(lines.get(n, '\x00unobserved') for n in range(1, max(lines) + 1))
        return path, SimpleNamespace(read_bytes=lambda: body.encode())

    def set_question(self, question):
        self._working_open_question = copy.deepcopy(question)
        self._working_question_bodies = self._capture_working_note_source_bodies(
            question['evidence'], self._snapshot_spans,
        ) or [] if isinstance(question, dict) else []


def compose(state, gateway, latest, prefix):
    projection = gateway.prepare_context_projection(latest)
    candidate = copy.deepcopy(state)
    candidate['source_spans'] = list(projection.source_spans)
    candidate['working_notes']['open_question'] = copy.deepcopy(gateway._working_open_question)
    candidate['observed_source_index'] = build_observed_source_index(
        projection.delivered_spans, editable_paths=projection.editable_paths)
    candidate['context_projection'].update(
        retained_content_chars=projection.retained_content_chars,
        omitted_observed_line_count=projection.omitted_observed_line_count,
        omitted_pinned_ranges=list(projection.omitted_pinned_ranges),
        omitted_observed_ranges=list(projection.omitted_observed_ranges),
        omitted_observed_range_count=projection.omitted_observed_range_count,
        delivered_source_hash=sha256_json(projection.delivered_spans))
    ids = {r.action_id for r in latest}
    calls = [c for e in prefix if e['event_type'] == 'turn_decision_recorded'
             for c in e['payload'].get('tool_calls', []) if c['action_id'] in ids]
    prompt = system_prompt('current', 'brief-v1')
    base = _segment_public_base(prompt, candidate, latest, calls)
    view = _segment_current_view(candidate, base[3:], latest)
    model_input = assemble_model_input(system_prompt=prompt, state=view, history=[],
                                       previous_input=base, context_policy='segmented-v1')
    facts, _, _ = RULES.inventory(model_input)
    actual = {(*key, value) for key, value in facts.items()}
    assert actual == inventory(projection.delivered_spans)
    assert actual <= inventory(gateway._snapshot_spans)
    assert projection.retained_content_chars <= 24000
    assert not any(i.get('type') == 'reasoning' for i in model_input)
    return projection, view, model_input, actual


def write_case(root, name, model_input, view, projection, actual, original, prior, protected):
    assert protected <= actual
    path = root / f'{name}.json'
    path.write_text(canonical_json(model_input), encoding='utf-8')
    critical = {167, 199, 200, 201, 202, 206, 207, 208}
    question = view['working_notes'].get('open_question')
    return {
        'id': name, 'input_artifact': {'path': str(path), 'sha256': digest(path.read_bytes())},
        'retained_chars': projection.retained_content_chars,
        'input_bytes': len(path.read_bytes()), 'protected_lines': len(protected),
        'gained_from_original': ranges(actual - original),
        'lost_from_original': ranges(original - actual),
        'gained_from_prior': ranges(actual - prior), 'lost_from_prior': ranges(prior - actual),
        'gained_original_count': len(actual - original),
        'lost_original_count': len(original - actual),
        'gained_prior_count': len(actual - prior), 'lost_prior_count': len(prior - actual),
        'critical_lines': sorted(n for p, _, n, _ in actual
                                 if p == 'astroid/manager.py' and n in critical),
        'question': question,
        'notes': [{k: n[k] for k in ('note_id', 'evidence_currency', 'evidence_delivery',
                                   'evidence')}
                  for n in view['working_notes']['findings']],
        'lost_from_prior_text': [{'path': p, 'file_hash': h, 'line': n, 'text': t}
                                 for p, h, n, t in sorted(prior - actual)],
        'gained_from_prior_text': [{'path': p, 'file_hash': h, 'line': n, 'text': t}
                                   for p, h, n, t in sorted(actual - prior)],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--audit-root', type=Path, required=True)
    parser.add_argument('--prior-root', type=Path, required=True)
    args = parser.parse_args()
    root = args.output
    journal = DevJournal(root, 'run_dev_questionpriority')
    planned = journal.events()[0]
    assert planned['event_type'] == 'analysis_planned'
    assert not (root / 'results.json').exists(), 'Use a fresh planned evidence directory'
    journal.append('replay_started', {'runtime_hash': runtime_content_hash(),
                                     'script_hash': digest(Path(__file__).read_bytes())})
    reader = Inputs()
    try:
        boundaries = reader.read(args.audit_root / 'boundaries-v2.json')
        # Only the public journal paths are used; outcome columns never affect selection.
        journals = {r['row']: r['journal'] for r in reader.read(args.audit_root / 'rows-v2.json')}
        prior_rows = {(r['row'], r['sequence']): r
                      for r in reader.read(args.prior_root / 'results.json')}
        event_cache, results, linebook = {}, [], ['# New source displacement', '']
        for boundary in boundaries:
            row, seq = boundary['row'], boundary['segment_sequence']
            if row not in event_cache:
                event_cache[row] = reader.events(journals[row])
            prefix = [e for e in event_cache[row] if e['sequence'] < seq]
            state = reader.artifact(boundary['handoff_artifact'])['state']
            gateway = SavedGateway(state, prefix, root)
            prior_results = {e['payload']['result']['action_id']: e['payload']['result']
                             for e in prefix if e['event_type'] == 'action_finished'}
            latest = [DevToolResult.model_validate(prior_results[r['action_id']])
                      for r in state['latest_tool_results']]
            original_facts, _, _ = RULES.inventory(
                reader.artifact(boundary['after_input_artifact']))
            original = {(*k, v) for k, v in original_facts.items()}
            prior_record = prior_rows[row, seq]
            prior_facts, _, _ = RULES.inventory(reader.artifact({
                'path': prior_record['input_artifact']['path'],
                'content_hash': prior_record['input_artifact']['sha256']}))
            prior = {(*k, v) for k, v in prior_facts.items()}
            priorities = gateway._source_projection_priorities()
            protected = {x for x in original if any(x[0] == p and lo <= x[2] <= hi and rank <= 1
                                                    for p, lo, hi, rank in priorities)}
            gateway.set_question(state['working_notes'].get('open_question'))
            projection, view, model_input, actual = compose(state, gateway, latest, prefix)
            assert actual == original
            assert inventory(projection.source_spans) == inventory(state['source_spans'])
            variants = {'actual_legacy': (projection, view, model_input, actual)}
            unscoped, error = bind_question({'text': 'Legacy surrogate; roles NOT_EXPOSED',
                                             'evidence': surrogate(state)},
                                            gateway._snapshot_spans, prior_results)
            assert error is None
            gateway.set_question(unscoped)
            variants['unscoped_surrogate'] = compose(state, gateway, latest, prefix)
            assert variants['unscoped_surrogate'][3] == original
            if row == 13 and str(seq) in planned['payload']['fixed_declarations']:
                refs = planned['payload']['fixed_declarations'][str(seq)]
                question, error = bind_question({
                    'text': 'Which observed open raises the missing-file error?' if seq == 303 else
                            'Does the directory guard reach the namespace route, and which branch '
                            'raises the observed file error?', 'evidence': refs,
                }, gateway._snapshot_spans, prior_results, diff_hash=gateway.current_diff_hash)
                assert error is None
                gateway.set_question(question)
                variants['paired_current'] = compose(state, gateway, latest, prefix)
                assert variants['paired_current'][1]['working_notes']['open_question'][
                    'evidence_delivery'] == 'complete'
                if seq == 476:
                    # Same old note, explicitly typed at its original before-edit diff.
                    stale_refs = [{**r, 'role': 'primary'} for r in surrogate(state)]
                    stale, error = bind_question({'text': state['working_notes']['open_question'],
                                                   'evidence': stale_refs},
                                                  gateway._snapshot_spans, prior_results,
                                                  diff_hash=state['working_notes'][
                                                      'last_update_result']['diff_hash_at_update'])
                    assert error is None
                    gateway.set_question(stale)
                    variants['pre_edit_question'] = compose(state, gateway, latest, prefix)
                    assert variants['pre_edit_question'][3] == original
            for variant, (projection, view, model_input, actual) in variants.items():
                name = f'row{row:02}-boundary{seq}-{variant}'
                result = write_case(root, name, model_input, view, projection, actual,
                                    original, prior, protected)
                result.update(row=row, boundary=seq, variant=variant,
                              original_reason=boundary['reason'],
                              prior_input_bytes=prior_record['new_input_bytes'])
                results.append(result)
                if variant in {'paired_current', 'pre_edit_question'}:
                    linebook.extend([f'## {name}', ''])
                    for label, field in [('Newly omitted vs prior implementation',
                                          'lost_from_prior_text'),
                                         ('Restored vs prior implementation',
                                          'gained_from_prior_text')]:
                        linebook.extend([f'### {label}', '', '```text'])
                        linebook.extend(f"{x['path']}:{x['line']} | {x['text']}"
                                        for x in result[field])
                        linebook.extend(['```', ''])
        summary = {}
        for variant in sorted({r['variant'] for r in results}):
            selected = [r for r in results if r['variant'] == variant]
            summary[variant] = {'cases': len(selected), **{k: sum(r[k] for r in selected) for k in (
                'gained_original_count', 'lost_original_count', 'gained_prior_count',
                'lost_prior_count')},
                'max_retained_chars': max(r['retained_chars'] for r in selected)}
        for name, data in [('results.json', results), ('summary.json', summary),
                           ('read-manifest.json', list(reader.files.values()))]:
            (root / name).write_text(json.dumps(data, ensure_ascii=False, indent=2),
                                     encoding='utf-8')
        (root / 'linebook.md').write_text('\n'.join(linebook), encoding='utf-8')
        assert all(digest(Path(x['path']).read_bytes()) == x['sha256']
                   for x in reader.files.values())
        journal.append('replay_completed', {
            'summary': summary, 'original_inputs_unchanged': len(reader.files),
            'runtime_hash': runtime_content_hash(),
            'artifacts': {p.name: digest(p.read_bytes()) for p in root.iterdir() if p.is_file()},
            'provider_calls': 0, 'model_exposure': 'NOT_EXPOSED',
            'exact_token_counts_and_full_request_admission': 'NOT_RUN', 'quality_claim': False,
        })
        print(json.dumps(summary, indent=2))
    except Exception as exc:
        journal.append('replay_failed', {'exception': type(exc).__name__, 'message': str(exc)})
        raise


if __name__ == '__main__':
    main()
