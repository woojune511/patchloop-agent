"""Synthetic collector tests; no real credentials, network or Docker execution."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_checkpoint_continuation import call, stop_steps
from test_mutation_advice_checkpoint import source as source  # noqa: F401

from diagnostics import checkpoint_comparison as comparison
from diagnostics import checkpoint_continuation as continuation
from diagnostics import mutation_advice_checkpoint as checkpoint
from patchloop.agent import model
from patchloop.dev import runner
from patchloop.dev.cost import DevCostLedger, pricing_for_model
from patchloop.dev.model import MOCK_MUTATIONS
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError
from patchloop.sandbox import LocalSandbox
from patchloop.util import sha256_bytes, sha256_json


@pytest.fixture(scope="module")
def packet(source, tmp_path_factory):
    return checkpoint.prepare(source, tmp_path_factory.mktemp("live-pair") / "packet")


@pytest.fixture
def prepared(packet, source, tmp_path, monkeypatch):
    def forbidden(*a, **kw):
        pytest.fail("network forbidden")

    monkeypatch.setattr("socket.socket.connect", forbidden)
    monkeypatch.setattr(runner, "_require_tracked_clean_paths", lambda *a, **kw: None)
    monkeypatch.setattr(comparison, "check_environment", lambda *a: {"status": "READY"})
    return comparison.prepare(
        Path(packet["packet"]), packet["packet_hash"], source.root.parent / "absent.env",
        tmp_path / "result", tmp_path / "plan",
    )


def install_sdk(monkeypatch, source, clients):
    envelope = DevJournal(source.root, source.run_id).load_envelope()
    iterator = iter(clients)
    monkeypatch.setattr(model, "create_openai_client", lambda *a, **kw: next(iterator))
    monkeypatch.setattr(runner, "load_exact_openai_api_key", lambda _: "synthetic")
    monkeypatch.setattr(runner, "_live_source_preflight", lambda *a, **kw: None)
    monkeypatch.setattr(runner, "_live_sandbox_preflight", lambda *a, **kw: LocalSandbox())
    monkeypatch.setattr(runner, "DockerProbeSandbox",
                        lambda **kw: continuation.UnexecutedProbe(envelope, **kw))
    original_manifest = runner._manifest

    def local_manifest(**kwargs):
        kwargs["sandbox_backend"] = "local"
        manifest = original_manifest(**kwargs)
        identity = runner._sandbox_identity_hash(
            kwargs["request"].model_copy(update={"provider": "mock"}), kwargs["package"],
            kwargs.get("probe_dependencies"),
        )
        return manifest.model_copy(update={"sandbox_identity_hash": identity})

    monkeypatch.setattr(runner, "_manifest", local_manifest)


def collect(prepared):
    return comparison.collect(Path(prepared["manifest"]), prepared["manifest_hash"],
                              Decimal(prepared["new_cap_usd"]))


def test_four_rows_keep_frozen_input_and_only_charge_new_usage(prepared, source, monkeypatch):
    mutation = MOCK_MUTATIONS["csv-quoted-newline"]
    args = {k: getattr(mutation, k) for k in
            ("path", "old_text", "new_text", "hypothesis", "expected_behavior")}
    args.update(occurrence=1, causal_revision=None)
    repair = [[call("replace_text", args, "mutate")],
              [call("run_check", {"check_id": "existing-unit-tests"}, "verify")],
              [call("finish_task", {}, "finish")]]
    clients = [continuation.ScriptedClient(steps) for steps in
               [repair, stop_steps(), stop_steps(), stop_steps()]]
    install_sdk(monkeypatch, source, clients)
    result = collect(prepared)
    assert result["stop_reason"] is None, result
    assert [row["row"] for row in result["rows"]] == list(comparison.ORDER)
    assert result["rows"][0]["result"]["terminal"] == "EVALUATOR_PASS", result
    assert all(row["result"]["terminal"] == "AGENT_STOPPED" for row in result["rows"][1:])
    assert all(row["first_state_restored"] for row in result["rows"])
    assert all(row["result"]["evaluator"] is None for row in result["rows"][1:])
    assert all(row["historical_spent_nanos"] > 0 for row in result["rows"])
    assert result["new_cost_nanos"] == 6 * (100 * 2500 + 20 * 15000)
    plan = json.loads(Path(prepared["manifest"]).read_bytes())
    for label, client in zip(comparison.ORDER, clients, strict=True):
        request = {k: v for k, v in client.created[0].items() if k != "timeout"}
        assert sha256_json(request) == plan["first_request_hashes"][label[0] + "_request_hash"]
        assert len(client.created) == len(client.counted) == (3 if label == "A1" else 1)
    with pytest.raises(ContractError, match="fresh output"):
        collect(prepared)


@pytest.mark.parametrize("failure", ["count", "transport", "usage"])
def test_uncertainty_cancels_all_remaining_rows(prepared, source, monkeypatch, failure):
    client = continuation.ScriptedClient(stop_steps(), failure=failure)
    install_sdk(monkeypatch, source, [client])
    result = collect(prepared)
    expected = "COUNT_TIMEOUT_OR_UNKNOWN" if failure == "count" else "PROVIDER_TIMEOUT_OR_UNKNOWN"
    assert result["rows"][0]["result"]["terminal"] == expected, result
    assert all(row["status"] == "NOT_RUN" for row in result["rows"][1:]), result
    assert result["rows"][0]["stop_remaining"], result
    assert result["billing_known"] == (failure == "count")
    assert result["new_cost_nanos"] == (0 if failure == "count" else None)
    plan = json.loads(Path(prepared["manifest"]).read_bytes())
    events = DevJournal(Path(plan["result_root"]) / "A1", source.run_id).events()
    fork = next(e["sequence"] for e in events if e["event_type"] == "diagnostic_checkpoint_fork")
    assert not any(e["event_type"] == "action_started" and e["sequence"] > fork for e in events)


def test_preflight_and_authorization_fail_before_provider(prepared, monkeypatch):
    def forbidden(*a, **kw):
        pytest.fail("provider construction forbidden")

    monkeypatch.setattr(model, "create_openai_client", forbidden)
    with pytest.raises(ContractError, match="manifest hash"):
        comparison.collect(Path(prepared["manifest"]), "sha256:wrong", Decimal("1"))
    with pytest.raises(ContractError, match="cap differs"):
        comparison.collect(Path(prepared["manifest"]), prepared["manifest_hash"], Decimal("1"))
    monkeypatch.setattr(comparison, "check_environment",
                        lambda *a: {"status": "PREFLIGHT_FAILED"})
    result = collect(prepared)
    assert result["stop_reason"] == "PREFLIGHT_FAILED"
    assert result["new_cost_nanos"] == 0
    assert all(row["status"] == "NOT_RUN" for row in result["rows"])


def test_ledger_keeps_row_and_group_limits_and_excludes_inherited_spend(tmp_path):
    pricing = pricing_for_model("gpt-5.4-2026-03-05")
    branch = SimpleNamespace(request=SimpleNamespace(max_cost_usd=Decimal("1.20")),
                             pricing=pricing, initial_spent_nanos=232537000)
    group = DevCostLedger(Decimal("3.869852"), pricing)
    journal = DevJournal(tmp_path, "run_dev_ledgerfixture")
    row = comparison.ContinuationLedger(branch, group, journal, "A1")
    assert row.remaining_nanos == 967463000 and group.spent_nanos == 0
    admission = row.admit(100, desired_output_ceiling=100000)
    assert admission.reserved_cost_nanos <= row.remaining_nanos
    cost = row.settle(input_tokens=100, cached_input_tokens=0, output_tokens=20)
    assert group.spent_nanos == cost == row.spent_nanos - branch.initial_spent_nanos
    group.spent_nanos = group.cap_nanos - 250000
    assert row.admit(100) is None  # Row has funds; invocation has no output budget.
    group.spent_nanos = 0
    row.spent_nanos = row.cap_nanos - 250000
    assert row.admit(100) is None  # Unused group funds cannot expand a row.
    row.spent_nanos = branch.initial_spent_nanos
    row.admit(100, desired_output_ceiling=128)
    with pytest.raises(ContractError, match="exceeded"):
        row.settle(input_tokens=100, cached_input_tokens=0, output_tokens=129)
    assert group.spent_nanos > 0  # Unexpected billing remains recorded.


def test_manifest_tamper_is_rejected(prepared):
    path = Path(prepared["manifest"])
    original = path.read_bytes()
    path.write_bytes(original.replace(b'"repeat":4', b'"repeat":5'))
    assert sha256_bytes(path.read_bytes()) != prepared["manifest_hash"]
    with pytest.raises(ContractError, match="manifest hash"):
        collect(prepared)


def test_changed_implementation_and_credential_path_are_rejected(prepared, monkeypatch):
    plan = json.loads(Path(prepared["manifest"]).read_bytes())
    with pytest.raises(ContractError, match="credential path"):
        comparison.controls(Path(plan["packet"]), plan["packet_hash"], Path("wrong.env"),
                            Path(plan["result_root"]))
    monkeypatch.setattr(comparison, "git_commit", lambda: "changed-head")
    with pytest.raises(ContractError, match="implementation changed"):
        collect(prepared)


@pytest.mark.parametrize("failure", [None, "docker", "profile"])
def test_read_only_environment_admission(tmp_path, monkeypatch, failure):
    env_file = tmp_path / "credential.env"
    env_file.write_text("synthetic-never-read", encoding="utf-8")
    identity = {"image_digest": "pinned-probe", "profile_hash": "pinned-profile"}
    envelope = SimpleNamespace(
        credential_file_path_hash=sha256_bytes(str(env_file.resolve()).encode()),
        prepared_source_path=str(tmp_path / "source.json"), prepared_source_hash="source-hash",
        prepared_probe_dependencies_path=None, probe_image_digest=identity["image_digest"],
        probe_profile_hash=identity["profile_hash"],
    )
    package = SimpleNamespace(
        public=SimpleNamespace(repository=SimpleNamespace(url="public", base_commit="base")),
        environment=SimpleNamespace(image_digest="pinned-evaluator"),
    )
    source = SimpleNamespace(public_path=tmp_path / "public.yaml")
    monkeypatch.setattr(comparison, "source_state",
                        lambda *a: ({"runtime_hash": "runtime"}, source, envelope))
    monkeypatch.setattr(runner, "_resolve_task_file", lambda _: (tmp_path, package))
    monkeypatch.setattr(runner, "_live_task_is_admitted", lambda *a: None)
    monkeypatch.setattr(runner, "_live_source_preflight", lambda *a, **kw: None)
    monkeypatch.setattr(runner, "load_source", lambda *a, **kw: None)

    def sandbox(*a, **kw):
        if failure == "docker":
            raise ContractError("Docker unavailable")

    def forbidden(*a, **kw):
        pytest.fail("read-only admission attempted credential/provider access")

    monkeypatch.setattr(runner, "_live_sandbox_preflight", sandbox)
    monkeypatch.setattr(runner, "DockerProbeSandbox", lambda **kw: SimpleNamespace(
        preflight=lambda **kw: identity if failure != "profile" else {}))
    monkeypatch.setattr(runner, "load_exact_openai_api_key", forbidden)
    monkeypatch.setattr(model, "create_openai_client", forbidden)
    result = comparison.check_environment(tmp_path / "packet", "hash", env_file)
    assert result["status"] == ("READY" if failure is None else "PREFLIGHT_FAILED")
    assert result["model_calls"] == result["input_counts"] == result["container_runs"] == 0
    assert result["provider_acceptance"] == result["acceptance"] == result["safety"] == "NOT_RUN"
