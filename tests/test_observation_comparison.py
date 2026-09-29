"""Exercise the paid collector with inert SDK clients, never real credentials."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest
import test_mutation_advice_checkpoint as fixture_source
from test_checkpoint_comparison import install_sdk
from test_checkpoint_continuation import call, stop_steps
from test_dev_probes import FakeProbe

from diagnostics import observation_comparison as comparison
from diagnostics.checkpoint_continuation import ScriptedClient
from patchloop.agent import model
from patchloop.contracts import TaskEnvironment
from patchloop.dev import runner
from patchloop.dev.model import MOCK_MUTATIONS
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError
from patchloop.util import canonical_json, sha256_bytes


def resolver(original):
    def resolve(path):
        task, package = original(path)
        return task, package.model_copy(
            update={
                "environment": TaskEnvironment(
                    evaluator_image="test/image@sha256:" + "a" * 64,
                    image_digest="sha256:" + "a" * 64,
                )
            }
        )

    return resolve


@pytest.fixture(scope="module")
def source(tmp_path_factory):
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(fixture_source, "FakeProbe", lambda **_: FakeProbe(status="failed"))
        return fixture_source.source.__wrapped__(tmp_path_factory)


@pytest.fixture(scope="module")
def prepared(source, tmp_path_factory):
    root = tmp_path_factory.mktemp("observation-plan")
    events = DevJournal(source.root, source.run_id).events()
    cut = [e for e in events if e["event_type"] == "model_input_prepared"][-1]["sequence"]
    target = next(
        e["payload"]["result"]["action_id"]
        for e in events
        if e["event_type"] == "action_finished" and e["payload"]["result"]["tool"] == "run_probe"
    )
    cases = {
        key: {"source": source.record(), "cut_sequence": cut, "target_action_id": target}
        for key in ("N1", "P1", "P2")
    }
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(comparison, "clean_implementation", lambda: None)
        patch.setattr(comparison, "check_environment", lambda *a: {"status": "READY"})
        patch.setattr(runner, "_resolve_task_file", resolver(runner._resolve_task_file))
        result = comparison.prepare(
            cases, source.root.parent / "absent.env", root / "result", Decimal("1"), root / "plan"
        )
    assert result["actual_provider_calls"] == 0 and not result["paid_execution_authorized"]
    return json.loads(Path(result["manifest"]).read_bytes())


@pytest.fixture
def manifest(prepared, tmp_path, monkeypatch):
    plan = {**prepared, "result_root": str(tmp_path / "result")}
    path = tmp_path / "plan" / "manifest.json"
    path.parent.mkdir()
    path.write_text(canonical_json(plan), encoding="utf-8")
    monkeypatch.setattr(comparison, "clean_implementation", lambda: None)
    monkeypatch.setattr(comparison, "check_environment", lambda *a: {"status": "READY"})
    monkeypatch.setattr(runner, "_resolve_task_file", resolver(runner._resolve_task_file))
    monkeypatch.setattr("socket.socket.connect", lambda *_: pytest.fail("network forbidden"))
    return path


def collect(path):
    return comparison.collect(path, sha256_bytes(path.read_bytes()), Decimal("6"))


def test_six_rows_use_real_collector_and_isolated_fixture_evaluation(manifest, source, monkeypatch):
    monkeypatch.setattr(comparison, "git_commit", lambda: "d" * 40)
    mutation = MOCK_MUTATIONS["csv-quoted-newline"]
    args = {
        k: getattr(mutation, k)
        for k in ("path", "old_text", "new_text", "hypothesis", "expected_behavior")
    }
    args.update(occurrence=1, causal_revision=None)
    repair = [
        [call("replace_text", args, "mutate")],
        [call("run_check", {"check_id": "existing-unit-tests"}, "verify")],
        [call("finish_task", {}, "finish")],
    ]
    clients = [ScriptedClient(steps) for steps in [repair, *[stop_steps() for _ in range(5)]]]
    install_sdk(monkeypatch, source, clients)
    result = collect(manifest)
    assert result["stop_reason"] is None, result
    assert [r["row"] for r in result["rows"]] == list(comparison.ORDER)
    assert result["rows"][0]["result"]["terminal"] == "EVALUATOR_PASS", result
    root = Path(json.loads(manifest.read_bytes())["result_root"])
    submitted = json.loads(
        (root / "N1A" / "artifacts" / "runs" / source.run_id / "manifest.json").read_bytes()
    )
    assert submitted["harness_git_commit"] == "d" * 40
    assert all(r["result"]["terminal"] == "AGENT_STOPPED" for r in result["rows"][1:])
    assert result["new_cost_nanos"] == 8 * (100 * 2500 + 20 * 15000)
    assert all(len(c.counted) == len(c.created) for c in clients)
    for label, client in zip(comparison.ORDER, clients, strict=True):
        for request in client.created:
            verification = json.loads(request["input"][-1]["content"])["state"]["working_notes"][
                "verification"
            ]
            assert ("observations" in verification) == label.endswith("B")
    with pytest.raises((ContractError, FileExistsError)):
        collect(manifest)


@pytest.mark.parametrize("failure", ["count", "transport", "usage"])
def test_uncertainty_stops_whole_group(manifest, source, monkeypatch, failure):
    client = ScriptedClient(stop_steps(), failure=failure)
    install_sdk(monkeypatch, source, [client])
    result = collect(manifest)
    expected = "COUNT_TIMEOUT_OR_UNKNOWN" if failure == "count" else "PROVIDER_TIMEOUT_OR_UNKNOWN"
    assert result["rows"][0]["result"]["terminal"] == expected, result
    assert all(r["status"] == "NOT_RUN" for r in result["rows"][1:])
    assert result["billing_known"] == (failure == "count")
    assert result["new_cost_nanos"] == (0 if failure == "count" else None)


def test_authorization_and_preflight_stop_before_sdk(manifest, monkeypatch):
    monkeypatch.setattr(model, "create_openai_client", lambda *a, **kw: pytest.fail("SDK reached"))
    with pytest.raises(ContractError, match="manifest hash"):
        comparison.collect(manifest, "wrong", Decimal("6"))
    with pytest.raises(ContractError, match="cap differs"):
        comparison.collect(manifest, sha256_bytes(manifest.read_bytes()), Decimal("7"))
    monkeypatch.setattr(comparison, "check_environment", lambda *a: {"status": "PREFLIGHT_FAILED"})
    result = collect(manifest)
    assert result["stop_reason"] == "PREFLIGHT_FAILED" and result["new_cost_nanos"] == 0
    assert all(r["status"] == "NOT_RUN" for r in result["rows"])


def test_first_input_tamper_prevents_dispatch(manifest, source, monkeypatch):
    plan = json.loads(manifest.read_bytes())
    plan["first_request_hashes"]["N1A"] = "wrong"
    manifest.write_text(canonical_json(plan), encoding="utf-8")
    client = ScriptedClient(stop_steps())
    install_sdk(monkeypatch, source, [client])
    result = collect(manifest)
    assert not client.counted and not client.created
    assert result["stop_reason"] is not None
    assert all(r["status"] == "NOT_RUN" for r in result["rows"][1:])


def test_changed_rubric_or_implementation_rejected(manifest, monkeypatch):
    monkeypatch.setattr(comparison.exposure, "implementation_hash", lambda: "changed")
    with pytest.raises(ContractError, match="controls changed"):
        collect(manifest)


def test_drift_between_count_and_dispatch_blocks_sdk_create(manifest, source, monkeypatch):
    client = ScriptedClient(stop_steps())
    install_sdk(monkeypatch, source, [client])
    original = comparison.OpenAIResponsesAdapter.count_input_tokens_v2

    def changed(self, payload, **kwargs):
        count = original(self, payload, **kwargs)
        payload["input"][-1]["content"] += "changed-after-count"
        return count

    monkeypatch.setattr(comparison.OpenAIResponsesAdapter, "count_input_tokens_v2", changed)
    result = collect(manifest)
    assert len(client.counted) == 1 and not client.created
    assert result["stop_reason"] is not None
    assert all(r["status"] == "NOT_RUN" for r in result["rows"][1:])
