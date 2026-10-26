"""Model-only diagnostic comparison with finite fake billing and public fixture tools."""
from __future__ import annotations

import copy
import json
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_dev_probes import FakeProbe
from test_exception_frame_repair import (
    common,
    edit_call,
    no_external,  # noqa: F401 -- retain the autouse external-execution guard.
    read_call,
    stop_call,
)
from test_request_annotation_comparison import PACKET, _probe_call, _thin

from diagnostics import exception_frame_repair as diagnostic
from diagnostics.checkpoint_continuation import ScriptedClient
from patchloop.agent.model import OpenAIResponsesAdapter
from patchloop.deadline import ExecutionDeadline
from patchloop.dev.cost import DevCostLedger, pricing_for_model
from patchloop.errors import ContractError
from patchloop.runtime import repository_root
from patchloop.util import canonical_json, sha256_bytes, sha256_json

MINI = "gpt-5.4-mini-2026-03-17"
FULL = "gpt-5.4-2026-03-05"


class UsageClient(ScriptedClient):
    """Set synthetic usage at the admitted ceiling, or change one billing field."""

    def __init__(self, steps, *, maximum=False, cached=0, response_model=None):
        super().__init__(steps, input_tokens=60_000 if maximum else 100)
        self.maximum, self.cached, self.response_model = maximum, cached, response_model

    def create(self, **request):
        response = super().create(**request)
        response.usage.input_tokens_details.cached_tokens = self.cached
        if self.maximum:
            response.usage.output_tokens = request["max_output_tokens"]
        if self.response_model is not None:
            response.model = self.response_model
        return response


def _request(data, arm):
    return diagnostic.request_payload(data, arm, profile=diagnostic.MODEL_SETTING_PROFILE,
                                      source_packet=PACKET)


def _run_arm(gateway_factory, arm, client, group):
    gateway, journal, _ = gateway_factory()
    gateway.agent_policy = "thin"
    gateway.probe_sandbox = FakeProbe(status="passed")
    gateway.limits.max_accepted_mutations = 1
    gateway.deadline = ExecutionDeadline.from_remaining(60)
    loaded = SimpleNamespace(common=common(gateway.public_task))
    model = MINI if arm == "A" else FULL
    adapter = OpenAIResponsesAdapter(diagnostic.config(model), api_key="", client=client)
    actual = diagnostic.run_model(loaded, arm, gateway, adapter, group,
        first_hash=sha256_json(_request(loaded.common, arm)),
        profile=diagnostic.MODEL_SETTING_PROFILE, source_packet=PACKET)
    return actual, journal


def _events(journal, event_type):
    return [row["payload"] for row in journal.events() if row["event_type"] == event_type]


def _prepare(smoke_package, tmp_path, monkeypatch):
    source = tmp_path / "source"
    source.mkdir()
    calibration = tmp_path / "calibration/calibration.json"
    calibration.parent.mkdir()
    calibration.write_text("{}", encoding="utf-8")
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(canonical_json(PACKET), encoding="utf-8")
    loaded = SimpleNamespace(common=common(smoke_package.public), environment_hash="environment",
        source=SimpleNamespace(root=source, public_path=source / "public.yaml"))
    monkeypatch.setattr(diagnostic, "load_calibration", lambda *_: loaded)
    monkeypatch.setattr(diagnostic, "validate_packet", lambda *_, **__: None)
    prepared = diagnostic.prepare(calibration, "calibration", tmp_path / "plan",
        tmp_path / "result", tmp_path / "unread.env", profile=diagnostic.MODEL_SETTING_PROFILE,
        source_packet=packet_path, source_packet_hash=sha256_bytes(packet_path.read_bytes()))
    manifest = Path(prepared["manifest"])
    plan, actual = diagnostic.validate(manifest, prepared["manifest_hash"])
    assert actual is loaded
    return prepared, manifest, plan


