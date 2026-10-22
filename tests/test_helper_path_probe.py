import copy
import json
import sys
from collections import namedtuple
from enum import Enum

import pytest

from diagnostics.helper_path_probe import ORDER, TRACE, analyze, export_result, parse, program
from patchloop.errors import ContractError


def records(case, root):
    present = case == "present"
    return [{"stage": "before_call", "input": {"cwd": root}},
            {"stage": "result", "pylint_exit_code": 0 if present else 1,
             "pylint_stdout": "" if present else "F0010", "overflow": 0,
             "calls": [{"function": "get_ast", "arguments": {
                 "filepath": "src/project/file.py" if present else "src/project/__init__.py"},
                 "cwd": root}]},
            {"stage": "helper_path", "overflow": 0, "calls": []}]


def test_parity_normalizes_only_the_fixture_root_and_requires_actual_child_analysis():
    rows = {mode: records(mode.split("-")[0], "/tmp/" + mode) for mode in ORDER}
    assert analyze(rows)["information_gate"] == "REQUIRES_PUBLIC_EVIDENCE_REVIEW"
    changed = copy.deepcopy(rows)
    changed["missing-on"][1]["pylint_exit_code"] = 0
    with pytest.raises(ContractError, match="instrumentation changed"):
        analyze(changed)
    for mode in ("present-off", "present-on"):
        rows[mode][1]["calls"] = []
    with pytest.raises(ContractError, match="child-analysis"):
        analyze(rows)


@pytest.mark.parametrize("failure", ["timed_out", "truncated", "cleanup_failed", "overflow"])
def test_incomplete_observation_cannot_qualify(failure):
    rows = records("missing", "/tmp/example")
    receipt = {"status": "passed", "exit_code": 0, "setup_checks": {"status": "passed"}}
    if failure == "overflow":
        rows[-1]["overflow"] = 1
    else:
        receipt[failure] = True
    receipt["stdout"] = "\n".join(json.dumps(row) for row in rows)
    with pytest.raises(ContractError):
        parse(receipt)


def test_collector_records_real_return_branch_and_exception_with_explicit_coverage():
    namespace = {}
    exec(compile(TRACE.read_text(encoding="utf-8"), str(TRACE), "exec"), namespace)
    namespace["ModuleSpec"] = namedtuple("ModuleSpec", "name type location origin search")
    namespace["kind"] = Enum("Kind", "PY_SOURCE PY_NAMESPACE").PY_NAMESPACE
    fixture = """
def _spec_from_modpath(modpath, path=None, context=None):
    location = None
    if modpath == ['project']:
        found_spec = ModuleSpec('project', kind, None, None, ['/tmp/src/project'])
        return found_spec
    raise ImportError('control')
def file_info_from_modpath(modpath, path=None, context_file=None):
    return _spec_from_modpath(modpath, path, context_file)
"""
    exec(compile(fixture, "/workspace/astroid/modutils.py", "exec"), namespace)
    previous = sys.gettrace()
    try:
        sys.settrace(namespace["helper_trace"])
        namespace["file_info_from_modpath"](["project"])
        with pytest.raises(ImportError):
            namespace["_spec_from_modpath"](["src"])
        with pytest.raises(ImportError):
            namespace["_spec_from_modpath"](["unrelated"])
    finally:
        sys.settrace(previous)
    rows = namespace["helper_calls"]
    assert len(rows) == 3 and namespace["helper_overflow"] == 0
    assert rows[1]["return"]["type"] == "PY_NAMESPACE"
    assert rows[1]["lines"] and rows[1]["states"] and rows[1]["returned"]
    assert rows[2]["return"] is None and rows[2]["exceptions"][0]["type"] == "ImportError"
    assert namespace["helper_counts"]["_spec_from_modpath"] == 3
    assert namespace["helper_selected"]["_spec_from_modpath"] == 2


def test_program_pair_only_changes_observer_activation():
    template = '''PRESENT = False
entry = next(e for e in md.distribution("pylint").entry_points if e.name == "pylint")
sys.setprofile(observe)
try:
    entry.load()()
finally:
    sys.setprofile(None)
'''
    off, on = (program(template, "missing-" + mode) for mode in ("off", "on"))
    assert off.replace("helper_trace if False", "helper_trace if True") == on
    assert len(on) < 8000
    with pytest.raises(ContractError, match="unknown"):
        program(template, "unregistered")


def test_completed_result_export_stays_in_its_own_root(tmp_path):
    result = {"paid_calls": 0, "information_gate": "REQUIRES_PUBLIC_EVIDENCE_REVIEW"}
    export_result(tmp_path, result)
    assert json.loads((tmp_path / "result.json").read_bytes()) == result
