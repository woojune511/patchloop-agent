from __future__ import annotations

import copy
import json
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace as NS

import pytest

from diagnostics import closure_policy_sampler as sampler
from diagnostics import decision_sampler as shared
from patchloop.artifacts import ArtifactStore
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import DevToolGateway, dev_tool_schemas
from patchloop.errors import ContractError
from patchloop.runtime import repository_root, runtime_content_hash
from patchloop.util import canonical_json, sha256_bytes, sha256_json
from tests.test_decision_sampler import FakeClient


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("network, credential or tool execution reached")
    monkeypatch.setattr("socket.socket.connect", forbidden)
    monkeypatch.setattr(shared, "load_exact_openai_api_key", forbidden)
    monkeypatch.setattr(shared, "create_openai_client", forbidden)
    monkeypatch.setattr(DevToolGateway, "execute", forbidden)
    source = tmp_path / "source"
    group = DevJournal(source, "run_dev_timeextension")
    branch = DevJournal(source / "A1", "run_dev_33068b6e257f423a")
    task = tmp_path / "public.yaml"
    task.write_text("synthetic public fixture", encoding="utf-8")
    envelope = NS(task_path=str(task), split="dev-train", task_id="original-toqito-1538",
                  task_version=1, task_content_hash=sha256_json("task"), run_id=branch.run_id,
                  model=sampler.MODEL, reasoning_effort="xhigh",
                  runtime_hash=runtime_content_hash(),
                  public_spec_hash=sha256_json({"fixture": "public"}))
    monkeypatch.setattr(sampler, "load_public_task", lambda _: NS(
        model_dump=lambda **kwargs: {"fixture": "public"}))
    monkeypatch.setattr(DevJournal, "load_envelope", lambda self: envelope)
    monkeypatch.setattr(sampler.segmented_input_audit, "verify_turn", lambda *a, **k: None)
    turn = branch.append("turn_started", {"turn_id": "turn_fixture", "max_parallel_reads": 4,
                                         "targeted_read_paths": ["public.py"]})
    a = {**shared.SETTINGS, "model": sampler.MODEL, "reasoning": {"effort": "xhigh"},
         "input": [{"role": "system", "content": "Before\n" + sampler.REMOVED + "After"}],
         "tools": dev_tool_schemas(finish_enabled=False, check_ids=[],
                                    allowed_tools=["read_file"], read_paths=["public.py"])}
    b = copy.deepcopy(a)
    b["input"][0]["content"] = b["input"][0]["content"].replace(sampler.REMOVED, "")
    group.append("actual_dispatch_started", {
        "artifact": ArtifactStore(source / "artifacts").put_json(a).model_dump(mode="json")})
    pair_dir = tmp_path / "pair"
    store = ArtifactStore(pair_dir / "artifacts")
    pair = {"schema": "closure-policy-next-decision-design-v1", "paid_execution_authorized": False,
            "source_root": str(source), "source_group_hash": sha256_bytes(group.path.read_bytes()),
            "source_branch_hash": sha256_bytes(branch.path.read_bytes()),
            "source_turn_sequence": turn["sequence"],
            "requests": {k: store.put_json(v).model_dump(mode="json")
                         for k, v in [("A", a), ("B", b)]},
            "request_hashes": {"A": sha256_json(a), "B": sha256_json(b)}}
    path = pair_dir / "packet.json"
    path.write_text(canonical_json(pair), encoding="utf-8")
    receipt = sampler.prepare(path, sha256_bytes(path.read_bytes()), tmp_path / "plan")
    plan = sampler.load_plan(tmp_path / "plan/packet.json", receipt["packet_hash"])
    grant = shared.Approval(plan.packet_hash, sampler.sampler_hash(), tmp_path / "results",
                            repository_root() / ".env", Decimal("4"),
                            sha256_json(plan.packet["pricing"]),
                            datetime.now(UTC).date().isoformat())
    return NS(plan=plan, grant=grant, pair=pair, pair_path=path, source=source)


def client(**kwargs):
    def edit(response):
        response.model = sampler.MODEL
    return FakeClient(edit_response=edit, **kwargs)


def test_independent_requests_and_no_tools(prepared):
    fake = client()
    result = sampler.collect(prepared.plan, prepared.grant, adapter_factory=fake.factory)
    assert result["terminal"] == "SAMPLES_COLLECTED"
    assert result["provider_calls"] == result["sample_count"] == 4
    assert result["tool_executions"] == 0 and result["task_acceptance"] == "NOT_RUN"
    assert result["total_cost_known"]
    for actual, cell in zip(fake.created, prepared.plan.cells, strict=True):
        assert {k: v for k, v in actual.items() if k != "timeout"} == json.loads(cell.request_json)
    with pytest.raises(ContractError, match="already exists"):
        sampler.collect(prepared.plan, prepared.grant, adapter_factory=fake.factory)


