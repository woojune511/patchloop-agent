from __future__ import annotations

import copy
import json
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace as NS

import pytest
from test_decision_sampler import FakeClient, ProcessKilled, artifact_json, events

from diagnostics import decision_sampler as shared
from diagnostics import failure_order_sampler as sampler
from patchloop.artifacts import ArtifactStore
from patchloop.dev.conversation import assemble_model_input, history_metadata
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import dev_tool_schemas
from patchloop.errors import ContractError, RecoveryError
from patchloop.util import canonical_json, sha256_bytes, sha256_json


def snapshot(*roots):
    return {p: p.read_bytes() for root in roots for p in root.rglob("*") if p.is_file()}


def write_json(path, value):
    path.write_text(canonical_json(value), encoding="utf-8")


@pytest.fixture
def prepared_order(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("live credentials/provider/task execution reached")

    monkeypatch.setattr(shared, "load_exact_openai_api_key", forbidden)
    monkeypatch.setattr(shared, "create_openai_client", forbidden)
    monkeypatch.setattr("patchloop.agent.model.create_openai_client", forbidden)
    monkeypatch.setattr("patchloop.dev.tools.DevToolGateway.execute", forbidden)
    source = tmp_path / "source"
    journal = DevJournal(source, "run_dev_synthetic_order")
    store = ArtifactStore(source / "artifacts")
    envelope = {
        "runtime_hash": shared.runtime_content_hash(),
        "model_hash": sha256_json("model"),
        "task_id": "synthetic-public",
        "task_version": 2,
        "task_content_hash": sha256_json("synthetic-public"),
    }
    write_json(journal.envelope_path, envelope)
    state = {
        "public_task": {"task_id": "synthetic-public", "task_version": 2},
        "current_diff": {"patch_hash": "current-diff", "patch": "PUBLIC_PATCH"},
        "mutation_scope_budget": {"current_diff_lines": 36, "max_diff_lines": 50},
        "visible_check_status": [{"check_id": "visible", "status": "FAIL"}],
        "remaining_budget": {"accepted_mutations": 1, "model_calls": 20},
        "available_tool_names": ["read_file", "replace_text", "search_files", "stop_task"],
        "current_public_failure": None,
    }
    failure = {
        "evidence_currency": "current",
        "current_diff_hash": "current-diff",
        "failure_summary": {
            "lines": ["FAILED alpha", "FAILED beta", "FAILED gamma"],
            "observed_count": 3,
            "truncated": False,
        },
    }
    items, history, actions = None, [], []
    for number in (1, 2, 3):
        state["remaining_budget"]["model_calls"] = 23 - number
        state["current_public_failure"] = failure if number == 3 else None
        items = assemble_model_input(
            system_prompt="PUBLIC_SYSTEM", state=state, history=history, previous_input=items
        )
        turn = {
            "turn_id": f"turn_{number}",
            "model_input_artifact": store.put_json(items).model_dump(mode="json"),
            "context_artifact": store.put_json(state).model_dump(mode="json"),
            "native_history": history_metadata(items),
            "max_parallel_reads": 4,
            "available_tool_names": state["available_tool_names"],
            "targeted_read_paths": [],
            "transcript_action_ids": list(actions),
        }
        event = journal.append("turn_started", turn)
        request = {
            **shared.SETTINGS,
            "input": items,
            "tools": dev_tool_schemas(
                finish_enabled=False,
                check_ids=[],
                allowed_tools=state["available_tool_names"],
                read_paths=[],
            ),
            "reasoning": {"effort": "medium"},
        }
        journal.append(
            "provider_call_started",
            {"turn_id": turn["turn_id"], "input_tokens": 100, "request_hash": sha256_json(request)},
        )
        if number == 3:
            break
        action = f"old_call_{number}"
        actions.append(action)
        result = {
            "action_id": action,
            "tool": "read_file",
            "status": "succeeded",
            "output": {"spans": [], "observation": "PUBLIC_OLD_RESULT"},
        }
        journal.append("action_finished", {"result": result})
        history = [
            {
                "type": "reasoning",
                "id": f"r{number}",
                "encrypted_content": f"opaque{number}",
                "summary": [],
            },
            {"type": "function_call", "call_id": action, "name": "read_file", "arguments": "{}"},
            {"type": "function_call_output", "call_id": action, "output": canonical_json(result)},
        ]
    journal.append(
        "turn_decision_recorded",
        {
            "turn_id": turn["turn_id"],
            "future_label": "FUTURE_DECISION_NOT_INPUT",
        },
    )
    audit = tmp_path / "audit"
    audit.mkdir()
    manifest = {
        "run_id": journal.run_id,
        "turn_number": 3,
        "turn_id": turn["turn_id"],
        "cutoff_event_sequence": event["sequence"],
        "cutoff_event_hash": event["event_hash"],
        "journal": {
            "path": str(journal.path),
            "content_hash": sha256_bytes(journal.path.read_bytes()),
        },
        "envelope": {
            "path": str(journal.envelope_path),
            "content_hash": sha256_bytes(journal.envelope_path.read_bytes()),
        },
        "runtime_hash": envelope["runtime_hash"],
        "model_hash": envelope["model_hash"],
        "native_input_artifact": turn["model_input_artifact"],
        "context_artifact": turn["context_artifact"],
        "native_history": turn["native_history"],
        "allowed_tools": turn["available_tool_names"],
        "current_diff_hash": "current-diff",
    }
    alternate = sampler.permute_latest_summary(items)
    contrast = {
        "dispatch_authorized": False,
        "original_input_hash": turn["model_input_artifact"]["content_hash"],
        "prospective_alternate_input_hash": sha256_json(alternate),
        "sole_change": {
            "item": len(items) - 1,
            "field": "content(JSON).state.current_public_failure.failure_summary.lines",
            "permutation": [1, 2, 0],
        },
    }
    write_json(audit / "checkpoint-manifest.json", manifest)
    write_json(audit / "contrast-spec.json", contrast)
    (audit / "observed-decision.json").write_text("REVIEWER_ONLY_SENTINEL", encoding="utf-8")
    monkeypatch.setattr(
        sampler,
        "AUDIT_HASHES",
        {name: sha256_bytes((audit / name).read_bytes()) for name in sampler.AUDIT_HASHES},
    )
    design = tmp_path / "design"
    sampler.prepare(audit, source, design)
    packet_path = design / "packet.json"
    plan = sampler.load_plan(packet_path, audit, source, sha256_bytes(packet_path.read_bytes()))
    approval = shared.Approval(
        plan.packet_hash,
        sampler.sampler_hash(),
        tmp_path / "results",
        tmp_path / "ABSENT.env",
        Decimal("1.20"),
        sha256_json(shared.price_identity()),
        datetime.now(UTC).date().isoformat(),
    )
    return plan, approval


class OrderedClient(FakeClient):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.sequence = []

    def count(self, **request):
        self.sequence.append("count")
        return super().count(**request)

    def create(self, **request):
        self.sequence.append("create")
        return super().create(**request)


def test_only_latest_failure_permutation_changes_both_arms_keep_native_reasoning(prepared_order):
    plan, approval = prepared_order
    before = snapshot(plan.source_root, plan.audit_root, plan.packet_path.parent)
    a, b = (json.loads(plan.cells[i].request_json) for i in (0, 1))
    assert a["input"][:-1] == b["input"][:-1]
    assert a["tools"] == b["tools"]
    va, vb = (json.loads(r["input"][-1]["content"]) for r in (a, b))
    sa = va["state"]["current_public_failure"]["failure_summary"]
    sb = vb["state"]["current_public_failure"]["failure_summary"]
    assert sb["lines"] == [sa["lines"][1], sa["lines"][2], sa["lines"][0]]
    sb["lines"] = sa["lines"]
    assert va == vb
    fake = OrderedClient()
    result = sampler.collect(plan, approval, adapter_factory=fake.factory)
    assert result["terminal"] == "SAMPLES_COLLECTED" and result["provider_free"]
    assert result["provider_calls"] == result["input_count_calls"] == result["sample_count"] == 4
    assert result["tool_executions"] == 0
    assert result["task_acceptance"] == result["safety_state"] == "NOT_RUN"
    assert fake.sequence == ["count", "create"] * 4
    for cell, counted, created in zip(plan.cells, fake.counted, fake.created, strict=True):
        wire = sampler.wire_json({k: v for k, v in created.items() if k != "timeout"})
        assert wire == cell.request_json
        assert counted["input"] == created["input"] and counted["tools"] == created["tools"]
        assert created["reasoning"] == {"effort": "medium"}
        assert created["store"] is False and created["max_output_tokens"] == 25000
        assert len([i for i in created["input"] if i.get("type") == "reasoning"]) == 2
        assert all(
            s not in wire
            for s in (
                "new_cipher_",
                "new_call_",
                "FUTURE_DECISION_NOT_INPUT",
                "REVIEWER_ONLY_SENTINEL",
            )
        )
    rows = events(approval)
    samples = [e["payload"] for e in rows if e["event_type"] == "sample_recorded"]
    assert [(r["arm"], r["sample_number"]) for r in samples] == list(PROTOCOL_ORDER)
    for row in samples:
        public = artifact_json(row["public_artifact"])
        assert not {"arm", "sample_number", "cost_nanos", "reasoning_effort"} & public.keys()
        continuation = artifact_json(row["continuation_ref"]["artifact"])
        assert [i["type"] for i in continuation["output_order"]] == [
            "reasoning",
            "function_call_ref",
        ]
    for path, raw in snapshot(approval.result_root).items():
        assert b"PLAINTEXT_REASONING_SENTINEL" not in raw
        if path.suffix == ".jsonl":
            assert b"new_cipher_" not in raw
    assert snapshot(plan.source_root, plan.audit_root, plan.packet_path.parent) == before
    assert shared.inspect_result(approval.result_root) == result


PROTOCOL_ORDER = (("A", 1), ("B", 1), ("B", 2), ("A", 2))


@pytest.mark.parametrize(
    "target",
    [
        "audit",
        "journal",
        "input",
        "request",
        "review",
        "runtime",
        "sampler",
        "schedule",
        "effort",
    ],
)
def test_tampering_rejected_before_root_key_or_client(prepared_order, monkeypatch, target):
    plan, approval = prepared_order
    if target == "audit":
        path = plan.audit_root / "contrast-spec.json"
    elif target == "journal":
        path = plan.source_root / "runs" / (plan.packet["source_run_id"] + ".jsonl")
    elif target == "input":
        manifest = json.loads((plan.audit_root / "checkpoint-manifest.json").read_bytes())
        path = Path(manifest["native_input_artifact"]["path"])
    elif target == "request":
        path = Path(plan.packet["request_artifacts"]["B"]["path"])
    elif target == "review":
        path = plan.packet_path.parent / "rubric.json"
    elif target == "runtime":
        monkeypatch.setattr(shared, "runtime_content_hash", lambda: "changed")
        path = None
    else:
        packet = copy.deepcopy(plan.packet)
        packet[
            {"sampler": "sampler_hash", "schedule": "sampling_order", "effort": "reasoning_effort"}[
                target
            ]
        ] = "changed"
        write_json(plan.packet_path, packet)
        digest = sha256_bytes(plan.packet_path.read_bytes())
        plan, approval = replace(plan, packet_hash=digest), replace(approval, packet_hash=digest)
        path = None
    if path:
        path.write_bytes(path.read_bytes() + b" ")
    fake = OrderedClient()
    with pytest.raises((ContractError, RecoveryError)):
        sampler.collect(plan, approval, adapter_factory=fake.factory)
    assert not approval.result_root.exists() and fake.sequence == []


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
def test_exact_approval(prepared_order, field, value):
    plan, approval = prepared_order
    with pytest.raises(ContractError):
        sampler.collect(plan, replace(approval, **{field: value}))
    assert not approval.result_root.exists()


@pytest.mark.parametrize(
    "count,terminal", [(184001, "COST_CAP_REACHED"), (272001, "INPUT_LIMIT_EXCEEDED")]
)
def test_full_future_capacity_reserved_without_lowering_output(prepared_order, count, terminal):
    plan, approval = prepared_order
    fake = OrderedClient(count_value=count)
    result = sampler.collect(plan, approval, adapter_factory=fake.factory)
    assert result["terminal"] == terminal and fake.sequence == ["count"]
    assert result["recorded_cost_nanos"] == 0


@pytest.mark.parametrize(
    "failure,expected",
    [
        ("count", "COUNT_TIMEOUT_OR_UNKNOWN"),
        ("create", "PROVIDER_TIMEOUT_OR_UNKNOWN"),
        ("usage", "PROVIDER_TIMEOUT_OR_UNKNOWN"),
        ("encrypted", "PROVIDER_CONTINUATION_ERROR"),
    ],
)
def test_uncertainty_stops_all_future_samples(prepared_order, failure, expected):
    plan, approval = prepared_order
    fake = OrderedClient()

    def fail_after_first(stage):
        if stage == "sample_recorded":
            fake.count_error = failure == "count"
            fake.create_error = failure == "create"
            if failure == "usage":
                fake.edit_response = lambda r: setattr(r, "usage", None)
            elif failure == "encrypted":
                fake.edit_response = lambda r: setattr(r.output[0], "encrypted_content", None)

    result = sampler.collect(
        plan, approval, adapter_factory=fake.factory, checkpoint=fail_after_first
    )
    assert result["terminal"] == expected and result["sample_count"] == 1
    assert len(fake.counted) == 2 and len(fake.created) == (1 if failure == "count" else 2)
    assert not any(
        b"SECRET_EXCEPTION_SENTINEL" in raw for raw in snapshot(approval.result_root).values()
    )


@pytest.mark.parametrize(
    "stage,terminal",
    [("dispatch_recorded", "PROVIDER_TIMEOUT_OR_UNKNOWN"), ("usage_recorded", "INTERRUPTED")],
)
def test_crash_inspection_is_read_only_and_cannot_resume(prepared_order, stage, terminal):
    plan, approval = prepared_order
    fake = OrderedClient()

    def kill(current):
        if current == stage:
            raise ProcessKilled()

    with pytest.raises(ProcessKilled):
        sampler.collect(plan, approval, adapter_factory=fake.factory, checkpoint=kill)
    before = snapshot(approval.result_root)
    assert shared.inspect_result(approval.result_root)["terminal"] == terminal
    with pytest.raises(ContractError, match="already exists"):
        sampler.collect(plan, approval, adapter_factory=fake.factory)
    assert snapshot(approval.result_root) == before


def test_incomplete_or_proposed_mutation_is_not_executed_or_corrected(prepared_order):
    plan, approval = prepared_order
    counter = 0

    def alter(response):
        nonlocal counter
        counter += 1
        if counter == 1:
            response.status = "incomplete"
            response.incomplete_details = NS(reason="max_output_tokens")
            response.output = response.output[:1]
        else:
            response.output[1].name = "replace_text"
            response.output[
                1
            ].arguments = '{"path":"never_created.py","old_text":"x","new_text":"y"}'

    result = sampler.collect(
        plan, approval, adapter_factory=OrderedClient(edit_response=alter).factory
    )
    assert result["sample_count"] == 4
    assert not any(
        e["event_type"] in {"action_started", "protocol_correction"} for e in events(approval)
    )
    assert not (approval.result_root / "never_created.py").exists()


def test_validation_and_cli_boundary_are_provider_free(prepared_order, capsys):
    plan, approval = prepared_order
    args = [
        "--packet",
        str(plan.packet_path),
        "--packet-hash",
        plan.packet_hash,
        "--audit-root",
        str(plan.audit_root),
        "--source-state-root",
        str(plan.source_root),
    ]
    before = snapshot(plan.audit_root, plan.source_root, plan.packet_path.parent)
    assert sampler.main(["validate", *args]) == 0
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["fresh_token_counts"] == {"A": None, "B": None}
    assert receipt["provider_calls"] == receipt["input_count_calls"] == 0
    assert len(receipt["implementation_hashes"]) == 2
    for flag in (
        [],
        ["--approve-four-responses-zero-tools"],
        ["--approve-six-responses-zero-tools"],
    ):
        with pytest.raises(SystemExit):
            sampler.main(["collect", *args, *flag])
    assert not approval.result_root.exists()
    assert snapshot(plan.audit_root, plan.source_root, plan.packet_path.parent) == before


def test_existing_collectors_reject_new_packet_and_all_roots_protected(prepared_order):
    plan, approval = prepared_order
    with pytest.raises((ContractError, KeyError)):
        shared.collect(plan, replace(approval, sampler_hash=shared.sampler_hash()))
    for root in (
        plan.audit_root,
        plan.source_root,
        plan.packet_path.parent,
        shared.repository_root(),
    ):
        with pytest.raises(ContractError, match="outside"):
            sampler.collect(plan, replace(approval, result_root=root / "new-order-results"))
    assert not approval.result_root.exists()


@pytest.mark.parametrize("change", ["historical", "truncated", "missing", "duplicate"])
def test_order_transform_requires_complete_current_distinct_rows(prepared_order, change):
    plan, _ = prepared_order
    items = json.loads(plan.cells[0].request_json)["input"]
    view = json.loads(items[-1]["content"])
    failure = view["state"]["current_public_failure"]
    if change == "historical":
        failure["evidence_currency"] = "historical"
    elif change == "truncated":
        failure["failure_summary"]["truncated"] = True
    elif change == "missing":
        failure["failure_summary"]["lines"].pop()
    else:
        failure["failure_summary"]["lines"][1] = failure["failure_summary"]["lines"][0]
    items[-1]["content"] = sampler.wire_json(view)
    with pytest.raises(ContractError, match="three complete"):
        sampler.permute_latest_summary(items)


def test_count_may_not_reorder_tools_even_when_canonical_hash_is_unchanged(prepared_order):
    plan, approval = prepared_order
    fake = OrderedClient()

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


def test_deadline_stops_before_another_sample(prepared_order):
    plan, approval = prepared_order
    timer = [0.0]
    fake = OrderedClient(clock=timer)

    def expire(stage):
        if stage == "sample_recorded":
            timer[0] = 1800.0

    result = sampler.collect(
        plan, approval, adapter_factory=fake.factory, clock=lambda: timer[0], checkpoint=expire
    )
    assert result["terminal"] == "LIMIT_REACHED" and fake.sequence == ["count", "create"]


def test_prepare_does_not_overwrite_existing_design_or_protected_roots(prepared_order):
    plan, _ = prepared_order
    before = snapshot(plan.packet_path.parent, plan.audit_root, plan.source_root)
    with pytest.raises(ContractError, match="already exists"):
        sampler.prepare(plan.audit_root, plan.source_root, plan.packet_path.parent)
    for root in (plan.source_root, plan.audit_root, shared.repository_root()):
        with pytest.raises(ContractError, match="external"):
            sampler.prepare(plan.audit_root, plan.source_root, root / "new-order-design")
    assert snapshot(plan.packet_path.parent, plan.audit_root, plan.source_root) == before
