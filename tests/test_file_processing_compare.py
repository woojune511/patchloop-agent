"""Local observer controls only; no saved-task, provider or Docker execution."""

from __future__ import annotations

import ast
import copy
import json
import os
import sys
from pathlib import Path

import pytest

from diagnostics import file_processing_compare as diagnostic
from patchloop.artifacts import ArtifactStore
from patchloop.dev import probe_invocation
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError
from patchloop.util import sha256_bytes, sha256_json


def test_program_preserves_exact_authored_source_and_rejects_changed_hash():
    source = "# unchanged Unicode: 대상\r\nrecord_observation({'x': '\\n'})\r\n"
    binding = {
        "program_hash": sha256_bytes(source.encode()), "case_id": "local-fixture",
        "definition": {"entrypoint": "os.getcwd", "observation_channel": probe_invocation.CHANNEL},
    }
    execution = diagnostic.program(source, binding)
    saved = [node.value.value for node in ast.walk(ast.parse(execution))
             if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant)
             and any(isinstance(target, ast.Name) and target.id == "_pr_source"
                     for target in node.targets)]
    assert saved == [source]
    assert binding["program_hash"] == sha256_bytes(saved[0].encode())
    with pytest.raises(ContractError, match="original program changed"):
        diagnostic.program(source + "# changed\n", binding)


@pytest.fixture
def observation(monkeypatch):
    saved = {
        "call_observation": {"calls": [{
            "call_id": "call-1", "arguments": {"args": [], "kwargs": {}},
            "cwd": "/tmp/patchloop-case/failing", "outcome": "returned",
        }]},
        "observed_json": "false", "comparison": "mismatched",
    }
    result = copy.deepcopy(saved)
    monkeypatch.setattr(diagnostic.reproduction, "compare", lambda *_: {"reproduction": result})
    receipt = {
        "status": "passed", "exit_code": 0, "setup_checks": {"status": "not_checked", "checks": []},
        "execution_policy": {"cleanup_status": "confirmed"},
        "stdout": diagnostic.MARKER + json.dumps({"complete": True, "events": []}),
    }
    return receipt, saved, result


def test_parse_accepts_only_same_call_and_observation(observation):
    receipt, saved, result = observation
    parsed = diagnostic.parse(receipt, {}, saved)
    assert parsed["saved_call_parity"] is True and parsed["reproduction"] == result
    assert parsed["trace"]["complete"] is True


@pytest.mark.parametrize("change", ["incomplete", "arguments", "outcome"])
def test_parse_rejects_incomplete_trace_or_changed_call(observation, change):
    receipt, saved, result = observation
    if change == "incomplete":
        receipt["stdout"] = diagnostic.MARKER + json.dumps({"complete": False, "events": []})
    elif change == "arguments":
        result["call_observation"]["calls"][0]["arguments"]["args"] = ["different.py"]
    else:
        result["call_observation"]["calls"][0]["outcome"] = "raised"
    with pytest.raises(ContractError, match="incomplete processing trace|inputs or outcomes"):
        diagnostic.parse(receipt, {}, saved)


@pytest.fixture
def reusable_receipt(tmp_path):
    root = tmp_path / "settled-diagnostic"
    journal = DevJournal(root, "run_dev_fileprocessing")
    execution, diff_hash = "print('same authored execution')", sha256_bytes(b"candidate2 diff")
    receipt = {"status": "passed", "exit_code": 0, "stdout": "captured original result"}
    ref = ArtifactStore(root / "artifacts").put_json(receipt).model_dump(mode="json")
    journal.append("processing_comparison_frozen", {"original_program_hash": "fixture"})
    journal.append("processing_probe_started", {
        "condition": "candidate2", "diff_hash": diff_hash,
        "identity": {"run_id": journal.run_id, "action_id": "candidate2",
                     "input_hash": sha256_json({"execution": execution, "diff": diff_hash})},
    })
    journal.append("processing_probe_finished", {"condition": "candidate2", "receipt": ref})
    journal.append("processing_comparison_stopped", {
        "reason": "setup not confirmed", "retry": False,
    })
    return root, journal, execution, diff_hash, receipt, ref