@pytest.mark.parametrize(("kwargs", "terminal", "calls"), [
    ({"count_error": True}, "COUNT_TIMEOUT_OR_UNKNOWN", 0),
    ({"create_error": True}, "PROVIDER_TIMEOUT_OR_UNKNOWN", 1),
    ({"count_value": 60_001}, "INPUT_LIMIT_EXCEEDED", 0),
])
def test_uncertainty_and_input_cap_stop_all_samples(prepared, kwargs, terminal, calls):
    fake = client(**kwargs)
    result = sampler.collect(prepared.plan, prepared.grant, adapter_factory=fake.factory)
    assert result["terminal"] == terminal
    assert len(fake.counted) == 1 and len(fake.created) == calls


def test_unknown_billing_stops_group(prepared):
    fake = FakeClient(edit_response=lambda response: setattr(response.usage, "input_tokens", 101))
    result = sampler.collect(prepared.plan, prepared.grant, adapter_factory=fake.factory)
    assert result["terminal"] == "PROVIDER_TIMEOUT_OR_UNKNOWN"
    assert not result["total_cost_known"] and len(fake.created) == 1


@pytest.mark.parametrize("field,value", [
    ("max_cost_usd", Decimal("5")), ("packet_hash", "sha256:wrong"),
    ("sampler_hash", "sha256:wrong"), ("pricing_hash", "sha256:wrong"),
    ("pricing_verified_on", "2000-01-01"),
])
def test_wrong_grant_never_claims_root(prepared, field, value):
    with pytest.raises(ContractError):
        sampler.collect(prepared.plan, replace(prepared.grant, **{field: value}))
    assert not prepared.grant.result_root.exists()


def test_rehashed_treatment_with_unrelated_change_rejected(prepared):
    pair = prepared.pair
    body = json.loads(shared.read_source_artifact(prepared.pair_path.parent, pair["requests"]["B"]))
    body["max_output_tokens"] = 24_000
    pair["requests"]["B"] = ArtifactStore(prepared.pair_path.parent / "artifacts").put_json(
        body).model_dump(mode="json")
    pair["request_hashes"]["B"] = sha256_json(body)
    prepared.pair_path.write_text(canonical_json(pair), encoding="utf-8")
    with pytest.raises(ContractError, match="other fields"):
        sampler.load_pair(prepared.pair_path, sha256_bytes(prepared.pair_path.read_bytes()))


def test_source_change_rejected_before_dispatch(prepared):
    DevJournal(prepared.source, "run_dev_timeextension").append("unexpected", {})
    with pytest.raises(ContractError, match="source journal changed"):
        sampler.collect(prepared.plan, prepared.grant)
    assert not prepared.grant.result_root.exists()


def test_full_reservation_fits_each_response():
    profile = shared.cell_profile(sampler.protocol(), "A")
    assert shared.full_reservation(60_000, profile.pricing()) <= 1_000_000_000


def test_post_invalid_probe_lane_binds_last_dispatch_and_boundary(prepared):
    pair = copy.deepcopy(prepared.pair)
    original = json.loads(shared.read_source_artifact(prepared.pair_path.parent,
                                                     pair["requests"]["A"]))
    original["input"].append({"role": "user", "content": canonical_json({
        "state": {"completion_guidance": {"submission_ready": True},
                  "remaining_budget": {"accepted_mutations": 0}}, "error": "SyntaxError"})})
    original["tools"] = dev_tool_schemas(finish_enabled=True, check_ids=[],
                                         allowed_tools=["run_probe", "finish_task"])
    group = DevJournal(prepared.source, "run_dev_probefollowup")
    branch = DevJournal(prepared.source / "B2", "run_dev_33068b6e257f423a")
    turn = branch.append("turn_started", {"turn_id": "last", "max_parallel_reads": 4,
                                         "targeted_read_paths": []})
    store = ArtifactStore(prepared.source / "artifacts")
    for index in range(5):
        group.append("actual_dispatch_started", {"artifact": store.put_json(
            original if index == 4 else {"not": "selected"}).model_dump(mode="json")})
    treatment = copy.deepcopy(original)
    treatment["input"][0]["content"] = treatment["input"][0]["content"].replace(sampler.REMOVED, "")
    pair.update(source_lane="post-invalid-probe", source_turn_sequence=turn["sequence"],
                source_group_hash=sha256_bytes(group.path.read_bytes()),
                source_branch_hash=sha256_bytes(branch.path.read_bytes()),
                requests={a: ArtifactStore(prepared.pair_path.parent / "artifacts").put_json(r)
                          .model_dump(mode="json") for a, r in [("A", original), ("B", treatment)]},
                request_hashes={"A": sha256_json(original), "B": sha256_json(treatment)})
    prepared.pair_path.write_text(canonical_json(pair), encoding="utf-8")
    loaded = sampler.load_pair(prepared.pair_path, sha256_bytes(prepared.pair_path.read_bytes()))
    assert loaded[3]["A"] == original
    group.append("actual_dispatch_started", {"artifact": store.put_json(original)
                                              .model_dump(mode="json")})
    pair["source_group_hash"] = sha256_bytes(group.path.read_bytes())
    prepared.pair_path.write_text(canonical_json(pair), encoding="utf-8")
    with pytest.raises(ContractError, match="ambiguous"):
        sampler.load_pair(prepared.pair_path, sha256_bytes(prepared.pair_path.read_bytes()))
