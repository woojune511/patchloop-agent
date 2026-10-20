"""Existing duplicate names do not make unrelated additive tests ambiguous."""

from textwrap import indent

import pytest
from test_additive_test_policy import source

from patchloop.contracts import TaskConstraints
from patchloop.dev.contracts import PublicTurnDecision, RequestedTool
from patchloop.errors import ContractError
from patchloop.git_execution import run_git
from patchloop.repository import WorkspaceManager
from patchloop.test_additions import UnsupportedTestChange, added_tests
from patchloop.verifier.policy import original_test_view, verify_test_tampering

DUPLICATES = (
    'def test_duplicate():\n    assert 1 == 1\n\n'
    'def test_duplicate():\n    assert 2 == 2\n'
)
ADDITION = '\ndef test_new():\n    assert 3 == 3\n'
CLASS = '\nclass TestContainer:\n    def test_existing(self):\n        assert 4 == 4\n'
METHOD = '\n    def test_new(self):\n        assert 5 == 5\n'


@pytest.mark.parametrize('suite_additions', [False, True])
@pytest.mark.parametrize('identical', [False, True])
def test_unchanged_duplicates_allow_an_unambiguous_new_function(suite_additions, identical):
    before = DUPLICATES.replace('2 == 2', '1 == 1') if identical else DUPLICATES
    assert added_tests(before.encode(), before.encode(), 'test_api.py',
                       suite_additions=suite_additions) == []
    assert added_tests(before.encode(), (before + ADDITION).encode(), 'test_api.py',
                       suite_additions=suite_additions) == [{
        'path': 'test_api.py', 'function': 'test_new', 'parameter_names': [], 'indices': None,
    }]


@pytest.mark.parametrize('placement', ['module', 'class'])
def test_duplicate_functions_or_methods_allow_a_new_method(placement):
    before = (DUPLICATES + CLASS if placement == 'module'
              else 'class TestContainer:\n' + indent(DUPLICATES, '    '))
    assert added_tests(before.encode(), (before + METHOD).encode(), 'test_api.py',
                       suite_additions=True) == [{
        'path': 'test_api.py', 'function': 'TestContainer::test_new',
        'parameter_names': [], 'indices': None,
    }]


@pytest.mark.parametrize('suite_additions', [False, True])
@pytest.mark.parametrize('candidate', [
    DUPLICATES.replace('assert 1 == 1', 'assert True') + ADDITION,
    DUPLICATES.replace('assert 2 == 2', 'assert True') + ADDITION,
    DUPLICATES.split('\n\n')[1] + ADDITION,
    DUPLICATES.split('\n\n')[0] + ADDITION,
    '\n\n'.join(reversed(DUPLICATES.split('\n\n'))) + ADDITION,
    DUPLICATES + ADDITION.replace('test_new', 'test_duplicate'),
    DUPLICATES + ADDITION + ADDITION,
])
def test_changed_removed_reordered_or_new_duplicates_still_fail(suite_additions, candidate):
    with pytest.raises(UnsupportedTestChange):
        added_tests(DUPLICATES.encode(), candidate.encode(), 'test_api.py',
                    suite_additions=suite_additions)


@pytest.mark.parametrize('which', [0, 1])
def test_parameter_additions_to_either_duplicate_are_ambiguous(which):
    definition = ('@pytest.mark.parametrize("value", [1])\n'
                  'def test_duplicate(value):\n    assert value > 0\n')
    before = definition + '\n' + definition
    definitions = [definition, definition]
    definitions[which] = definition.replace('[1]', '[1, 2]')
    with pytest.raises(UnsupportedTestChange, match='duplicate'):
        added_tests(before.encode(), '\n'.join(definitions).encode(), 'test_api.py',
                    suite_additions=True)


def test_preserved_duplicate_classes_allow_only_unambiguous_additions():
    before = CLASS + CLASS
    assert added_tests(before.encode(), (before + ADDITION).encode(), 'test_api.py',
                       suite_additions=True)[0]['function'] == 'test_new'
    for after in (CLASS + METHOD + CLASS, before + METHOD, before + CLASS):
        with pytest.raises(UnsupportedTestChange, match='duplicate'):
            added_tests(before.encode(), after.encode(), 'test_api.py', suite_additions=True)


def test_duplicate_baseline_policy_restores_original_bytes(tmp_path):
    path = source(tmp_path)
    before = (DUPLICATES + CLASS).encode()
    path.write_bytes(before)
    run_git(tmp_path, 'add', '.')
    run_git(tmp_path, 'commit', '-m', 'existing duplicates')
    after = before + METHOD.encode()
    path.write_bytes(after)
    outcome = verify_test_tampering(
        WorkspaceManager.diff_summary(tmp_path),
        TaskConstraints(additive_test_roots=['tests']), tmp_path,
    )
    assert outcome.passed, outcome.violations
    with original_test_view(tmp_path, outcome):
        assert path.read_bytes() == before
    assert path.read_bytes() == after


def test_gateway_keeps_protection_with_duplicate_baseline(gateway_factory):
    gateway, _, workspace = gateway_factory()
    path = workspace / 'tests/test_duplicate.py'
    path.parent.mkdir(exist_ok=True)
    before = DUPLICATES + CLASS
    path.write_bytes(before.encode())
    run_git(workspace, 'add', 'tests/test_duplicate.py')
    run_git(workspace, '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
            'commit', '-m', 'existing duplicate tests')
    gateway.public_task.constraints = TaskConstraints(
        allowed_paths=['**'], additive_test_roots=['tests'], max_diff_lines=1000,
    )
    gateway.execute(RequestedTool(
        name='read_file', action_id='read-duplicates',
        arguments={'path': 'tests/test_duplicate.py', 'start_line': 1, 'end_line': 40},
        turn_decision=PublicTurnDecision(
            mode='inspect', basis='Read current tests',
            evidence_goal='Locate additive method anchor',
        ),
    ))
    args = {
        'path': 'tests/test_duplicate.py', 'old_text': before,
        'new_text': before + METHOD, 'occurrence': 1,
        'hypothesis': 'Add an independent regression', 'expected_behavior': 'Keep original tests',
        'causal_revision': None,
    }
    assert gateway._validate_replacement_intent(args).after_bytes == (before + METHOD).encode()
    for candidate in (
        before.replace('assert 1 == 1', 'assert True') + METHOD,
        before + METHOD.replace('test_new', 'test_existing'),
    ):
        with pytest.raises(ContractError, match='preserve existing'):
            gateway._validate_replacement_intent({**args, 'new_text': candidate})
    assert path.read_text(encoding='utf-8') == before
