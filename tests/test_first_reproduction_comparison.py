"""Public-checkpoint diagnostic plumbing only; no network or target execution."""

from __future__ import annotations

import copy
import json
import shutil
import subprocess
from decimal import Decimal

import pytest
import yaml
from test_dev_probes import FakeProbe
from test_probe_purpose import original_intent

from diagnostics import first_reproduction_comparison as diagnostic
from diagnostics.checkpoint_continuation import ScriptedClient
from patchloop.agent.model import OpenAIResponsesAdapter
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import TaskEnvironment
from patchloop.dev import runner
from patchloop.dev.contracts import DevLimits, DevRunRequest
from patchloop.dev.cost import DevCostLedger, pricing_for_model
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError
from patchloop.runtime import repository_root
from patchloop.sandbox import LocalSandbox


def stop(action_id="stop"):
    return {
        "name": "stop_task",
        "action_id": action_id,
        "arguments": {
            "reason_code": "insufficient_public_evidence",
            "summary": "Synthetic endpoint.",
        },
    }


def test_live_tracking_guard_checks_files_and_rejects_changed_or_untracked_code(
    tmp_path, monkeypatch,
):
    root = tmp_path / "repo"
    paths = ["patchloop/runtime.py", "diagnostics/comparison.py", "pyproject.toml",
             "uv.lock", "docker/probe_runner.py", "docker/Dockerfile.sandbox"]
    for name in paths:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("original\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "add", "--", *paths], cwd=root, check=True)
    subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                    "commit", "-qm", "fixture"], cwd=root, check=True)
    monkeypatch.setattr(diagnostic, "repository_root", lambda: root)
    # Use the real exact-file tracking guard, unlike simulated paid-row tests.
    diagnostic.clean_implementation()
    changed = root / "diagnostics/comparison.py"
    changed.write_text("changed\n", encoding="utf-8")
    with pytest.raises(ContractError, match="match HEAD exactly"):
        diagnostic.clean_implementation()
    changed.write_text("original\n", encoding="utf-8")
    (root / "patchloop/untracked.py").write_text("new\n", encoding="utf-8")
    with pytest.raises(ContractError, match="all be tracked"):
        diagnostic.clean_implementation()


@pytest.fixture(scope="module")
def source(tmp_path_factory):
    root = tmp_path_factory.mktemp("first-original-source")
    task = root / "task"
    shutil.copytree(repository_root() / "tasks/smoke/csv-quoted-newline", task)
    public = task / "public.yaml"
    value = yaml.safe_load(public.read_text(encoding="utf-8"))
    value["split"] = "dev-train"
    public.write_text(yaml.safe_dump(value), encoding="utf-8")
    reads = [
        {
            "name": "read_file",
            "action_id": f"read{i}",
            "arguments": {
                "path": "mini_data_utils/csvlite.py",
                "start_line": 1,
                "end_line": 10,
                "memory_update": None,
            },
        }
        for i in range(6)
    ]
    client = ScriptedClient([reads[:3], reads[3:], [stop()]])
    credential = root / "absent.env"
    request = DevRunRequest(
        provider="openai",
        model=diagnostic.MODEL,
        reasoning_effort="xhigh",
        max_output_tokens=40000,
        max_correction_output_tokens=25000,
        context_policy="segmented-v1",
        agent_policy="thin",
        planning_policy="none",
        enable_probes=True,
        reproduction_acquisition="bounded-v1",
        completion_cost_policy="completion-recovery-v1",
        evaluation_reserve_seconds=390,
        max_cost_usd=Decimal("4.50"),
        env_file=credential,
        task=public,
        state_root=root / "state",
        limits=DevLimits(
            max_model_calls=20,
            max_tool_actions=40,
            max_accepted_mutations=3,
            wall_time_seconds=2400,
        ),
    )
    task_dir, package = runner._resolve_task_file(public)
    package = package.model_copy(
        update={
            "environment": TaskEnvironment(
                evaluator_image="test/image@sha256:" + "a" * 64, image_digest="sha256:" + "a" * 64
            )
        }
    )
    old_schemas = runner.dev_tool_schemas

    def baseline_schemas(**kwargs):
        schemas = old_schemas(**kwargs)
        if kwargs.get("original_acquisition_pending"):
            for tool in schemas:
                if tool["name"] == "run_probe":
                    tool["description"] = (
                        "Synthetic long baseline description. " + tool["description"]
                    ).replace(diagnostic.probe_call_capture.EXCEPTION_DESCRIPTION,
                              diagnostic.LEGACY_EXCEPTION_DESCRIPTION)
        return schemas

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("socket.socket.connect", diagnostic.forbidden)
        patch.setattr(runner, "_live_task_is_admitted", lambda *a, **k: None)
        patch.setattr(runner, "_live_source_preflight", lambda *a, **k: None)
        patch.setattr(runner, "_live_sandbox_preflight", lambda *a, **k: LocalSandbox())
        patch.setattr(runner, "DockerProbeSandbox", lambda **kw: FakeProbe(status="passed"))
        patch.setattr(runner, "load_exact_openai_api_key", lambda _: "synthetic")
        patch.setattr(runner, "_resolve_task_file", lambda _: (task_dir, package))
        patch.setattr(runner, "dev_tool_schemas", baseline_schemas)
        patch.setattr(
            runner,
            "OpenAIResponsesAdapter",
            lambda config, **_: OpenAIResponsesAdapter(config, api_key="synthetic", client=client),
        )
        result = runner.run_dev(request)["runs"][0]
    assert result["terminal"] == "AGENT_STOPPED", result
    journal = DevJournal(request.state_root, result["run_id"])
    cut = [e for e in journal.events() if e["event_type"] == "model_input_prepared"][-1]
    return (
        diagnostic.source_record(request.state_root, result["run_id"], public),
        cut["sequence"],
        credential,
    )


