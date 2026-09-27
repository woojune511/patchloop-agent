"""Offline input integrity; fake provider/probe records do not measure agent quality."""
from __future__ import annotations

import copy
import json
import shutil
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest
import yaml
from test_decision_sampler import FakeClient
from test_dev_probes import FakeProbe

from diagnostics import mutation_advice_checkpoint as diagnostic
from patchloop.contracts import TaskEnvironment
from patchloop.dev import runner
from patchloop.dev.contracts import DevRunRequest
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError
from patchloop.runtime import repository_root
from patchloop.sandbox import LocalSandbox
from patchloop.util import canonical_json, sha256_bytes


@pytest.fixture(scope="module")
def source(tmp_path_factory):
    root = tmp_path_factory.mktemp("mutation-source")
    task = root / "task"
    shutil.copytree(repository_root() / "tasks/smoke/csv-quoted-newline", task)
    public = task / "public.yaml"
    value = yaml.safe_load(public.read_text(encoding="utf-8"))
    value["split"] = "dev-train"
    public.write_text(yaml.safe_dump(value), encoding="utf-8")

    def response(value):
        value.model = "gpt-5.4-2026-03-05"
        call = value.output[1]
        n = len(client.created)
        if n == 1:
            call.name = "read_file"
            arguments = {"path": "mini_data_utils/csvlite.py", "start_line": 1, "end_line": 90}
            mode = "inspect"
        elif n == 2:
            call.name = "run_probe"
            arguments = {"question": "Observe public behavior.", "python_source": "print('x')"}
            mode = "verify"
        else:
            call.name = "stop_task"
            arguments = {"reason_code": "insufficient_public_evidence", "summary": "Fixture end."}
            mode = "stop"
        arguments["turn_decision"] = {
            "mode": mode, "basis": "Synthetic checkpoint fixture.", "memory_update": None,
            "plan_update": "Read, probe, repair and check." if n == 1 else None,
            "evidence_goal": "Inspect the implementation." if n == 1 else None,
        }
        call.arguments = canonical_json(arguments)

    client = FakeClient(count_value=100, edit_response=response)
    request = DevRunRequest(
        provider="openai", model="gpt-5.4-2026-03-05", reasoning_effort="xhigh",
        context_policy="segmented-v1", planning_policy="brief-v1", enable_probes=True,
        max_cost_usd=Decimal("1.20"), env_file=root / "absent.env",
        task=public, state_root=root / "state",
    )
    task_dir, package = runner._resolve_task_file(public)
    package = package.model_copy(update={"environment": TaskEnvironment(
        evaluator_image="test/image@sha256:" + "a" * 64, image_digest="sha256:" + "a" * 64)})
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("socket.socket.connect", lambda *_: pytest.fail("network forbidden"))
        patch.setattr(runner, "_live_task_is_admitted", lambda *a, **k: None)
        patch.setattr(runner, "_live_source_preflight", lambda *a, **k: None)
        patch.setattr(runner, "_live_sandbox_preflight", lambda *a, **k: LocalSandbox())
        patch.setattr(runner, "DockerProbeSandbox", lambda **kw: FakeProbe(status="passed"))
        patch.setattr(runner, "load_exact_openai_api_key", lambda _: "synthetic")
        patch.setattr(runner, "_resolve_task_file", lambda _: (task_dir, package))
        patch.setattr(runner, "OpenAIResponsesAdapter", lambda config, **_: client.factory(config))
        result = runner.run_dev(request)["runs"][0]
    assert result["terminal"] == "AGENT_STOPPED", result
    assert len(client.created) == 3
    journal = DevJournal(request.state_root, result["run_id"])
    return diagnostic.Source(
        request.state_root, result["run_id"], sha256_bytes(journal.path.read_bytes()),
        sha256_bytes(journal.envelope_path.read_bytes()), public, sha256_bytes(public.read_bytes()))


@pytest.fixture(autouse=True)
def no_external_execution(monkeypatch):
    def forbidden(*_, **__):
        pytest.fail("offline preparation reached execution")
    monkeypatch.setattr("socket.socket.connect", forbidden)
    monkeypatch.setattr(runner, "load_exact_openai_api_key", forbidden)
    monkeypatch.setattr(runner, "OpenAIResponsesAdapter", forbidden)
    monkeypatch.setattr(runner, "DockerProbeSandbox", forbidden)


def test_real_loader_and_round_trip_packet(source, tmp_path):
    loaded = diagnostic.load(source)
    original = copy.deepcopy(loaded.request)
    b = diagnostic.project(original)
    assert original == loaded.request
    assert b["input"][:-1] == original["input"][:-1]
    assert any(x.get("type") == "reasoning" for x in b["input"])
    assert "PUBLIC_PROBE_OUTPUT" in canonical_json(b)
    assert json.loads(b["input"][-1]["content"])["state"]["completion_guidance"] == {
        **json.loads(original["input"][-1]["content"])["state"]["completion_guidance"],
        "next_action": None, "message": diagnostic.FACTUAL,
    }
    prepared = diagnostic.prepare(source, tmp_path / "packet")
    verified = diagnostic.validate(Path(prepared["packet"]), prepared["packet_hash"])
    assert verified["verified"] and verified["efficacy"] == "NOT_RUN"
    assert verified["model_calls"] == verified["input_counts"] == verified["tool_executions"] == 0
    with pytest.raises(ContractError, match="fresh output"):
        diagnostic.prepare(source, tmp_path / "packet")


@pytest.mark.parametrize("field", ["history", "tools", "model", "budget", "plan", "probe"])
def test_pair_rejects_additional_changes(source, field):
    a = diagnostic.load(source).request
    b = diagnostic.project(a)
    if field == "history":
        b["input"][3]["encrypted_content"] = "changed opaque continuation"
    elif field in {"tools", "model"}:
        b[field] = [] if field == "tools" else "other-model"
    elif field == "probe":
        item = next(x for x in reversed(b["input"]) if x.get("type") == "function_call_output")
        item["output"] = "different public observation"
    else:
        view = json.loads(b["input"][-1]["content"])
        view["state"]["remaining_budget" if field == "budget" else "working_plan"] = {}
        b["input"][-1]["content"] = canonical_json(view)
    with pytest.raises(ContractError, match="beyond the two"):
        diagnostic.verify_pair(a, b)


@pytest.mark.parametrize("field", ["stage", "message", "next_action"])
def test_unknown_advice_not_silently_rewritten(source, field):
    a = diagnostic.load(source).request
    view = json.loads(a["input"][-1]["content"])
    view["state"]["completion_guidance"][field] = "different"
    a["input"][-1]["content"] = canonical_json(view)
    with pytest.raises(ContractError, match="unsupported mutation"):
        diagnostic.project(a)


def test_source_and_packet_hash_binding(source, tmp_path):
    with pytest.raises(ContractError, match="source identity"):
        diagnostic.load(replace(source, journal_hash="sha256:" + "0" * 64))
    result = diagnostic.prepare(source, tmp_path / "packet")
    path = Path(result["packet"])
    with pytest.raises(ContractError, match="packet identity"):
        diagnostic.validate(path, "sha256:" + "0" * 64)
    packet = json.loads(path.read_bytes())
    artifact = Path(packet["requests"]["B"]["path"])
    artifact.write_bytes(artifact.read_bytes() + b" ")
    with pytest.raises(ContractError):
        diagnostic.validate(path, result["packet_hash"])
