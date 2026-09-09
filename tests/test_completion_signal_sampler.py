from __future__ import annotations

import copy
import json
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace as NS

import pytest
from test_completion_signal_view import frozen_request
from test_decision_sampler import ProcessKilled, artifact_json, events
from test_failure_order_sampler import OrderedClient, snapshot, write_json

from diagnostics import completion_signal_sampler as sampler
from diagnostics import completion_signal_view as view
from diagnostics import decision_sampler as shared
from patchloop.artifacts import ArtifactStore
from patchloop.dev.conversation import history_metadata, reconstruct_state
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import dev_tool_schemas
from patchloop.errors import ContractError, RecoveryError
from patchloop.util import sha256_bytes, sha256_json


@pytest.fixture
def prepared_signal(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("live credentials/provider/task execution reached")

    monkeypatch.setattr(shared, "load_exact_openai_api_key", forbidden)
    monkeypatch.setattr(shared, "create_openai_client", forbidden)
    monkeypatch.setattr("patchloop.agent.model.create_openai_client", forbidden)
    monkeypatch.setattr("patchloop.dev.tools.DevToolGateway.execute", forbidden)
    source, views = tmp_path / "source", tmp_path / "views"
    source.mkdir()
    views.mkdir()
    write_json(
        source / "envelope.json",
        {
            "task_id": sampler.TASK_ID,
            "task_version": 2,
            "task_content_hash": sampler.TASK_HASH,
            "model": shared.MODEL,
        },
    )
    pairs = []
    for label in sampler.CHECKPOINTS:
        request = frozen_request()
        initial = json.loads(request["input"][1]["content"])
        initial["public_task"].update(task_id=sampler.TASK_ID, task_version=2)
        request["input"][1]["content"] = view.wire(initial).decode()
        state = reconstruct_state(request["input"])
        request.update(shared.SETTINGS)
        request["tools"] = dev_tool_schemas(
            finish_enabled=False,
            check_ids=state["remaining_visible_check_ids"],
            allowed_tools=state["available_tool_names"],
            read_paths=[],
        )
        root = source / label
        journal = DevJournal(root, f"run_dev_signal_{label}")
        store = ArtifactStore(root / "artifacts")
        start = journal.append(
            "turn_started",
            {
                "turn_id": f"turn_{label}",
                "max_parallel_reads": 4,
                "targeted_read_paths": [],
                "model_input_artifact": store.put_json(request["input"]).model_dump(mode="json"),
                "native_history": history_metadata(request["input"]),
            },
        )
        body = view.wire(request)
        ref = store.put_text(body.decode(), "application/json")
        count = journal.append(
            "input_count_started",
            {
                "turn_id": f"turn_{label}",
                "request_artifact": ref.model_dump(mode="json"),
                "ordered_request_hash": sha256_bytes(body),
            },
        )
        journal.append(
            "turn_decision_recorded",
            {
                "turn_id": f"turn_{label}",
                "future": "FUTURE_DECISION_NOT_INPUT",
            },
        )
        manifest = view.prepare(Path(ref.path), sha256_bytes(body), views / label)
        pairs.append(
            {
                **manifest,
                "checkpoint": label,
                "turn_id": f"turn_{label}",
                "turn_start_event_hash": start["event_hash"],
                "count_event_hash": count["event_hash"],
            }
        )
    write_json(
        views / "result.json",
        {
            "runtime_hash": shared.runtime_content_hash(),
            "independent_pairs": pairs,
        },
    )
    monkeypatch.setattr(
        sampler, "SOURCE_VIEW_HASH", sha256_bytes((views / "result.json").read_bytes())
    )
    root = tmp_path / "design"
    receipt = sampler.prepare(views, source, root)
    plan = sampler.load_plan(root / "packet.json", views, source, receipt["packet_hash"])
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


def test_eight_exact_independent_requests_no_tools_or_plaintext_reasoning(prepared_signal):
    plan, approval = prepared_signal
    before = snapshot(plan.view_root, plan.source_root, plan.packet_path.parent)
    fake = OrderedClient()
    result = sampler.collect(plan, approval, adapter_factory=fake.factory)
    assert result["terminal"] == "SAMPLES_COLLECTED" and result["provider_free"]
    assert result["sample_count"] == result["provider_calls"] == result["input_count_calls"] == 8
    assert result["recorded_cost_nanos"] == 8 * 158250
    assert result["tool_executions"] == 0
    assert result["task_acceptance"] == result["safety_state"] == "NOT_RUN"
    assert fake.sequence == ["count", "create"] * 8
    by_case = {}
    for cell, counted, sent in zip(plan.cells, fake.counted, fake.created, strict=True):
        request = {k: v for k, v in sent.items() if k != "timeout"}
        assert view.wire(request).decode() == cell.request_json
        assert counted["input"] == sent["input"] and counted["tools"] == sent["tools"]
        assert sent["reasoning"] == {"effort": "medium"}
        assert sent["store"] is False and sent["max_output_tokens"] == 25000
        assert len([i for i in sent["input"] if i.get("type") == "reasoning"]) == 2
        assert not any(
            s in cell.request_json
            for s in (
                "new_cipher_",
                "new_call_",
                "FUTURE_DECISION_NOT_INPUT",
                "NOT_ASSESSED",
            )
        )
        by_case.setdefault(cell.case_id, {})[cell.arm] = request
    for pair in by_case.values():
        assert view.without_further_edit_horizon(pair["A"])[0] == pair["B"]
        assert view.wire(pair["A"]["input"][:-1]) == view.wire(pair["B"]["input"][:-1])
    rows = events(approval)
    samples = [e["payload"] for e in rows if e["event_type"] == "sample_recorded"]
    assert [(s["case_id"], s["arm"]) for s in samples] == list(sampler.PROTOCOL.sampling_order)
    assert not any(e["event_type"] in {"action_started", "protocol_correction"} for e in rows)
    for sample in samples:
        public = artifact_json(sample["public_artifact"])
        assert not {"arm", "sample_number", "cost_nanos", "reasoning_effort"} & public.keys()
        assert (
            artifact_json(sample["continuation_ref"]["artifact"])["output_order"][0]["type"]
            == "reasoning"
        )
    for path, raw in snapshot(approval.result_root).items():
        assert b"PLAINTEXT_REASONING_SENTINEL" not in raw
        if path.suffix == ".jsonl":
            assert b"new_cipher_" not in raw
    assert snapshot(plan.view_root, plan.source_root, plan.packet_path.parent) == before
    assert shared.inspect_result(approval.result_root) == result


def test_jit_full_output_reservation_stops_at_cap_without_reserving_later_cells(prepared_signal):
    plan, approval = prepared_signal

    def maximal(response):
        response.usage.output_tokens = 25000
        response.usage.input_tokens_details.cached_tokens = 0

    fake = OrderedClient(count_value=100000, edit_response=maximal)
    result = sampler.collect(plan, approval, adapter_factory=fake.factory)
    assert result["terminal"] == "COST_CAP_REACHED"
    assert result["sample_count"] == result["provider_calls"] == 6
    assert result["input_count_calls"] == 7 and result["recorded_cost_nanos"] == 1125000000
    starts = [e["payload"] for e in events(approval) if e["event_type"] == "provider_call_started"]
    assert all(e["reserved_cost_nanos"] == 187500000 for e in starts)
    assert all(
        e["remaining_cell_reserve_nanos"] == 0 and e["output_ceiling"] == 25000 for e in starts
    )
    assert shared.SIX_CELL_PROTOCOL.reserve_future_calls is True


def test_input_limit_before_generation(prepared_signal):
    plan, approval = prepared_signal
    fake = OrderedClient(count_value=272001)
    result = sampler.collect(plan, approval, adapter_factory=fake.factory)
    assert result["terminal"] == "INPUT_LIMIT_EXCEEDED" and fake.sequence == ["count"]


@pytest.mark.parametrize(
    "failure,terminal",
    [
        ("count", "COUNT_TIMEOUT_OR_UNKNOWN"),
        ("create", "PROVIDER_TIMEOUT_OR_UNKNOWN"),
        ("usage", "PROVIDER_TIMEOUT_OR_UNKNOWN"),
        ("cipher", "PROVIDER_CONTINUATION_ERROR"),
    ],
)
def test_uncertainty_stops_without_retry_or_later_cells(prepared_signal, failure, terminal):
    plan, approval = prepared_signal
    fake = OrderedClient()

    def fail_next(stage):
        if stage == "sample_recorded":
            fake.count_error = failure == "count"
            fake.create_error = failure == "create"
            if failure == "usage":
                fake.edit_response = lambda r: setattr(r, "usage", None)
            elif failure == "cipher":
                fake.edit_response = lambda r: setattr(r.output[0], "encrypted_content", None)

    result = sampler.collect(plan, approval, adapter_factory=fake.factory, checkpoint=fail_next)
    assert result["terminal"] == terminal and result["sample_count"] == 1
    assert len(fake.counted) == 2 and len(fake.created) == (1 if failure == "count" else 2)
    assert all(
        b"SECRET_EXCEPTION_SENTINEL" not in b for b in snapshot(approval.result_root).values()
    )


@pytest.mark.parametrize(
    "stage,terminal",
    [
        ("dispatch_recorded", "PROVIDER_TIMEOUT_OR_UNKNOWN"),
        ("provider_returned", "PROVIDER_TIMEOUT_OR_UNKNOWN"),
        ("usage_recorded", "INTERRUPTED"),
        ("continuation_stored", "INTERRUPTED"),
        ("sample_recorded", "INTERRUPTED"),
    ],
)
def test_crash_read_only_inspect_and_no_duplicate_dispatch(prepared_signal, stage, terminal):
    plan, approval = prepared_signal
    fake = OrderedClient()

    def kill(current):
        if current == stage:
            raise ProcessKilled()

    with pytest.raises(ProcessKilled):
        sampler.collect(plan, approval, adapter_factory=fake.factory, checkpoint=kill)
    before = snapshot(approval.result_root)
    sequence = list(fake.sequence)
    assert shared.inspect_result(approval.result_root)["terminal"] == terminal
    with pytest.raises(ContractError, match="already exists"):
        sampler.collect(plan, approval, adapter_factory=fake.factory)
    assert snapshot(approval.result_root) == before and fake.sequence == sequence


@pytest.mark.parametrize(
    "target",
    [
        "receipt",
        "view",
        "source",
        "request",
        "review",
        "runtime",
        "schedule",
        "settings",
        "task",
    ],
)
def test_disk_identity_revalidated_before_root_or_provider(prepared_signal, monkeypatch, target):
    plan, approval = prepared_signal
    path = None
    if target == "receipt":
        path = plan.view_root / "result.json"
    elif target == "view":
        path = plan.view_root / "A1" / "B.json"
    elif target == "source":
        path = next((plan.source_root / "A1" / "runs").glob("*.jsonl"))
    elif target == "request":
        path = Path(plan.packet["request_artifacts"]["C1/A"]["path"])
    elif target == "review":
        path = plan.packet_path.parent / "protocol.md"
    elif target == "runtime":
        monkeypatch.setattr(shared, "runtime_content_hash", lambda: "changed")
    else:
        packet = copy.deepcopy(plan.packet)
        packet[
            {
                "schedule": "sampling_order",
                "settings": "fixed_request_settings",
                "task": "task_content_hash",
            }[target]
        ] = "changed"
        write_json(plan.packet_path, packet)
        digest = sha256_bytes(plan.packet_path.read_bytes())
        plan, approval = replace(plan, packet_hash=digest), replace(approval, packet_hash=digest)
    if path:
        path.write_bytes(path.read_bytes() + b" ")
    fake = OrderedClient()
    with pytest.raises((ContractError, RecoveryError, ValueError)):
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
def test_exact_cap_and_identity(prepared_signal, field, value):
    plan, approval = prepared_signal
    with pytest.raises(ContractError):
        sampler.collect(plan, replace(approval, **{field: value}))
    assert not approval.result_root.exists()


@pytest.mark.parametrize("response_kind", ["incomplete", "mutation"])
def test_incomplete_or_proposed_mutation_never_executes_or_chains(prepared_signal, response_kind):
    plan, approval = prepared_signal

    def incomplete(response):
        if response_kind == "incomplete":
            response.status = "incomplete"
            response.incomplete_details = NS(reason="max_output_tokens")
            response.output = response.output[:1]
        else:
            response.output[1].name = "replace_text"
            response.output[
                1
            ].arguments = '{"path":"never_created.py","old_text":"x","new_text":"y"}'

    result = sampler.collect(
        plan, approval, adapter_factory=OrderedClient(edit_response=incomplete).factory
    )
    assert result["sample_count"] == 8 and result["tool_executions"] == 0
    assert not any(
        e["event_type"] in {"action_started", "protocol_correction"} for e in events(approval)
    )
    assert not (approval.result_root / "never_created.py").exists()


def test_cli_validation_is_read_only_and_collection_requires_all_fields(prepared_signal, capsys):
    plan, approval = prepared_signal
    args = [
        "--packet",
        str(plan.packet_path),
        "--packet-hash",
        plan.packet_hash,
        "--view-root",
        str(plan.view_root),
        "--source-live-root",
        str(plan.source_root),
    ]
    before = snapshot(plan.view_root, plan.source_root, plan.packet_path.parent)
    assert sampler.main(["validate", *args]) == 0
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["provider_calls"] == receipt["input_count_calls"] == 0
    assert len(receipt["sampling_order"]) == 8
    with pytest.raises(SystemExit):
        sampler.main(["collect", *args, "--approve-eight-responses-zero-tools"])
    assert snapshot(plan.view_root, plan.source_root, plan.packet_path.parent) == before
    assert not approval.result_root.exists()