def plan_for(source, tmp_path):
    saved, cut, credential = source
    return diagnostic.controls(saved, cut, credential, tmp_path / "result")


@pytest.fixture(autouse=True)
def synthetic_environment(source, monkeypatch):
    task_dir, package = runner._resolve_task_file(source[0].public_path)
    package = package.model_copy(
        update={
            "environment": TaskEnvironment(
                evaluator_image="test/image@sha256:" + "a" * 64, image_digest="sha256:" + "a" * 64
            )
        }
    )
    monkeypatch.setattr(runner, "_resolve_task_file", lambda _: (task_dir, package))
    monkeypatch.setattr("socket.socket.connect", diagnostic.forbidden)


def branch_for(source, tmp_path, arm="B"):
    plan, loaded = plan_for(source, tmp_path)
    return diagnostic.restore(plan, loaded, tmp_path / arm, arm), plan, loaded


def execute(branch, plan, tmp_path, client, **kwargs):
    journal = DevJournal(tmp_path / "group", "run_dev_testfirstreproduction")
    group = DevCostLedger(Decimal(plan["new_cap_nanos"]) / 10**9, branch.pricing)
    return diagnostic.run_branch(
        branch, group, journal, ArtifactStore(tmp_path / "artifacts"), client=client, **kwargs
    )


def test_pair_keeps_all_public_input_and_parameter_schema(source, tmp_path):
    plan, loaded = plan_for(source, tmp_path)
    a, b = loaded.requests["A"], loaded.requests["B"]
    assert a["input"] == diagnostic.public_input(loaded.bundle["request"]["input"])
    assert a["input"] == b["input"]
    assert any(item.get("type") == "reasoning" for item in loaded.bundle["request"]["input"])
    assert not any(item.get("type") == "reasoning" for item in a["input"])
    assert plan["pair"]["changed_fields"] == ["tools.run_probe.description"]
    assert plan["remaining_budget"]["tool_actions"] == 34
    assert plan["new_cap_nanos"] == 2 * plan["row_new_cap_nanos"]
    bad = copy.deepcopy(b)
    diagnostic.probe_tool(bad)["parameters"]["required"] = []
    with pytest.raises(ContractError, match="only in"):
        diagnostic.verify_pair(a, bad)


