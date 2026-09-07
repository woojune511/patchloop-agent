from __future__ import annotations

import copy
import json
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest
from test_decision_sampler import (
    FakeClient,
    ProcessKilled,
    artifact_json,
    events,
)
from test_decision_sampler import (
    prepared as prepared,
)

from diagnostics import decision_sampler as shared
from diagnostics import fresh_state_design as design
from diagnostics import fresh_state_sampler as sampler
from patchloop.errors import ContractError, RecoveryError
from patchloop.util import canonical_json, sha256_bytes, sha256_json, sha256_text


@pytest.fixture
def fresh(prepared, monkeypatch, tmp_path):
    source, approval = prepared
    monkeypatch.setattr(design, "SOURCE_PACKET_HASH", source.packet_hash)
    root = tmp_path / "fresh-design"
    root.mkdir()
    (root / "protocol.md").write_text("FRESH_REVIEWER_ONLY_SENTINEL", encoding="utf-8")
    (root / "rubric.json").write_text('{"sentinel":"FRESH_RUBRIC_ONLY"}', encoding="utf-8")
    design.prepare(source, root)
    packet = root / "packet.json"
    plan = sampler.load_plan(
        packet, source.packet_path, source.source_root, sha256_bytes(packet.read_bytes())
    )
    return plan, replace(
        approval, packet_hash=plan.packet_hash, sampler_hash=sampler.sampler_hash()
    )


class CountedClient(FakeClient):
    def __init__(self, counts=(153464, 62000, 62000, 153464), **kwargs):
        super().__init__(**kwargs)
        self.counts = iter(counts)
        self.sequence = []

    def count(self, **request):
        self.sequence.append("count")
        self.count_value = next(self.counts)
        return super().count(**request)

    def create(self, **request):
        self.sequence.append("create")
        return super().create(**request)


def snapshots(*roots):
    return {p: p.read_bytes() for root in roots for p in root.rglob("*") if p.is_file()}


def test_four_independent_ordered_requests_are_counted_just_before_dispatch(fresh):
    plan, approval = fresh
    before = snapshots(plan.source_root, plan.source_packet_path.parent, plan.packet_path.parent)
    fake = CountedClient()
    result = sampler.collect(plan, approval, adapter_factory=fake.factory)
    assert result["terminal"] == "SAMPLES_COLLECTED"
    assert result["sample_count"] == result["input_count_calls"] == result["provider_calls"] == 4
    assert fake.sequence == ["count", "create"] * 4
    assert result["tool_executions"] == 0 and result["provider_free"] is True
    assert result["task_acceptance"] == result["safety_state"] == "NOT_RUN"
    rows = events(approval)
    recorded = [e["payload"] for e in rows if e["event_type"] == "sample_recorded"]
    assert [(r["arm"], r["sample_number"]) for r in recorded] == list(
        sampler.PROTOCOL.sampling_order
    )
    assert len({r["sample_id"] for r in recorded}) == 4
    assert all(c.historical_count is None for c in plan.cells if c.arm == "B")
    for cell, counted, request in zip(plan.cells, fake.counted, fake.created, strict=True):
        wire = design.wire_json({k: v for k, v in request.items() if k != "timeout"})
        assert wire == cell.request_json
        assert request["reasoning"] == {"effort": "medium"}
        assert request["store"] is False and request["max_output_tokens"] == 25000
        assert design.wire_json(counted["input"]) == design.wire_json(request["input"])
        assert design.wire_json(counted["tools"]) == design.wire_json(request["tools"])
        assert "new_cipher_" not in wire and "new_call_" not in wire
        assert "FRESH_REVIEWER_ONLY_SENTINEL" not in wire and "FRESH_RUBRIC_ONLY" not in wire
        assert any(i.get("type") == "reasoning" for i in request["input"]) == (cell.arm == "A")
    for record in recorded:
        public = artifact_json(record["public_artifact"])
        assert public["case_id"] == "C3"
        assert (
            not {"arm", "sample_number", "reasoning_effort", "cost_nanos", "latency"}
            & public.keys()
        )
        continuation = artifact_json(record["continuation_ref"]["artifact"])
        assert [i["type"] for i in continuation["output_order"]] == [
            "reasoning",
            "function_call_ref",
        ]
    envelope = json.loads((approval.result_root / "envelope.json").read_bytes())
    assert envelope["kind"] == "fresh-state-sampler-v1"
    assert envelope["maximum_generation_calls"] == envelope["maximum_input_count_calls"] == 4
    assert envelope["collection_policy"]["input_token_limit"] == 272000
    assert envelope["preparer_hash"] == plan.packet["preparer_hash"]
    assert envelope["source_packet_hash"] == design.SOURCE_PACKET_HASH
    assert all(p.read_bytes() == raw for p, raw in before.items())
    for path, raw in snapshots(approval.result_root).items():
        assert b"PLAINTEXT_REASONING_SENTINEL" not in raw
        assert b"SECRET_EXCEPTION_SENTINEL" not in raw
        if path.suffix == ".jsonl":
            assert b"new_cipher_" not in raw
    assert shared.inspect_result(approval.result_root) == result


