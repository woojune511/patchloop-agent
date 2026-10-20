"""Whole test definitions may be added without changing existing class members."""

import subprocess
import sys

import pytest
from test_additive_test_policy import source

from patchloop.contracts import TaskConstraints
from patchloop.git_execution import run_git
from patchloop.repository import WorkspaceManager
from patchloop.test_additions import UnsupportedTestChange, added_tests
from patchloop.verifier.policy import original_test_view, verify_test_tampering

BASE = '''import unittest
from unittest import mock
import pytest

class TestExisting:
    @pytest.mark.parametrize("value", [1])
    def test_value(self, value):
        assert value > 0

    def helper(self):
        return 7
'''
METHOD = '''
    def test_added(self):
        assert self.helper() == 7
'''
CLASS = '''
class TestAdditional(unittest.TestCase):
    """An independent unittest regression."""
    def test_added(self):
        self.assertEqual(2, 2)
'''
DECORATED = '''
@mock.patch.object(unittest.TestCase, "maxDiff", None)
def test_decorated():
    assert unittest.TestCase.maxDiff is None
'''


def test_suite_accepts_methods_parameter_cases_classes_and_decorated_functions(tmp_path):
    candidate = BASE.replace('[1]', '[1, 2]') + METHOD + CLASS + DECORATED
    selectors = added_tests(
        BASE.encode(), candidate.encode(), "tests/test_api.py", suite_additions=True
    )
    assert [(s["function"], s["indices"]) for s in selectors] == [
        ("TestExisting::test_value", [1]),
        ("TestExisting::test_added", None),
        ("TestAdditional::test_added", None),
        ("test_decorated", None),
    ]
    target = tmp_path / "test_additions.py"
    target.write_text(candidate, encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", str(target)],
        cwd=tmp_path, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "5 passed" in result.stdout


@pytest.mark.parametrize(
    "candidate",
    [
        BASE.replace("value > 0", "True") + METHOD,
        BASE.replace("return 7", "return 0") + METHOD,
        BASE.replace("class TestExisting:", "class TestExisting(unittest.TestCase):") + METHOD,
        BASE.replace("class TestExisting:", "@pytest.mark.skip\nclass TestExisting:") + METHOD,
        BASE.replace('[1]', '[2]') + METHOD,
        BASE + METHOD.replace("test_added", "test_value"),
        BASE + METHOD.replace("test_added", "setUp"),
        BASE + CLASS.replace("def test_added", "def setUp"),
    ],
)
def test_original_members_class_headers_and_fixtures_remain_immutable(candidate):
    with pytest.raises(UnsupportedTestChange):
        added_tests(BASE.encode(), candidate.encode(), "tests/test_api.py", suite_additions=True)


def test_repair_verify_keeps_its_top_level_selector_contract():
    with pytest.raises(UnsupportedTestChange):
        added_tests(BASE.encode(), (BASE + METHOD).encode(), "tests/test_api.py")


@pytest.mark.parametrize("case", [
    "pytest.param(2)",
    'pytest.param(2, id="two")',
    'pytest.param({"items": [2, None, True]}, id="nested literal")',
    'pytest.param(-2, id="negative")',
    'pytest.param((2, "two"), id="tuple")',
])
def test_named_literal_cases_keep_original_method_and_select_only_addition(case):
    candidate = BASE.replace("[1]", f"[1, {case}]")
    assert added_tests(
        BASE.encode(), candidate.encode(), "tests/test_api.py", suite_additions=True,
    ) == [{
        "path": "tests/test_api.py", "function": "TestExisting::test_value",
        "parameter_names": ["value"], "indices": [1],
    }]


@pytest.mark.parametrize("case", [
    "pytest.param()",
    "pytest.param(2, marks=pytest.mark.skip)",
    "pytest.param(2, marks=[])",
    "pytest.param(2, ids='two')",
    "pytest.param(2, id=None)",
    "pytest.param(2, id=2)",
    "pytest.param(2, id=str(2))",
    "pytest.param(2, id='two', id='other')",
    "pytest.param(2, **{'id': 'two'})",
    "pytest.param(*(2,))",
    "pytest.param(value)",
    "pytest.param(1 + 1)",
    "pytest.param([int('2')])",
    "pytest.param(set())",
    "pytest.param([x for x in (2,)])",
    "param(2)",
    "other.param(2)",
])
def test_computed_or_marked_new_cases_are_rejected_without_execution(case):
    candidate = BASE.replace("[1]", f"[1, {case}]")
    with pytest.raises(UnsupportedTestChange):
        added_tests(BASE.encode(), candidate.encode(), "tests/test_api.py", suite_additions=True)


def test_existing_marked_case_is_preserved_while_new_named_case_is_added():
    original = BASE.replace("[1]", '[pytest.param(1, marks=pytest.mark.skip, id="old")]')
    candidate = original.replace('id="old")]', 'id="old"), pytest.param(2, id="new")]')
    assert added_tests(
        original.encode(), candidate.encode(), "tests/test_api.py", suite_additions=True,
    )[0]["indices"] == [1]


@pytest.mark.parametrize("replacement", [
    'pytest.param(1, id="changed"), pytest.param(2, id="two"), pytest.param(3)',
    'pytest.param(2, id="two"), pytest.param(3)',
    'pytest.param(2, id="two"), pytest.param(1, id="one"), pytest.param(3)',
])
def test_existing_named_cases_cannot_be_changed_removed_or_reordered(replacement):
    cases = 'pytest.param(1, id="one"), pytest.param(2, id="two")'
    original = BASE.replace("[1]", f"[{cases}]")
    candidate = original.replace(cases, replacement)
    with pytest.raises(UnsupportedTestChange):
        added_tests(
            original.encode(), candidate.encode(), "tests/test_api.py", suite_additions=True,
        )


def test_class_additions_pass_policy_but_original_view_is_restored(tmp_path):
    path = source(tmp_path)
    path.write_text(BASE, encoding="utf-8")
    run_git(tmp_path, "add", ".")
    run_git(tmp_path, "commit", "-m", "original test class")
    before = path.read_bytes()
    path.write_text(BASE.replace("[1]", '[1, pytest.param(2, id="two")]') + METHOD,
                    encoding="utf-8")
    after = path.read_bytes()
    outcome = verify_test_tampering(
        WorkspaceManager.diff_summary(tmp_path),
        TaskConstraints(additive_test_roots=["tests"]), tmp_path,
    )
    assert outcome.passed
    with original_test_view(tmp_path, outcome):
        assert path.read_bytes() == before
    assert path.read_bytes() == after