def test_pair_changes_only_snapshot_with_identical_thin_requests_and_full_evidence(smoke_package):
    a, b = [_request(common(smoke_package.public), arm) for arm in ("A", "B")]
    frozen = copy.deepcopy((a, b))
    assert diagnostic.verify_model_pair(a, b) is None
    assert (a, b) == frozen
    assert (a["model"], b["model"]) == (MINI, FULL)
    assert {**a, "model": FULL} == b
    assert a["reasoning"] == b["reasoning"] == {"effort": "xhigh"}
    assert a["max_output_tokens"] == b["max_output_tokens"] == 40_000
    focus = json.loads(a["input"][1]["content"])
    assert focus["source_packet"] == PACKET
    assert focus["current_failure"]["exception_diagnostics"]["calls"]
    assert len(focus["source_packet"]["sources"][0]["content"].splitlines()) == 148
    for request in (a, b):
        for tool in request["tools"]:
            if tool["name"] in {"read_file", "search_files", "run_probe"}:
                properties = tool["parameters"]["properties"]
                assert "turn_decision" not in properties
                assert properties["memory_update"]["type"] == ["object", "null"]


def test_pair_rejects_changed_reasoning_evidence_tools_or_wrong_model(smoke_package):
    a, b = [_request(common(smoke_package.public), arm) for arm in ("A", "B")]
    for field, value in (("model", MINI), ("reasoning", {"effort": "high"}),
                         ("max_output_tokens", 25_000), ("parallel_tool_calls", False)):
        with pytest.raises(ContractError):
            diagnostic.verify_model_pair(a, {**b, field: value})
    changed = copy.deepcopy(b)
    changed["input"][1]["content"] += " altered evidence"
    with pytest.raises(ContractError):
        diagnostic.verify_model_pair(a, changed)
    changed = copy.deepcopy(b)
    changed["tools"][0]["description"] += " altered instruction"
    with pytest.raises(ContractError):
        diagnostic.verify_model_pair(a, changed)
    with pytest.raises(ContractError):
        diagnostic.verify_model_pair({**a, "model": FULL}, b)


def test_existing_profiles_keep_their_model_policy_caps_and_request_comparisons(smoke_package):
    data = common(smoke_package.public)
    old = [diagnostic.DEFAULT_PROFILE, diagnostic.SOURCE_READY_PROFILE,
           diagnostic.OPPORTUNITY_PROFILE, diagnostic.REQUEST_STRUCTURE_PROFILE]
    assert [profile.invocation_cap for profile in old] == [
        Decimal("1.20"), Decimal("1.20"), Decimal("1.20"), Decimal("2.40")]
    for profile in old:
        requests = {arm: diagnostic.request_payload(data, arm, profile=profile,
            source_packet=None if profile == diagnostic.DEFAULT_PROFILE else PACKET)
            for arm in profile.order}
        assert all(request["model"] == MINI for request in requests.values())
        assert not profile.compare_models
        if profile == diagnostic.DEFAULT_PROFILE:
            diagnostic.verify_pair(requests["A"], requests["B"])
        if profile.compare_request_annotations:
            diagnostic.verify_request_pair(requests["A"], requests["B"])
    assert diagnostic.config() == diagnostic.config(MINI)


def test_shared_cap_funds_both_complete_maximum_usage_horizons_without_closing_tools(
        gateway_factory):
    # Start at the other model's price: each arm must price its own future and usage.
    group = DevCostLedger(Decimal("8.60"), pricing_for_model(FULL))
    costs = []
    for arm, model, expected_cost in (("A", MINI, 1_957_500_000),
                                      ("B", FULL, 6_525_000_000)):
        steps = [[_thin(read_call(str(index)))] for index in range(6)]
        steps += [[], [_thin(_probe_call())], [edit_call()]]
        client = UsageClient(steps, maximum=True)
        prior_spend = group.spent_nanos
        actual, journal = _run_arm(gateway_factory, arm, client, group)
        assert actual["terminal"] == "CANDIDATE_PRODUCED"
        assert actual["billing_known"] and not actual["stop_remaining"]
        assert (actual["normal_calls"], actual["correction_calls"], actual["tool_actions"],
                actual["diagnostic_probes"], actual["new_mutations"]) == (8, 1, 8, 1, 1)
        assert actual["model"] == model
        assert actual["new_cost_nanos"] == group.spent_nanos - prior_spend == expected_cost
        assert group.pricing == pricing_for_model(model)
        assert not _events(journal, "opportunity_cost_narrowed")
        assert len(client.counted) == len(client.created) == 9
        first_remaining = json.loads(client.created[0]["input"][-1]["content"])["remaining"]
        assert first_remaining["cost_nanos"] == 6_600_000_000
        assert group.cap_nanos - prior_spend >= first_remaining["cost_nanos"]
        assert [row["max_output_tokens"] for row in client.created] == [
            *([40_000] * 7), 25_000, 40_000]
        for counted, dispatched in zip(client.counted, client.created, strict=True):
            assert {key: dispatched[key] for key in counted if key != "timeout"} == {
                key: value for key, value in counted.items() if key != "timeout"}
            assert dispatched["model"] == model
        actions = [event["result"] for event in _events(journal, "action_finished")]
        assert [row["tool"] for row in actions[-2:]] == ["run_probe", "replace_text"]
        assert all(row["status"] == "succeeded" and not row["error_code"] for row in actions)
        costs.append(actual["new_cost_nanos"])
    assert group.spent_nanos == sum(costs) == 8_482_500_000
    assert group.remaining_nanos == 117_500_000


