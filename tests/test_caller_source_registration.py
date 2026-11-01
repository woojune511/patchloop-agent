"""Explicit prepared caller scopes survive the ordinary request/dispatch/recovery path."""

from __future__ import annotations

import copy
import json
import socket

import httpx
import pytest
from test_dev_dependency_sources import source_bundle  # noqa: F401
from test_dev_dependency_tools import source_call
from test_dev_planning import request as mock_request
from test_dev_segments import configured, records
from test_prepared_probe_dependencies import DependencyProbe, write_bundle
from typer.testing import CliRunner

from patchloop.cli import app
from patchloop.dev import runner
from patchloop.dev.contracts import DevModelTurn, DevRunEnvelope, DevRunRequest, RequestedTool
from patchloop.dev.dependency_sources import for_run, normalize_roots, parse_cli_roots
from patchloop.errors import ContractError, ResumeContractMismatch
from patchloop.prepared_probe_dependencies import _inventory
from patchloop.repair import RepairRunRequest
from patchloop.util import canonical_json, sha256_json


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("caller source validation must not make network requests")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbidden)


def caller_bundle(tmp_path, public):
    path = write_bundle(tmp_path / "prepared", public)
    caller = path.parent / "site-packages/caller/lint/expand.py"
    caller.parent.mkdir(parents=True)
    caller.write_bytes(b"def expand(items):\n    return list(items)  # PINNED_CALLER_BODY\n")
    data = json.loads(path.read_bytes())
    data["files"] = _inventory(path.parent / "site-packages")
    data["content_hash"] = sha256_json(data["files"])
    # Distribution and import directory deliberately differ: no name-based inference.
    data["wheel_lock"] = {"operator_caller_requirements": ["caller-dist==1.2"],
                          "source_metadata": {"project_name": "project"}}
    path.write_text(canonical_json(data), encoding="utf-8")
    return path


def test_empty_roots_keep_legacy_request_bytes_and_shared_repair_contract(tmp_path):
    original = mock_request(tmp_path, "none")
    explicit = DevRunRequest.model_validate({**original.model_dump(), "caller_source_roots": {}})
    assert original.model_dump_json() == explicit.model_dump_json()
    assert "caller_source_roots" not in explicit.model_dump()
    assert runner._model_hash(original, None) == runner._model_hash(explicit, None)
    assert "caller_source_roots" in RepairRunRequest.model_fields
    assert for_run(None, {}) is None


@pytest.mark.parametrize("enabled,descriptor", [(False, None), (True, None), (False, "pins.json")])
def test_mapping_requires_prepared_enabled_probe(tmp_path, enabled, descriptor):
    base = mock_request(tmp_path, "none").model_dump()
    with pytest.raises(ValueError, match="requires"):
        DevRunRequest.model_validate({**base, "enable_probes": enabled,
                                      "prepared_probe_dependencies": descriptor,
                                      "caller_source_roots": {"caller-dist": "caller"}})


@pytest.mark.parametrize("values", [
    ["caller"], ["caller=caller", "caller=elsewhere"],
    ["Caller_Dist=caller", "caller-dist=elsewhere"], ["caller=../private"],
    ["caller=caller/*"], ["caller==1.2=caller"],
])
def test_cli_mapping_rejects_ambiguous_or_unsafe_registration(values):
    with pytest.raises(ContractError):
        parse_cli_roots(values)


def test_cli_passes_explicit_distribution_root_map(monkeypatch, tmp_path):
    captured = []
    monkeypatch.setattr(runner, "run_dev", lambda request: captured.append(request) or {"ok": True})
    base = mock_request(tmp_path, "none")
    result = CliRunner().invoke(app, [
        "dev", "--provider", "mock", "--model", "mock-dev", "--task", str(base.task),
        "--enable-probes", "--prepared-probe-dependencies", str(tmp_path / "pins.json"),
        "--caller-source", "Caller_Dist=caller", "--caller-source", "other=other_module",
    ])
    assert result.exit_code == 0, result.output
    assert captured[0].caller_source_roots == {"caller-dist": "caller", "other": "other_module"}


