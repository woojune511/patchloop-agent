"""Cost-only forks retain a mini/48k checkpoint; all provider responses are synthetic."""
from __future__ import annotations

import json
import shutil
from decimal import Decimal
from pathlib import Path

import pytest
import yaml
from test_checkpoint_comparison import install_sdk
from test_checkpoint_continuation import call, stop_steps
from test_dev_probes import FakeProbe
from test_observation_comparison import resolver

from diagnostics import cost_cap_continuation as diagnostic
from diagnostics.checkpoint_continuation import ScriptedClient
from diagnostics.declaration_checkpoint import Source
from patchloop.agent.model import OpenAIResponsesAdapter
from patchloop.dev import runner
from patchloop.dev.contracts import DevRunRequest
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError
from patchloop.runtime import repository_root
from patchloop.sandbox import LocalSandbox
from patchloop.util import canonical_json, sha256_bytes


@pytest.fixture(scope="module")
def source(tmp_path_factory):
    root = tmp_path_factory.mktemp("mini-cost-stop")
    task = root / "task"
    shutil.copytree(repository_root() / "tasks/smoke/csv-quoted-newline", task)
    public = task / "public.yaml"
    spec = yaml.safe_load(public.read_text(encoding="utf-8"))
    spec["split"] = "dev-train"
    public.write_text(yaml.safe_dump(spec), encoding="utf-8")
    read = call("read_file", {"path": "mini_data_utils/csvlite.py",
                             "start_line": 1, "end_line": 90}, "inspect")
    read["arguments"]["turn_decision"]["evidence_goal"] = "Inspect current source."
    client = ScriptedClient([[read]])
    request = DevRunRequest(
        provider="openai", task=public, model="gpt-5.4-mini-2026-03-17",
        reasoning_effort="xhigh", max_cost_usd=Decimal("0.0007"),
        env_file=root / "absent.env", state_root=root / "state", context_policy="segmented-v1",
        retained_source_chars=48000, evaluation_reserve_seconds=330, enable_probes=True,
        repair_recheck=True,
    )
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("socket.socket.connect", lambda *_: pytest.fail("network forbidden"))
        patch.setattr(runner, "_resolve_task_file", resolver(runner._resolve_task_file))
        patch.setattr(runner, "_live_task_is_admitted", lambda *a, **k: None)
        patch.setattr(runner, "_live_source_preflight", lambda *a, **k: None)
        patch.setattr(runner, "_live_sandbox_preflight", lambda *a, **k: LocalSandbox())
        patch.setattr(runner, "DockerProbeSandbox", lambda **kw: FakeProbe(status="passed"))
        patch.setattr(runner, "load_exact_openai_api_key", lambda _: "synthetic")
        patch.setattr(runner, "OpenAIResponsesAdapter", lambda config, **kw:
                      OpenAIResponsesAdapter(config, api_key="synthetic", client=client))
        result = runner.run_dev(request)["runs"][0]
    assert result["terminal"] == "COST_CAP_REACHED", result
    assert result["call_counts"]["model"] == 1
    journal = DevJournal(request.state_root, result["run_id"])
    return Source(request.state_root, result["run_id"], sha256_bytes(journal.path.read_bytes()),
                  sha256_bytes(journal.envelope_path.read_bytes()), public,
                  sha256_bytes(public.read_bytes()))


@pytest.fixture
def prepared(source, tmp_path, monkeypatch):
    monkeypatch.setattr(diagnostic.live, "clean_implementation", lambda: None)
    monkeypatch.setattr(diagnostic.live, "check_environment", lambda *a: {"status": "READY"})
    monkeypatch.setattr(runner, "_resolve_task_file", resolver(runner._resolve_task_file))
    monkeypatch.setattr("socket.socket.connect", lambda *_: pytest.fail("network forbidden"))
    return diagnostic.prepare([source], source.root.parent / "absent.env", tmp_path / "result",
                              Decimal("1.20"), tmp_path / "plan")


def test_prepare_restores_same_configuration_and_keeps_parent(source, prepared):
    plan = json.loads(Path(prepared["manifest"]).read_bytes())
    root = Path(prepared["manifest"]).parent
    first = json.loads((root / "1-first.json").read_bytes())
    branch = DevJournal(root / "1", source.run_id)
    env = branch.load_envelope()
    assert env.model == first["model"] == "gpt-5.4-mini-2026-03-17"
    assert env.retained_source_chars == 48000 and env.evaluation_reserve_seconds == 330
    budget = json.loads(first["input"][-1]["content"])["state"]["remaining_budget"]
    assert budget["model_calls"] == 39 and budget["tool_actions"] == 99
    assert budget["cost"]["remaining"] == 1_200_000_000
    assert budget["cost"]["settled_usage"] == 165_000
    assert prepared["actual_provider_calls"] == prepared["new_cost_nanos"] == 0
    assert not prepared["paid_execution_authorized"]
    assert not Path(plan["result_root"]).exists()
    assert sha256_bytes(
        DevJournal(source.root, source.run_id).path.read_bytes()) == source.journal_hash


@pytest.mark.parametrize("failure", [None, "count", "transport", "usage"])
def test_collect_preserves_counts_and_stops_on_uncertainty(source, prepared, monkeypatch, failure):
    path = Path(prepared["manifest"])
    client = ScriptedClient(stop_steps(), failure=failure)
    install_sdk(monkeypatch, source, [client])
    monkeypatch.setattr(runner, "DockerProbeSandbox", lambda **kw: FakeProbe(status="passed"))
    result = diagnostic.collect(path, prepared["manifest_hash"], Decimal("1.20"))
    if failure is None:
        assert result["rows"][0]["result"]["terminal"] == "AGENT_STOPPED", result
        assert result["rows"][0]["result"]["call_counts"]["model"] == 2
        assert result["new_cost_nanos"] == 165_000
        assert result["stop_reason"] is None
    else:
        assert result["stop_reason"] is not None
        assert result["rows"][0]["stop_remaining"]
    assert sha256_bytes(
        DevJournal(source.root, source.run_id).path.read_bytes()) == source.journal_hash
    with pytest.raises(ContractError, match="fresh output"):
        diagnostic.collect(path, prepared["manifest_hash"], Decimal("1.20"))


def test_changed_cap_or_parent_rejected(prepared):
    path = Path(prepared["manifest"])
    with pytest.raises(ContractError, match="approved cap"):
        diagnostic.collect(path, prepared["manifest_hash"], Decimal("2"))
    plan = json.loads(path.read_bytes())
    plan["rows"][0]["source"]["journal_hash"] = "changed"
    path.write_text(canonical_json(plan), encoding="utf-8")
    with pytest.raises(ContractError, match="parent identity"):
        diagnostic.collect(path, sha256_bytes(path.read_bytes()), Decimal("1.20"))
