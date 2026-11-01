"""Pure size-boundary controls; no repository, provider or container setup."""

import ast

import pytest

from patchloop import probe_limits
from patchloop.dev import probe_invocation, probe_requests, reproduction
from patchloop.dev.tools import DevToolGateway
from patchloop.errors import ContractError

BINDING = {
    "case_id": "sha256:" + "c" * 64,
    "definition": {"entrypoint": "public_api.entry",
                   "observation_channel": probe_invocation.CHANNEL},
}


@pytest.mark.parametrize("character", ["x", "'", "\\", "한", "\U000e0001"])
def test_full_authored_allowance_survives_observer_and_repr_expansion(character):
    source = "#" + character * (probe_limits.SOURCE_LIMIT_CHARS - 1)
    helper = DevToolGateway._probe_execution_source("observe", source)
    assert helper == source
    wrapped = DevToolGateway._probe_execution_source(
        "observe", source, reproduction_binding=BINDING)
    assert len(wrapped) > probe_limits.SOURCE_LIMIT_CHARS
    assert len(wrapped) <= probe_limits.EXECUTION_LIMIT_CHARS
    assert len(wrapped.encode("utf-8")) <= probe_limits.EXECUTION_LIMIT_BYTES
    assignment = ast.parse(wrapped).body[2]
    assert ast.literal_eval(assignment.value) == source


@pytest.mark.parametrize("binding", [None, BINDING], ids=["helper", "original"])
def test_authored_overflow_remains_a_source_field_error(binding):
    with pytest.raises(ContractError) as caught:
        DevToolGateway._probe_execution_source(
            "observe", "#" * (probe_limits.SOURCE_LIMIT_CHARS + 1),
            reproduction_binding=binding)
    assert [item["path"] for item in probe_requests.fields(caught.value)] == ["/python_source"]


def test_host_observer_budget_is_independent_and_does_not_blame_authored_source(monkeypatch):
    monkeypatch.setattr(probe_invocation, "observer", lambda channel: "")
    header_size = len(reproduction.program("", BINDING)) - len(repr(""))
    trace = "#" * (probe_limits.OBSERVER_LIMIT_CHARS - header_size)
    monkeypatch.setattr(probe_invocation, "observer", lambda channel: trace)
    assert reproduction.program("x" * probe_limits.SOURCE_LIMIT_CHARS, BINDING)
    monkeypatch.setattr(probe_invocation, "observer", lambda channel: trace + "#")
    with pytest.raises(ContractError, match="host reproduction observer") as caught:
        DevToolGateway._probe_execution_source("observe", "x", reproduction_binding=BINDING)
    assert [item["path"] for item in probe_requests.fields(caught.value)] == ["/"]