def test_registry_requires_exact_caller_pin_and_explicit_root(source_bundle):  # noqa: F811
    prepared, _ = source_bundle
    assert normalize_roots({"CALLER": "caller"}) == {"caller": "caller"}
    assert for_run(prepared, {"caller": "caller"}).catalog()[0]["version"] == "1.2"
    with pytest.raises(ContractError, match="exact caller pin"):
        for_run(prepared, {"different-distribution": "caller"})
    with pytest.raises(ContractError, match="prepared probe dependencies"):
        for_run(None, {"caller": "caller"})


def test_normal_run_counts_scoped_tools_delivers_source_and_rejects_changed_resume(
    monkeypatch, tmp_path, smoke_package,
):
    class ReadThenStop:
        def __init__(self):
            self.calls = 0
            self.tools = []

        def next_turn(self, context, tools):
            self.tools.append(copy.deepcopy(tools))
            self.calls += 1
            if self.calls == 1:
                return DevModelTurn(tool_calls=[source_call(source_scope="dependency:caller-dist")])
            state = json.loads(context)
            assert "PINNED_CALLER_BODY" in canonical_json(state["dependency_sources"])
            return DevModelTurn(tool_calls=[RequestedTool(
                name="stop_task", action_id="done", arguments={
                    "reason_code": "insufficient_public_evidence",
                    "summary": "Source read verified.",
                }, turn_decision={"mode": "stop", "basis": "Stop the local registration test."},
            )])

    script = ReadThenStop()
    request, inputs, counted, _ = configured(monkeypatch, tmp_path, script=script)
    path = caller_bundle(tmp_path, smoke_package.public)
    request = request.model_copy(update={"enable_probes": True,
                                         "prepared_probe_dependencies": path,
                                         "caller_source_roots": {"caller-dist": "caller"}})
    monkeypatch.setattr(runner, "DockerProbeSandbox", DependencyProbe)
    provider = runner.OpenAIResponsesAdapter
    original_count = provider.count_input_tokens_v2
    counted_tools = []

    def count(self, payload, **kwargs):
        counted_tools.append(copy.deepcopy(payload["tools"]))
        return original_count(self, payload, **kwargs)

    monkeypatch.setattr(provider, "count_input_tokens_v2", count)
    result = runner.run_dev(request)["runs"][0]
    assert result["terminal"] == "AGENT_STOPPED", result
    assert len(inputs) == len(counted) == script.calls == 2
    assert inputs == counted and counted_tools == script.tools
    for tool in script.tools[0]:
        if tool["name"] in {"read_file", "search_files"}:
            assert tool["parameters"]["properties"]["source_scope"]["enum"] == [
                "repository", "dependency:caller-dist"]
    assert "PINNED_CALLER_BODY" in canonical_json(inputs[1])
    assert str(path) not in canonical_json(inputs)
    journal, _ = records(request)
    envelope_data = json.loads(journal.envelope_path.read_bytes())
    envelope = DevRunEnvelope.model_validate(envelope_data)
    assert envelope.caller_source_roots == request.caller_source_roots
    assert envelope.probe_dependencies is not None
    with pytest.raises(ValueError, match="snapshot"):
        DevRunEnvelope.model_validate({**envelope_data, "probe_dependencies": None})
    empty = envelope.model_copy(update={"caller_source_roots": {}})
    assert "caller_source_roots" not in empty.model_dump()
    before = journal.path.read_bytes()
    resumed = request.model_copy(update={"resume_run_id": result["run_id"]})
    assert runner.run_dev(resumed)["runs"][0] == result
    assert journal.path.read_bytes() == before and script.calls == 2
    with pytest.raises(ResumeContractMismatch):
        runner.run_dev(resumed.model_copy(update={"caller_source_roots": {"caller-dist": "other"}}))
    assert journal.path.read_bytes() == before and script.calls == 2


def test_unpinned_mapping_stops_normal_run_before_provider(monkeypatch, tmp_path, smoke_package):
    request, inputs, counted, _ = configured(monkeypatch, tmp_path)
    path = caller_bundle(tmp_path, smoke_package.public)
    request = request.model_copy(update={"enable_probes": True,
                                         "prepared_probe_dependencies": path,
                                         "caller_source_roots": {"unpinned": "caller"}})
    monkeypatch.setattr(runner, "DockerProbeSandbox", DependencyProbe)
    result = runner.run_dev(request)["runs"][0]
    assert result["terminal"] == "PREFLIGHT_FAILED", result
    assert inputs == counted == []