def test_active_model_cached_prices_add_to_existing_currency_without_repricing_it(gateway_factory):
    group = DevCostLedger(Decimal("8.60"), pricing_for_model(MINI))
    group.spent_nanos = 123_456_789
    client = UsageClient([[stop_call()]], cached=80)
    actual, _ = _run_arm(gateway_factory, "B", client, group)
    # 20 uncached input * $2.5/M + 80 cached * $0.25/M + 20 output * $15/M.
    assert actual["terminal"] == "AGENT_STOPPED" and actual["billing_known"]
    assert actual["new_cost_nanos"] == 370_000
    assert group.spent_nanos == 123_826_789


def test_small_global_remainder_cannot_admit_full_model_at_mini_prices(gateway_factory):
    group = DevCostLedger(Decimal("8.60"), pricing_for_model(MINI))
    group.spent_nanos = 8_400_000_000
    client = UsageClient([[stop_call()]])
    actual, journal = _run_arm(gateway_factory, "B", client, group)
    assert actual["terminal"] == "COST_CAP_REACHED"
    assert not client.created and len(client.counted) == 3
    assert actual["new_cost_nanos"] == 0 and group.spent_nanos == 8_400_000_000
    assert not _events(journal, "action_started")
    assert len(_events(journal, "opportunity_cost_narrowed")) == 2


def test_response_model_mismatch_stops_before_tools_or_uncertain_settlement(gateway_factory):
    group = DevCostLedger(Decimal("8.60"), pricing_for_model(MINI))
    group.spent_nanos = 110_000_000
    client = UsageClient([[_thin(read_call())]], response_model=MINI)
    actual, journal = _run_arm(gateway_factory, "B", client, group)
    assert actual["terminal"] == "BILLING_UNCERTAIN" and actual["stop_remaining"]
    assert not actual["billing_known"] and actual["new_cost_nanos"] == 0
    assert group.spent_nanos == 110_000_000
    assert len(client.created) == 1 and client.created[0]["model"] == FULL
    assert _events(journal, "provider_usage_unknown")
    assert not _events(journal, "action_started")


def test_manifest_binds_each_model_price_scope_and_exact_request(
        smoke_package, tmp_path, monkeypatch):
    prepared, manifest, plan = _prepare(smoke_package, tmp_path, monkeypatch)
    assert plan["profile"] == "model-setting-pair-v1"
    assert plan["models"] == {"A": MINI, "B": FULL}
    assert "model" not in plan and "pricing" not in plan
    assert plan["model_pricing"] == {
        MINI: {"input_per_million_usd": "0.75", "cached_input_per_million_usd": "0.075",
               "output_per_million_usd": "4.5"},
        FULL: {"input_per_million_usd": "2.5", "cached_input_per_million_usd": "0.25",
               "output_per_million_usd": "15"}}
    assert plan["request_annotation_policies"] == {"A": "thin", "B": "thin"}
    assert (plan["row_cap_usd"], plan["new_cap_usd"]) == ("6.60", "8.60")
    assert (plan["normal_calls"], plan["correction_calls"], plan["input_limit"],
            plan["ordinary_output"], plan["correction_output"]) == (8, 1, 60_000, 40_000, 25_000)
    assert prepared["provider_calls"] == prepared["credential_reads"] == 0
    altered_prices = copy.deepcopy(plan["model_pricing"])
    altered_prices[FULL]["output_per_million_usd"] = "4.5"
    for field, value in (("models", {"A": MINI, "B": MINI}),
                         ("model_pricing", altered_prices), ("new_cap_usd", "13.20"),
                         ("row_cap_usd", "6.50"), ("input_limit", 60_001),
                         ("request_annotation_policies", {"A": "current", "B": "thin"})):
        manifest.write_text(canonical_json({**plan, field: value}), encoding="utf-8")
        with pytest.raises(ContractError):
            diagnostic.validate(manifest, sha256_bytes(manifest.read_bytes()))
    manifest.write_text(canonical_json(plan), encoding="utf-8")
    first = manifest.parent / "B-first.json"
    payload = json.loads(first.read_bytes())
    first.write_text(canonical_json({**payload, "model": MINI}), encoding="utf-8")
    with pytest.raises(ContractError, match="prepared input"):
        diagnostic.validate(manifest, sha256_bytes(manifest.read_bytes()))