@pytest.mark.parametrize("comparison", ["description", "model", "helper"])
def test_prepare_and_validate_are_offline_and_single_use(
    source, tmp_path, monkeypatch, comparison,
):
    for name in ("load_exact_openai_api_key", "OpenAIResponsesAdapter", "DockerProbeSandbox"):
        monkeypatch.setattr(runner, name, diagnostic.forbidden)
    monkeypatch.setattr("socket.socket.connect", diagnostic.forbidden)
    saved, cut, credential = source
    output, results = tmp_path / "prepared", tmp_path / "results"
    restored = []
    restore = diagnostic.restore

    def capture_branch(*args, **kwargs):
        branch = restore(*args, **kwargs)
        restored.append(branch)
        return branch

    monkeypatch.setattr(diagnostic, "restore", capture_branch)
    receipt = diagnostic.prepare(
        saved, cut, credential, results, output, comparison=comparison,
    )
    assert all(
        receipt[key] == 0
        for key in ("provider_calls", "input_count_calls", "credential_reads", "target_executions")
    )
    assert not credential.exists() and not results.exists()
    plan, _ = diagnostic.validate(output / "manifest.json", receipt["manifest_hash"])
    with pytest.raises(ContractError, match="approved cap"):
        diagnostic.validate(output / "manifest.json", receipt["manifest_hash"], Decimal("1"))
    with pytest.raises(ContractError, match="fresh output"):
        diagnostic.prepare(saved, cut, credential, results, output, comparison=comparison)
    assert plan["paid_execution_authorized"] is False
    if comparison in {"model", "helper"}:
        assert [branch.arm for branch in restored] == plan["order"]
        assert plan["order"] == (["B"] if comparison == "helper" else ["A", "B"])
        assert plan["new_cap_nanos"] == plan["row_new_cap_nanos"] * len(restored)
        expected_group = 0
        for branch in restored:
            model = diagnostic.MODELS[branch.arm]
            assert branch.request.model == branch.envelope.model == model
            assert branch.pricing == pricing_for_model(model)
            assert branch.envelope.model_hash == runner._model_hash(branch.request, branch.pricing)
            assert branch.initial_spent_nanos == plan["historical_spent_nanos"] > 0
            assert branch.request.max_cost_usd * 10**9 == (
                branch.initial_spent_nanos + plan["row_new_cap_nanos"]
            )
            rehearsal = receipt["rehearsals"][branch.arm]
            assert rehearsal["admitted_output_tokens"] == [40000, 25000]
            assert rehearsal["synthetic_input_tokens_per_call"] == 60000
            price = DevCostLedger(Decimal("100"), branch.pricing)
            costs = [price.settle(input_tokens=60000, cached_input_tokens=0, output_tokens=n)
                     for n in (40000, 25000)]
            usage = branch.journal.provider_usage()
            assert [row["cost_nanos"] for row in usage[-2:]] == costs
            assert sum(row["cost_nanos"] for row in usage[:-2]) == branch.initial_spent_nanos
            assert rehearsal["new_cost_nanos"] == sum(costs)
            expected_group += sum(costs)
        journal = DevJournal(output, "run_dev_firstreproductionpreparation")
        assert sum(e["payload"]["provisional_cost_nanos"] for e in journal.events()
                   if e["event_type"] == "new_usage_recorded") == expected_group


def test_model_pair_changes_only_model_after_symmetric_forecast_projection(source, tmp_path):
    saved, cut, credential = source
    plan, loaded = diagnostic.controls(
        saved, cut, credential, tmp_path / "result", comparison="model",
    )
    a, b = loaded.requests["A"], loaded.requests["B"]
    assert {**a, "model": b["model"]} == b
    assert a["tools"] == loaded.public["tools"]
    assert plan["pair"]["changed_fields"] == ["model"]
    assert plan["models"] == diagnostic.MODELS
    restored = copy.deepcopy(a)
    # Only the derived model-priced forecast is omitted; public facts remain exact.
    for index, original in enumerate(loaded.public["input"]):
        if original != restored["input"][index]:
            prior = json.loads(original["content"])
            after = json.loads(restored["input"][index]["content"])
            forecast = prior["state"]["remaining_budget"]["cost"].pop("completion_cost")
            assert forecast
            assert after == prior
            restored["input"][index] = original
    assert restored == loaded.public
    assert "completion_cost" in loaded.state["remaining_budget"]["cost"]
    bad = copy.deepcopy(b)
    bad["max_output_tokens"] = 25000
    with pytest.raises(ContractError, match="only in model"):
        diagnostic.verify_model_pair(a, bad)