@pytest.mark.parametrize(
    "field,value",
    [
        ("sampler_hash", "wrong"),
        ("packet_hash", "wrong"),
        ("max_cost_usd", Decimal("1.21")),
        ("pricing_hash", "wrong"),
        ("pricing_verified_on", "2000-01-01"),
    ],
)
def test_exact_fresh_approval_before_any_client(fresh, field, value):
    plan, approval = fresh
    fake = CountedClient()
    with pytest.raises(ContractError):
        sampler.collect(plan, replace(approval, **{field: value}), adapter_factory=fake.factory)
    assert not approval.result_root.exists() and fake.sequence == []


@pytest.mark.parametrize(
    "target",
    [
        "source_packet",
        "source_artifact",
        "fresh_artifact",
        "fresh_protocol",
        "source_protocol",
        "runtime",
        "preparer",
        "schedule",
        "effort",
    ],
)
def test_disk_contract_tampering_rejected_before_root_or_calls(fresh, target):
    plan, approval = fresh
    if target == "source_packet":
        path = plan.source_packet_path
    elif target == "source_artifact":
        source = json.loads(plan.source_packet_path.read_bytes())
        path = Path(source["cases"][2]["input_artifact"]["path"])
    elif target == "fresh_artifact":
        path = Path(plan.packet["request_artifacts"]["B"]["path"])
    elif target.endswith("protocol"):
        root = (
            plan.packet_path.parent
            if target == "fresh_protocol"
            else plan.source_packet_path.parent
        )
        path = root / "protocol.md"
    else:
        packet = copy.deepcopy(plan.packet)
        key = {
            "runtime": "runtime_hash",
            "preparer": "preparer_hash",
            "schedule": "sampling_order_proposal",
            "effort": "reasoning_effort",
        }[target]
        packet[key] = "tampered"
        plan.packet_path.write_text(canonical_json(packet), encoding="utf-8")
        # A newly supplied packet hash cannot authorize a changed frozen contract.
        digest = sha256_bytes(plan.packet_path.read_bytes())
        plan, approval = replace(plan, packet_hash=digest), replace(approval, packet_hash=digest)
        path = None
    if path:
        path.write_bytes(path.read_bytes() + b" ")
    fake = CountedClient()
    with pytest.raises((ContractError, RecoveryError)):
        sampler.collect(plan, approval, adapter_factory=fake.factory)
    assert not approval.result_root.exists() and fake.sequence == []


def test_six_cell_collector_and_fresh_collector_do_not_accept_each_others_packet(fresh, prepared):
    plan, approval = fresh
    source, _ = prepared
    fake = CountedClient()
    with pytest.raises((ContractError, KeyError)):
        shared.collect(
            plan,
            replace(approval, sampler_hash=shared.sampler_hash()),
            adapter_factory=fake.factory,
        )
    with pytest.raises((ContractError, KeyError)):
        sampler.load_plan(
            source.packet_path, source.packet_path, source.source_root, source.packet_hash
        )
    assert fake.sequence == [] and not approval.result_root.exists()