def test_wrong_cap_or_manifest_hash_never_reaches_external_setup(
        smoke_package, tmp_path, monkeypatch):
    prepared, manifest, _ = _prepare(smoke_package, tmp_path, monkeypatch)
    monkeypatch.setattr(diagnostic, "_gateway", lambda *_, **__:
                        pytest.fail("invalid approval reached setup"))
    for cap in ("2.40", "6.60", "8.50", "8.59", "13.20"):
        with pytest.raises(ContractError, match="cap approval"):
            diagnostic.collect(manifest, prepared["manifest_hash"], Decimal(cap))
    with pytest.raises(ContractError, match="manifest hash"):
        diagnostic.collect(manifest, "wrong", Decimal("8.60"))
    assert not (tmp_path / "result").exists()


def test_collect_uses_each_approved_model_and_one_shared_currency_ledger(tmp_path, monkeypatch):
    loaded = SimpleNamespace(source_packet=PACKET, source=SimpleNamespace(
        root=tmp_path / "historical",
        public_path=repository_root() / "tasks/dev-train/current-dev20/13/public.yaml"))
    plan = {"result_root": str(tmp_path / "result"), "calibration": str(tmp_path / "cal/a.json"),
        "calibration_hash": "calibration", "profile": diagnostic.MODEL_SETTING_PROFILE.name,
        "order": ["A", "B"], "credential_file": str(tmp_path / "unread.env"),
        "first_request_hashes": {"A": "a", "B": "b"}, "interpretation": "synthetic"}
    monkeypatch.setattr(diagnostic, "validate", lambda *_: (plan, loaded))
    monkeypatch.setattr(diagnostic, "_gateway", lambda _, root, **__:
                        SimpleNamespace(workspace=root, agent_policy="thin"))
    monkeypatch.setattr(diagnostic, "validate_packet", lambda *_, **__: None)
    monkeypatch.setattr(diagnostic, "observe_sources", lambda *_: None)
    monkeypatch.setattr(diagnostic, "load_exact_openai_api_key", lambda _: "synthetic-not-a-key")
    monkeypatch.setattr(diagnostic, "OpenAIResponsesAdapter", lambda config, **_:
                        SimpleNamespace(config=config, client=SimpleNamespace(close=lambda: None)))
    groups, selected = [], []

    def model(_, arm, gateway, adapter, group, **kwargs):
        assert gateway.agent_policy == "thin" and group.cap_nanos == 8_600_000_000
        assert kwargs["profile"] == diagnostic.MODEL_SETTING_PROFILE
        selected.append((arm, adapter.config.model_id))
        assert group.spent_nanos == (0 if arm == "A" else 123)
        group.spent_nanos += 123
        groups.append(group)
        return {"terminal": "AGENT_STOPPED", "stop_remaining": False}

    monkeypatch.setattr(diagnostic, "run_model", model)
    result = diagnostic.collect(tmp_path / "plan/manifest.json", "synthetic-approved",
                                Decimal("8.60"))
    assert selected == [("A", MINI), ("B", FULL)] and groups[0] is groups[1]
    assert result["new_cost_nanos"] == 246