def test_helper_followup_retains_long_description_and_changes_only_exception_contract(
    source, tmp_path,
):
    saved, cut, credential = source
    plan, loaded = diagnostic.controls(
        saved, cut, credential, tmp_path / "result", comparison="helper",
    )
    request = loaded.requests["B"]
    baseline = diagnostic.model_requests(loaded.public)["B"]
    old_description = diagnostic.probe_tool(baseline)["description"]
    new_description = diagnostic.probe_tool(request)["description"]
    assert new_description.startswith("Synthetic long baseline description.")
    assert new_description.replace(diagnostic.probe_call_capture.EXCEPTION_DESCRIPTION,
                                   diagnostic.LEGACY_EXCEPTION_DESCRIPTION) == old_description
    assert diagnostic.project(request, old_description) == baseline
    assert plan["schema"] == diagnostic.HELPER_SCHEMA
    assert plan["models"] == {"B": diagnostic.MODELS["B"]}
    assert plan["new_cap_nanos"] == plan["row_new_cap_nanos"]
    assert request["model"] == diagnostic.MODELS["B"]
    assert plan["pair"]["changed_fields"] == [
        "tools.run_probe.description.expected_exceptions"
    ]
    bad = copy.deepcopy(request)
    diagnostic.probe_tool(bad)["parameters"]["required"] = []
    with pytest.raises(ContractError, match="beyond exception paragraph"):
        diagnostic.verify_helper_request(loaded.public, bad)
    with pytest.raises(ContractError, match="one legacy exception paragraph"):
        diagnostic.helper_request(diagnostic.project(loaded.public, new_description))


def test_helper_collection_dispatches_only_full_model_and_stops_on_usage_uncertainty(
    source, tmp_path, monkeypatch,
):
    saved, cut, credential = source
    plan, loaded = diagnostic.controls(
        saved, cut, credential, tmp_path / "result", comparison="helper",
    )
    monkeypatch.setattr(diagnostic, "validate", lambda *args: (plan, loaded))
    monkeypatch.setattr(diagnostic, "clean_implementation", lambda: None)
    monkeypatch.setattr(diagnostic.live, "check_environment", lambda *a: {"status": "READY"})
    actual_run, attempted = diagnostic.run_branch, []

    def scripted(branch, group, journal, store):
        attempted.append(branch.arm)
        return actual_run(branch, group, journal, store,
                          client=ScriptedClient([[stop()]], failure="usage"))

    monkeypatch.setattr(diagnostic, "run_branch", scripted)
    preparation = tmp_path / "preparation"
    preparation.mkdir()
    receipt = diagnostic.collect(
        preparation / "manifest.json", "synthetic-approved", Decimal(plan["new_cap_nanos"]) / 10**9
    )
    assert attempted == ["B"]
    assert len(receipt["rows"]) == 1
    assert receipt["rows"][0]["arm"] == "B"
    assert receipt["stop_reason"] is not None
    assert receipt["billing_known"] is False


