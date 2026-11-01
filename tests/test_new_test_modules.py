"""New pytest modules can declare imports without relaxing existing-file integrity."""

import pytest

from patchloop.test_additions import UnsupportedTestChange, added_tests


def test_new_module_allows_imports_docstring_and_reports_exact_test_selector():
    content = (b'"""A public regression."""\nfrom sample import resolve\nimport pytest\n'
               b'@pytest.mark.parametrize("value", [1, 2])\n'
               b'def test_value(value):\n    assert resolve(value) == value\n')
    assert added_tests(b"", content, "tests/test_new.py", new_file=True) == [{
        "path": "tests/test_new.py", "function": "test_value",
        "parameter_names": [], "indices": None,
    }]


def test_existing_empty_module_does_not_implicitly_gain_import_permission():
    content = b"import math\ndef test_value():\n    assert math.sqrt(4) == 2\n"
    with pytest.raises(UnsupportedTestChange, match="imports"):
        added_tests(b"", content, "tests/test_empty.py")


def test_new_module_flag_cannot_replace_an_existing_module():
    with pytest.raises(UnsupportedTestChange, match="no original file bytes"):
        added_tests(b"# Original file\n", b"def test_added(): pass\n", "tests/test_old.py",
                    new_file=True)


@pytest.mark.parametrize("setup", [
    b"pytestmark = pytest.mark.skip\n",
    b"def helper(): return 1\n",
    b"@pytest.fixture\ndef test_data(): return 1\n",
])
def test_new_module_setup_still_requires_supported_separation(setup):
    with pytest.raises(UnsupportedTestChange):
        added_tests(b"", b"import pytest\n" + setup + b"def test_added(): pass\n",
                    "tests/test_new.py", new_file=True)


def test_new_module_preserves_distinct_suite_and_repair_verify_selector_contracts():
    content = b"import math\nclass TestValue:\n    def test_value(self): assert math.sqrt(4) == 2\n"
    assert added_tests(b"", content, "tests/test_new.py", new_file=True, suite_additions=True) == [{
        "path": "tests/test_new.py", "function": "TestValue::test_value",
        "parameter_names": [], "indices": None,
    }]
    with pytest.raises(UnsupportedTestChange, match="classes"):
        added_tests(b"", content, "tests/test_new.py", new_file=True)
