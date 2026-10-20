"""Replay original and operator programs separately on the saved ineffective patch.

Opt in with PATCHLOOP_TEST_REAL_PROBES=1 and PYDICOM_1413_SOURCE pointing to an
existing local pydicom Git checkout containing BASE. Use an external --basetemp.
No model, downloads, hidden checks, reference patches or changes to source checkout.
"""

from __future__ import annotations

import ast
import io
import json
import os
import subprocess
import tarfile
from pathlib import Path

import pytest

from diagnostics.probe_recheck_public import PYDICOM_WRITE, classify, design
from patchloop.artifacts import ArtifactStore
from patchloop.deadline import ExecutionDeadline
from patchloop.dev.state import DevJournal
from patchloop.repository import WorkspaceManager
from patchloop.runtime import repository_root
from patchloop.sandbox.probes import DockerProbeSandbox
from patchloop.util import sha256_bytes

FIXTURES = Path(__file__).parent / 'fixtures' / 'pydicom_1413'
BASE = 'f909c76e31f759246cec3708dadd173c5d6e84b1'
ORIGINAL_HASH = 'sha256:37df1ed087240f6eda80925da9f51604fa212eeac6c24bc7910235cb572af3de'
PATCH_HASH = 'sha256:0981910bc8d62304d321bc40429bf17a29eb48d9158558dd8fdd04cbfd51f4cc'
OPERATOR_HASH = 'sha256:74241bbbdbba3b4e05279f7b0f82ccc4f2b5ba3842d0932c31f5d373179a0d7b'


def test_original_probe_is_not_a_public_save_reproducer():
    source = (FIXTURES / 'original_probe.py').read_bytes()
    assert sha256_bytes(source) == ORIGINAL_HASH
    assert sha256_bytes((FIXTURES / 'submitted.patch').read_bytes()) == PATCH_HASH
    assert sha256_bytes(PYDICOM_WRITE.encode()) == OPERATOR_HASH
    tree = ast.parse(source)
    byte_inputs = [n.value for n in ast.walk(tree)
                   if isinstance(n, ast.Constant) and isinstance(n.value, bytes)]
    assert byte_inputs and all(b'\\' not in value for value in byte_inputs)
    calls = [n.func for n in ast.walk(tree) if isinstance(n, ast.Call)]
    assert any(isinstance(f, ast.Name) and f.id == 'write_data_element' for f in calls)
    assert not any(isinstance(f, ast.Attribute) and f.attr == 'save_as' for f in calls)
    # The original only observes list/ordinary-byte outcomes; no expected save result.
    assert not any(isinstance(n, ast.Assert) for n in ast.walk(tree))


def _git(path, *args):
    return subprocess.run(['git', '-C', str(path), *args], capture_output=True,
                          check=True, timeout=30).stdout


@pytest.mark.skipif(
    os.environ.get('PATCHLOOP_TEST_REAL_PROBES') != '1'
    or not os.environ.get('PYDICOM_1413_SOURCE'),
    reason='requires explicit local-source/real-probe opt-in',
)
def test_same_programs_on_base_and_saved_submission(tmp_path):
    assert not tmp_path.resolve().is_relative_to(repository_root().resolve())
    source = Path(os.environ['PYDICOM_1413_SOURCE']).resolve(strict=True)
    assert (source / '.git').exists()
    assert _git(source, 'rev-parse', f'{BASE}^{{commit}}').decode().strip() == BASE
    backend = DockerProbeSandbox()
    deadline = ExecutionDeadline.from_remaining(110)
    identity = backend.preflight(deadline=deadline)  # Inspect only; never pull/build.
    workspace = tmp_path / 'public'
    workspace.mkdir()
    archive = _git(source, 'archive', '--format=tar', BASE, 'pydicom')
    with tarfile.open(fileobj=io.BytesIO(archive)) as files:
        files.extractall(workspace, filter='data')
    _git(workspace, 'init')
    _git(workspace, 'config', 'core.autocrlf', 'false')
    _git(workspace, 'add', '--', 'pydicom')
    _git(workspace, '-c', 'user.name=Public replay', '-c', 'user.email=replay@example.invalid',
         'commit', '-m', 'Pinned public source')
    original = (FIXTURES / 'original_probe.py').read_bytes().decode()
    assert sha256_bytes(original.encode()) == ORIGINAL_HASH
    assert sha256_bytes(PYDICOM_WRITE.encode()) == OPERATOR_HASH
    journal = DevJournal(tmp_path / 'evidence', 'run_dev_pydicom1413replay')
    store = ArtifactStore(tmp_path / 'evidence' / 'artifacts')
    journal.append('replay_started', {'base_commit': BASE, 'environment': identity,
                                    'provider_calls': 0, 'original_source_hash': ORIGINAL_HASH,
                                    'operator_source_hash': OPERATOR_HASH,
                                    'submitted_patch_hash': PATCH_HASH})
    observations = {}
    for stage in ('base', 'submitted'):
        if stage == 'submitted':
            _git(workspace, 'apply', str((FIXTURES / 'submitted.patch').resolve()))
        diff = WorkspaceManager.diff_summary(workspace)
        assert not diff.untracked_files
        assert diff.patch_hash == (sha256_bytes(b'') if stage == 'base' else PATCH_HASH)
        for author, program in [('original_agent', original), ('existing_operator', PYDICOM_WRITE)]:
            action = f'{stage}_{author}'
            journal.append('replay_program_started', {'action_id': action,
                                                     'source_hash': sha256_bytes(program.encode()),
                                                     'diff_hash': diff.patch_hash})
            result = backend.run_probe(
                workspace, 'Replay the unchanged public program on this candidate.', program,
                deadline=deadline,
                execution_identity={'run_id': journal.run_id, 'action_id': action},
            )
            journal.append('replay_program_finished', {
                'action_id': action, 'receipt': store.put_json(result).model_dump(mode='json'),
            })
            assert not any(result.get(k) for k in ('cleanup_failed', 'timed_out', 'truncated',
                                                   'deadline_exhausted'))
            assert result['exit_code'] == 0, result
            if author == 'original_agent':
                final = ast.literal_eval(result['stdout'].splitlines()[-1])['results']
                assert final['list']['ok'] is False and final['list']['exc_type'] == 'TypeError'
                assert final['bytes']['ok'] is True
                observations[stage, author] = final
            else:
                rows = json.loads(result['stdout'])
                assert rows[0] == {'case': 'repair', 'contains_backslash': True,
                                   'constructed_type': 'MultiValue', 'saved': False,
                                   'error': 'TypeError'}
                assert all(r['saved'] and r['bytes_preserved'] for r in rows[1:])
                assert classify(result, design('1413', ''))['status'] == 'FAIL'
                observations[stage, author] = rows
    assert observations['base', 'original_agent'] == observations['submitted', 'original_agent']
    assert (observations['base', 'existing_operator']
            == observations['submitted', 'existing_operator'])
    journal.append('replay_assertions_passed', {
        'original_program_suitable_for_issue': False,
        'operator_program_exposes_ineffective_submission': True,
        'new_runtime_connection_justified': False, 'provider_calls': 0,
    })