@pytest.mark.parametrize(
    "count,terminal",
    [
        (184001, "COST_CAP_REACHED"),
        (272001, "INPUT_LIMIT_EXCEEDED"),
    ],
)
def test_rejects_over_budget_or_input_limit_without_lowering_output(fresh, count, terminal):
    plan, approval = fresh
    fake = CountedClient(counts=(count,))
    result = sampler.collect(plan, approval, adapter_factory=fake.factory)
    assert result["terminal"] == terminal
    assert fake.sequence == ["count"]
    assert result["recorded_cost_nanos"] == 0 and result["total_cost_known"]


def test_exact_cap_reserves_full_capacity_even_if_every_future_input_reaches_limit(fresh):
    plan, approval = fresh

    def full_output(response):
        response.usage.output_tokens = 25000
        response.usage.input_tokens_details.cached_tokens = 0

    fake = CountedClient(counts=(184000, 272000, 272000, 272000), edit_response=full_output)
    result = sampler.collect(plan, approval, adapter_factory=fake.factory)
    assert result["terminal"] == "SAMPLES_COLLECTED"
    assert result["recorded_cost_nanos"] == 1_200_000_000
    starts = [e["payload"] for e in events(approval) if e["event_type"] == "provider_call_started"]
    assert [r["remaining_cell_reserve_nanos"] for r in starts] == [
        949500000,
        633000000,
        316500000,
        0,
    ]
    assert all(r["output_ceiling"] == 25000 for r in starts)
    assert all("not an estimated" in r["remaining_input_basis"] for r in starts)


@pytest.mark.parametrize(
    "failure,expected",
    [
        ("count", "COUNT_TIMEOUT_OR_UNKNOWN"),
        ("create", "PROVIDER_TIMEOUT_OR_UNKNOWN"),
        ("usage", "PROVIDER_TIMEOUT_OR_UNKNOWN"),
        ("encrypted", "PROVIDER_CONTINUATION_ERROR"),
    ],
)
def test_partial_collection_stops_all_later_samples_on_uncertainty(fresh, failure, expected):
    plan, approval = fresh
    fake = CountedClient()

    def checkpoint(stage):
        if stage == "sample_recorded":
            fake.count_error = failure == "count"
            fake.create_error = failure == "create"
            if failure == "usage":
                fake.edit_response = lambda r: setattr(r, "usage", None)
            elif failure == "encrypted":
                fake.edit_response = lambda r: setattr(r.output[0], "encrypted_content", None)

    result = sampler.collect(plan, approval, adapter_factory=fake.factory, checkpoint=checkpoint)
    assert result["terminal"] == expected and result["sample_count"] == 1
    assert result["input_count_calls"] == 2
    assert len(fake.created) == (1 if failure == "count" else 2)
    assert result["total_cost_known"] == (failure in {"count", "encrypted"})
    assert not any(
        b"SECRET_EXCEPTION_SENTINEL" in raw for raw in snapshots(approval.result_root).values()
    )


@pytest.mark.parametrize(
    "stage,terminal",
    [
        ("dispatch_recorded", "PROVIDER_TIMEOUT_OR_UNKNOWN"),
        ("provider_returned", "PROVIDER_TIMEOUT_OR_UNKNOWN"),
        ("usage_recorded", "INTERRUPTED"),
        ("sample_recorded", "INTERRUPTED"),
    ],
)
def test_crash_inspection_never_retries_or_changes_existing_bytes(fresh, stage, terminal):
    plan, approval = fresh
    fake = CountedClient()

    def kill(current):
        if current == stage:
            raise ProcessKilled()

    with pytest.raises(ProcessKilled):
        sampler.collect(plan, approval, adapter_factory=fake.factory, checkpoint=kill)
    before = snapshots(approval.result_root)
    assert shared.inspect_result(approval.result_root)["terminal"] == terminal
    with pytest.raises(ContractError, match="already exists"):
        sampler.collect(plan, approval, adapter_factory=fake.factory)
    assert snapshots(approval.result_root) == before
    assert len(fake.counted) == 1 and len(fake.created) <= 1


