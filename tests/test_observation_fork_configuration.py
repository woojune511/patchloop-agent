"""Same-configuration forks preserve effective policies; providers are scripted."""
from __future__ import annotations

import shutil
from decimal import Decimal

import pytest
import yaml
from test_checkpoint_continuation import call, stop_steps
from test_dev_probes import FakeProbe
from test_observation_comparison import resolver

from diagnostics import observation_exposure as diagnostic
from diagnostics.checkpoint_continuation import ScriptedClient
from diagnostics.declaration_checkpoint import Source
from patchloop.agent.model import OpenAIResponsesAdapter
from patchloop.dev import runner
from patchloop.dev.contracts import DevRunRequest
from patchloop.dev.cost import correction_output_ceiling
from patchloop.dev.state import DevJournal
from patchloop.runtime import repository_root
from patchloop.sandbox import LocalSandbox
from patchloop.util import sha256_bytes


@pytest.fixture(scope="module", params=["current", "thin"])
def configured_source(request, tmp_path_factory):
    policy = request.param
    root = tmp_path_factory.mktemp("fork-configuration-" + policy)
    task = root / "task"
    shutil.copytree(repository_root() / "tasks/smoke/csv-quoted-newline", task)
    public = task / "public.yaml"
    spec = yaml.safe_load(public.read_text(encoding="utf-8"))
    spec["split"] = "dev-train"
    public.write_text(yaml.safe_dump(spec), encoding="utf-8")
    read = call("read_file", {"path": "mini_data_utils/csvlite.py",
                             "start_line": 1, "end_line": 90}, "inspect")
    read["arguments"]["turn_decision"]["evidence_goal"] = "Read the current source."
    steps = [[read], *stop_steps()]
    if policy == "thin":
        for step in steps:
            for tool in step:
                tool["arguments"].pop("turn_decision")
                tool["arguments"]["memory_update"] = None
    client = ScriptedClient(steps)
    parent = DevRunRequest(
        provider="openai", task=public, model="gpt-5.4-mini-2026-03-17",
        reasoning_effort="medium", max_cost_usd=Decimal("1.20"),
        env_file=root / "absent.env", state_root=root / "state",
        context_policy="segmented-v1", segment_boundary_policy="size-only-v1",
        completion_cost_policy="completion-recovery-v1", max_output_tokens=40000,
        max_correction_output_tokens=25000, retained_source_chars=48000,
        evaluation_reserve_seconds=330, enable_probes=True,
        reproduction_acquisition="bounded-v1", probe_policy="cases-v1",
        probe_recheck="saved-program-v1", repair_recheck=True,
        repair_inspection_policy="current-failure-v1", agent_policy=policy,
        planning_policy="brief-v1" if policy == "current" else "none",
        history_search_policy="public-v1" if policy == "current" else "none",
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
        result = runner.run_dev(parent)["runs"][0]
    assert result["terminal"] == "AGENT_STOPPED", result
    assert result["call_counts"]["model"] == 2
    journal = DevJournal(parent.state_root, result["run_id"])
    return Source(parent.state_root, result["run_id"], sha256_bytes(journal.path.read_bytes()),
                  sha256_bytes(journal.envelope_path.read_bytes()), public,
                  sha256_bytes(public.read_bytes()))


@pytest.mark.parametrize("preserve", [True, False])
def test_fork_preserves_configuration_only_when_requested(
    configured_source, tmp_path, monkeypatch, preserve,
):
    source = configured_source
    historical = DevJournal(source.root, source.run_id)
    old = historical.load_envelope()
    cut = [e for e in historical.events() if e["event_type"] == "model_input_prepared"][-1]
    monkeypatch.setattr("socket.socket.connect", lambda *_: pytest.fail("network forbidden"))
    monkeypatch.setattr(runner, "_resolve_task_file", resolver(runner._resolve_task_file))
    branch = diagnostic.fork(source, cut["sequence"], tmp_path / "branch", "B",
        synthetic_cap_usd=Decimal("1.20"), preserve_parent_configuration=preserve)
    if preserve:
        fields = (
            "model", "reasoning_effort", "max_output_tokens", "max_correction_output_tokens",
            "reproduction_acquisition", "history_search_policy", "agent_policy",
            "retained_source_chars", "evaluation_reserve_seconds", "probe_recheck",
        )
        for field in fields:
            assert getattr(branch.request, field) == getattr(old, field), field
            assert getattr(branch.envelope, field) == getattr(old, field), field
        assert correction_output_ceiling(branch.request.max_output_tokens,
                                         branch.request.max_correction_output_tokens) == 25000
        assert branch.envelope.completion_cost_contract == old.completion_cost_contract
        assert branch.envelope.segment_contract == old.segment_contract
    else:
        # Existing observation comparisons intentionally use their full-model policy.
        assert branch.request.model == "gpt-5.4-2026-03-05"
        assert branch.request.reasoning_effort == "xhigh"
        assert branch.request.max_output_tokens == 25000
        assert branch.request.max_correction_output_tokens is None
        assert branch.request.reproduction_acquisition == "none"
        assert branch.request.history_search_policy == "none"
        assert branch.request.agent_policy == "current"
    assert branch.ledger.remaining_nanos == 1_200_000_000
    assert sha256_bytes(historical.path.read_bytes()) == source.journal_hash
    assert sha256_bytes(historical.envelope_path.read_bytes()) == source.envelope_hash
