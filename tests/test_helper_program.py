"""Local helper admission tests; validation must never run submitted code."""

import pytest

from patchloop.dev import helper_program
from patchloop.errors import ContractError
from patchloop.util import sha256_bytes


def test_plain_helper_uses_common_setup_and_a_local_fixture_without_execution():
    source = (
        "from pathlib import Path\nfrom tempfile import TemporaryDirectory\n"
        "with TemporaryDirectory() as work:\n"
        "    root = Path(work)\n"
        "    check_setup('fixture_name', root.name, root.name)\n"
        "    raise RuntimeError('must not execute during validation')\n"
    )
    assert helper_program.validate(source) is None
    assert "automatically supplies only check_setup" in helper_program.DESCRIPTION
    assert "with TemporaryDirectory() as work:" in helper_program.DESCRIPTION
    for name in helper_program.ORIGINAL_ONLY_APIS:
        assert name in helper_program.DESCRIPTION


@pytest.mark.parametrize("name", sorted(helper_program.ORIGINAL_ONLY_APIS))
def test_unbound_original_only_name_has_structured_no_dispatch_error(name):
    source = f"from pathlib import Path\nresult = {name}()\n"
    with pytest.raises(ContractError) as raised:
        helper_program.validate(source)
    error = raised.value
    assert error.details["invalid_fields"] == [{
        "path": "/python_source", "requirement": str(error),
    }]
    assert error.details["helper_program_error"] == {
        "kind": "unavailable_api", "source_hash": sha256_bytes(source.encode()),
        "names": [name], "line": 2,
    }


@pytest.mark.parametrize("source", [
    "from deliberately_missing_package import observed_target\nobserved_target()\n",
    "from deliberately_missing_package import target as observed_target\nobserved_target()\n",
    "def reproduction_workspace():\n    return '/tmp'\nreproduction_workspace()\n",
    "def helper(observed_target):\n    return observed_target()\n",
    "def helper():\n    record_observation = print\n    return lambda: record_observation(1)\n",
    "values = [observed_target for observed_target in range(3)]\n",
    "comment = 'observed_target() reproduction_workspace() record_observation()'\n",
    "class Helper:\n    observed_target = print\n    observed_target('ok')\n",
])
def test_imports_aliases_local_definitions_closures_and_strings_are_not_api_misuse(source):
    assert helper_program.validate(source) is None


def test_class_namespace_does_not_bind_a_method_global_reference():
    source = ("class Helper:\n    observed_target = print\n"
              "    def run(self):\n        observed_target()\n")
    with pytest.raises(ContractError) as raised:
        helper_program.validate(source)
    assert raised.value.details["helper_program_error"]["names"] == ["observed_target"]


@pytest.mark.parametrize("source,line", [
    ("value = 1\nif True print(value)\n", 2),
    ("return 1\n", 1),
])
def test_syntax_and_compile_errors_precede_any_execution(source, line):
    with pytest.raises(ContractError) as raised:
        helper_program.validate(source)
    assert raised.value.details["helper_program_error"] == {
        "kind": "syntax_error", "source_hash": sha256_bytes(source.encode()),
        "names": [], "line": line,
    }


@pytest.mark.parametrize("source", [
    "missing_target_name()\n",
    "raise NameError('target implementation failed')\n",
    "assert False, 'intended behavior counterexample'\n",
    "eval('observed_target()')\n",
    "globals()['observed_target'] = print\nobserved_target('dynamic')\n",
    "from deliberately_missing_package import *\nobserved_target()\n",
])
def test_runtime_target_failures_and_dynamic_namespaces_are_not_classified(source):
    assert helper_program.validate(source) is None