def test_reasoning_only_incomplete_and_proposed_mutation_are_not_executed_or_corrected(fresh):
    plan, approval = fresh
    number = 0

    def alter(response):
        nonlocal number
        number += 1
        if number == 1:
            response.status = "incomplete"
            response.incomplete_details = type("Incomplete", (), {"reason": "max_output_tokens"})()
            response.output = response.output[:1]
        else:
            response.output[1].name = "replace_text"
            response.output[
                1
            ].arguments = '{"path":"never_create.py","old_text":"x","new_text":"y"}'

    fake = CountedClient(edit_response=alter)
    result = sampler.collect(plan, approval, adapter_factory=fake.factory)
    assert result["sample_count"] == 4 and not (approval.result_root / "never_create.py").exists()
    assert not any(
        e["event_type"] in {"protocol_correction", "action_started"} for e in events(approval)
    )


def test_count_cannot_mutate_schema_order_even_when_content_hash_matches(fresh):
    plan, approval = fresh
    fake = CountedClient()

    def factory(config):
        adapter = fake.factory(config)
        count = adapter.count_input_tokens_v2

        def reordered(request, **kwargs):
            before = sha256_json(request)
            value = count(request, **kwargs)
            request["tools"] = json.loads(canonical_json(request["tools"]))
            assert sha256_json(request) == before
            return value

        adapter.count_input_tokens_v2 = reordered
        return adapter

    result = sampler.collect(plan, approval, adapter_factory=factory)
    assert result["terminal"] == "SAMPLER_ERROR" and fake.sequence == ["count"]


def test_validation_is_read_only_and_collect_requires_four_response_flag(fresh, capsys):
    plan, approval = fresh
    args = [
        "--packet",
        str(plan.packet_path),
        "--packet-hash",
        plan.packet_hash,
        "--source-packet",
        str(plan.source_packet_path),
        "--source-state-root",
        str(plan.source_root),
    ]
    before = snapshots(plan.packet_path.parent, plan.source_root)
    assert sampler.main(["validate", *args]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["fresh_token_counts"] == {"A": None, "B": None}
    assert result["provider_calls"] == result["input_count_calls"] == 0
    assert result["sampler_hash"] == sha256_json(sampler.implementation_hashes())
    assert len(result["implementation_hashes"]) == 3
    for flag in ([], ["--approve-six-responses-zero-tools"]):
        with pytest.raises(SystemExit):
            sampler.main(["collect", *args, *flag])
    assert (
        not approval.result_root.exists()
        and snapshots(plan.packet_path.parent, plan.source_root) == before
    )


def test_both_design_roots_source_state_and_repository_are_protected(fresh):
    plan, approval = fresh
    for root in (
        plan.packet_path.parent,
        plan.source_packet_path.parent,
        plan.source_root,
        shared.repository_root(),
    ):
        with pytest.raises(ContractError, match="outside"):
            sampler.collect(plan, replace(approval, result_root=root / "new-fresh-results"))


def test_deadline_covers_all_four_responses_and_stops_before_later_count(fresh):
    plan, approval = fresh
    timer = [0.0]
    fake = CountedClient(clock=timer)

    def expire(stage):
        if stage == "sample_recorded":
            timer[0] = 1800.0

    result = sampler.collect(
        plan, approval, adapter_factory=fake.factory, clock=lambda: timer[0], checkpoint=expire
    )
    assert result["terminal"] == "LIMIT_REACHED" and fake.sequence == ["count", "create"]


def test_saved_request_identities_bind_bytes_and_schema_property_order(fresh):
    plan, approval = fresh
    fake = CountedClient()
    sampler.collect(plan, approval, adapter_factory=fake.factory)
    counts = [e["payload"] for e in events(approval) if e["event_type"] == "input_count_started"]
    for cell, count in zip(plan.cells, counts, strict=True):
        raw = Path(count["request_artifact"]["path"]).read_bytes()
        assert raw.decode("utf-8") == cell.request_json
        assert sha256_bytes(raw) == count["ordered_request_hash"] == sha256_text(cell.request_json)
        assert sha256_json(json.loads(raw)) == count["request_hash"] == cell.request_hash