def test_reuse_requires_exact_settled_first_execution(reusable_receipt):
    root, journal, execution, diff_hash, receipt, ref = reusable_receipt
    before = journal.path.read_bytes()
    assert diagnostic.reuse_candidate2(root, execution, diff_hash) == (receipt, ref)
    assert journal.path.read_bytes() == before
    with pytest.raises(ContractError, match="execution identity"):
        diagnostic.reuse_candidate2(root, execution + "\n# changed", diff_hash)
    with pytest.raises(ContractError, match="execution identity"):
        diagnostic.reuse_candidate2(root, execution, sha256_bytes(b"different candidate"))
    journal.append("processing_probe_started", {"condition": "candidate3"})
    with pytest.raises(ContractError, match="single settled first probe"):
        diagnostic.reuse_candidate2(root, execution, diff_hash)


def test_reuse_rejects_changed_receipt_bytes(reusable_receipt):
    root, _, execution, diff_hash, _, ref = reusable_receipt
    Path(ref["path"]).write_bytes(b'{"status":"tampered"}')
    with pytest.raises(ContractError, match="reused receipt changed"):
        diagnostic.reuse_candidate2(root, execution, diff_hash)


@pytest.fixture
def observer():
    namespace = {}
    exec(compile(diagnostic.TRACE.read_text(encoding="utf-8"), str(diagnostic.TRACE), "exec"),
         namespace)
    return namespace


def selected_functions():
    module = {}
    exec(compile(
        "def get_module_files(src_directory):\n"
        "    directory = src_directory\n"
        "    filenames = ['file.py']\n"
        "    dirnames = []\n"
        "    return [directory + '/' + filename for filename in filenames]\n",
        "/workspace/astroid/modutils.py", "exec",
    ), module)
    exec(compile(
        "class Module:\n"
        "    def __init__(self, path):\n"
        "        self.name, self.file, self.body = 'file', path, [object(), object()]\n"
        "def file_build(self, path, modname=None):\n"
        "    return Module(path)\n",
        "/workspace/astroid/builder.py", "exec",
    ), module)
    return module["get_module_files"], module["file_build"]


def capture(observer, monkeypatch, cwd, body, **limits):
    previous = sys.gettrace()
    with monkeypatch.context() as patcher:
        patcher.setattr(os, "getcwd", lambda: cwd)
        observer["install_processing_trace"](**limits)
        try:
            body()
        finally:
            report = observer["finish_processing_trace"]()
            assert sys.gettrace() is previous
    return report


def test_observer_records_selected_files_and_built_module_body(observer, monkeypatch):
    selected, build = selected_functions()
    cwd = "/tmp/patchloop-case/failing"

    def body():
        assert selected(cwd) == [cwd + "/file.py"]
        assert len(build(None, cwd + "/file.py").body) == 2

    report = capture(observer, monkeypatch, cwd, body)
    assert report["complete"] is True and report["overflow"] is False
    assert report["counts"]["recorded_calls"] == report["counts"]["closed_calls"] == 2
    rows = {row["function"]: row for row in report["calls"]}
    selected_row = next(row for name, row in rows.items() if name.endswith("get_module_files"))
    built_row = next(row for name, row in rows.items() if name.endswith("file_build"))
    assert selected_row["return_seen"] and selected_row["return_value"] == [cwd + "/file.py"]
    assert built_row["return_value"] == {
        "type": "Module", "name": "file", "file": cwd + "/file.py", "body_length": 2,
        "package": None,
    }


def test_observer_excludes_unrelated_working_directory(observer, monkeypatch):
    selected, _ = selected_functions()
    report = capture(observer, monkeypatch, "/tmp/unrelated",
                     lambda: selected("/tmp/patchloop-case/failing"))
    assert report["complete"] is True and report["calls"] == []
    assert report["counts"]["selected_calls"] == 0


def test_observer_overflow_is_incomplete_and_restores_previous_trace(observer, monkeypatch):
    selected, _ = selected_functions()
    original = sys.gettrace()

    def previous_trace(frame, event, arg):
        return previous_trace

    sys.settrace(previous_trace)
    try:
        cwd = "/tmp/patchloop-case/failing"
        report = capture(observer, monkeypatch, cwd,
                         lambda: (selected(cwd), selected(cwd)), max_calls=1)
        assert report["complete"] is False and report["overflow"] is True
        assert report["counts"]["dropped_calls"] >= 1
        assert sys.gettrace() is previous_trace
    finally:
        sys.settrace(original)