@pytest.mark.parametrize("cleanup_failed", [False, True])
def test_settled_original_ends_after_one_synthetic_probe(
    source,
    tmp_path,
    monkeypatch,
    cleanup_failed,
):
    synthetic = diagnostic.exposure.SyntheticProbe

    class CleanupProbe(synthetic):
        def run_probe(self, *args, **kwargs):
            result = super().run_probe(*args, **kwargs)
            result["cleanup_failed"] = cleanup_failed
            return result

    monkeypatch.setattr(diagnostic.exposure, "SyntheticProbe", CleanupProbe)
    branch, plan, _ = branch_for(source, tmp_path)
    call = {
        "name": "run_probe",
        "action_id": "first_original",
        "arguments": {
            "question": "Synthetic original observation.",
            "python_source": "record_observation(observed_target()('x').value)",
            "replay_action_id": None,
            "call_path": None,
            "memory_update": None,
            "purpose": {"kind": "original_requirement", **original_intent(branch.package.public)},
        },
    }
    client = ScriptedClient([[call], [stop("must_not_dispatch")]])
    receipt = execute(
        branch, plan, tmp_path, client, synthetic_probe_outcomes={"first_original": "passed"}
    )
    assert receipt["result"]["terminal"] == "FIRST_PROBE_SETTLED", receipt
    assert receipt["input_counts"] == receipt["model_dispatches"] == 1
    assert receipt["stop_remaining"] is cleanup_failed
    assert len(client.steps) == 1
    result = receipt["result"]["probe_result"]
    assert result["output"]["stdout"] == "SYNTHETIC_PROBE_ONLY"
    assert result["output"]["reproduction"]["comparison"] == "not_compared"
    assert receipt["task_acceptance"] == "NOT_RUN"
    count = copy.deepcopy(client.counted[0])
    created = copy.deepcopy(client.created[0])
    count.pop("timeout", None)
    created.pop("timeout", None)
    assert created == branch.selected
    assert count == {key: created[key] for key in count}
    counted = [
        e["payload"]["request_hash"]
        for e in DevJournal(tmp_path / "group", "run_dev_testfirstreproduction").events()
        if e["event_type"] == "actual_input_count_started"
    ]
    dispatched = [
        e["payload"]["request_hash"]
        for e in DevJournal(tmp_path / "group", "run_dev_testfirstreproduction").events()
        if e["event_type"] == "actual_dispatch_started"
    ]
    assert counted == dispatched
    new_actions = [
        e
        for e in branch.journal.events()[branch.inherited_events :]
        if e["event_type"] == "action_started"
    ]
    assert [e["payload"]["tool"] for e in new_actions] == ["run_probe"]


def test_protocol_correction_keeps_schema_and_fresh_continuation(source, tmp_path):
    branch, plan, _ = branch_for(source, tmp_path)
    client = ScriptedClient(
        [[{"name": "invalid_tool", "action_id": "bad", "arguments": {}}], [stop("corrected")]]
    )
    receipt = execute(branch, plan, tmp_path, client)
    assert receipt["result"]["terminal"] == "AGENT_STOPPED", receipt
    assert receipt["model_dispatches"] == 2
    assert client.created[0]["max_output_tokens"] == 40000
    assert client.created[1]["max_output_tokens"] == 25000
    assert client.created[0]["tools"] == client.created[1]["tools"]
    assert not any(item.get("type") == "reasoning" for item in client.created[0]["input"])
    # The correction may retain only its own new reasoning under ordinary policy.
    reasoning = [item for item in client.created[1]["input"] if item.get("type") == "reasoning"]
    assert all(item["id"] == "offline_reasoning_1" for item in reasoning)


@pytest.mark.parametrize("failure", ["count", "transport", "usage"])
def test_uncertainty_stops_entire_pair(source, tmp_path, monkeypatch, failure):
    plan, loaded = plan_for(source, tmp_path)
    # Entry controls are tested separately; collect still creates real journals
    # and uses the ordinary runner with a scripted provider in the first row.
    monkeypatch.setattr(diagnostic, "validate", lambda *args: (plan, loaded))
    monkeypatch.setattr(runner, "_require_tracked_clean_paths", lambda *a, **k: None)
    monkeypatch.setattr(diagnostic.live, "check_environment", lambda *a: {"status": "READY"})
    actual_run = diagnostic.run_branch
    attempted = []

    def scripted(branch, group, journal, store):
        attempted.append(branch.arm)
        return actual_run(
            branch, group, journal, store, client=ScriptedClient([[stop()]], failure=failure)
        )

    monkeypatch.setattr(diagnostic, "run_branch", scripted)
    preparation = tmp_path / "preparation"
    preparation.mkdir()
    receipt = diagnostic.collect(
        preparation / "manifest.json", "synthetic-approved", Decimal(plan["new_cap_nanos"]) / 10**9
    )
    assert attempted == ["A"]
    assert receipt["rows"][1] == {"arm": "B", "status": "NOT_RUN"}
    assert receipt["stop_reason"] is not None
