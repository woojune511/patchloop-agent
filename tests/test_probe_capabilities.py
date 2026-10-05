"""Capability checks distinguish import/process success from library execution."""

import sys
from types import ModuleType

import pytest

from diagnostics.probe_capabilities import (
    SUCCESS_MARKER,
    operation_program,
    run_operation_canary,
)


class Sandbox:
    def __init__(self, result):
        self.result = result

    def run_probe(self, *args, **kwargs):
        return self.result


@pytest.mark.parametrize("result", [
    {"status": "passed", "exit_code": 0, "stdout": "IMPORT_OK\n"},
    {"status": "passed", "exit_code": 0, "stdout": "caught operation error\n"},
    {"status": "failed", "exit_code": 1, "stdout": SUCCESS_MARKER},
    {"status": "passed", "exit_code": 0, "stdout": SUCCESS_MARKER, "cleanup_failed": True},
    {"status": "passed", "exit_code": 0, "stdout": SUCCESS_MARKER, "timed_out": True},
])
def test_incomplete_operation_or_cleanup_does_not_pass(result, tmp_path):
    receipt = run_operation_canary(
        Sandbox(result), tmp_path, "marshmallow", execution_identity={},
    )
    assert not receipt["passed"]
    assert receipt["result"] == result


def test_successful_operation_receipt_preserves_program_and_result(tmp_path):
    result = {"status": "passed", "exit_code": 0, "stdout": SUCCESS_MARKER + "\n"}
    receipt = run_operation_canary(
        Sandbox(result), tmp_path, "marshmallow", execution_identity={},
    )
    assert receipt["passed"]
    assert "schema.validate" in receipt["program"]
    assert receipt["program_hash"].startswith("sha256:")


def test_marshmallow_canary_reaches_validation_after_successful_import(monkeypatch, capsys):
    module = ModuleType("marshmallow")

    class Schema:
        def validate(self, data):
            raise AttributeError("module 'collections' has no attribute 'Mapping'")

    module.Schema = Schema
    module.fields = type("Fields", (), {"Integer": staticmethod(lambda **kwargs: object())})
    monkeypatch.setitem(sys.modules, "marshmallow", module)
    exec("import marshmallow", {})
    with pytest.raises(AttributeError, match="Mapping"):
        exec(operation_program("marshmallow"), {})
    assert SUCCESS_MARKER not in capsys.readouterr().out


def test_panel_rejects_broken_operation_after_import_pass(monkeypatch, tmp_path):
    from diagnostics import current_dev20 as panel
    from patchloop.dev.state import DevJournal
    from patchloop.errors import ContractError

    class ImportOnlySandbox:
        def run_probe(self, source, question, program, **kwargs):
            if "IMPORT_OK" in program:
                return {"exit_code": 0, "stdout": "IMPORT_OK\n"}
            return {"status": "failed", "exit_code": 1, "stdout": "",
                    "stderr": "AttributeError: collections.Mapping"}

    monkeypatch.setattr(panel.old.driver, "environment", lambda req: (
        None, tmp_path, ImportOnlySandbox(), {},
    ))
    with pytest.raises(ContractError, match="public operation failed"):
        panel.preflight_row(tmp_path, {
            "index": 1, "instance_id": "marshmallow-code__marshmallow-1343",
        }, None)
    events = DevJournal(tmp_path, panel.JOURNAL).events()
    assert [event["event_type"] for event in events] == [
        "import_canary_finished", "operation_canary_finished",
    ]
    assert not events[-1]["payload"]["passed"]
