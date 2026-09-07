from __future__ import annotations

import copy
import json
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

from diagnostics import decision_sampler as sampler
from patchloop.agent.model import FunctionCallContinuationRef, OpenAIResponsesAdapter
from patchloop.artifacts import ArtifactStore
from patchloop.dev.conversation import assemble_model_input, history_metadata
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import dev_tool_schemas
from patchloop.errors import ContractError
from patchloop.util import canonical_json, sha256_bytes, sha256_json


def write_json(path, data):
    path.write_text(canonical_json(data), encoding="utf-8")


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    # Synthetic public source only; tests need neither the user's state nor credentials.
    root = tmp_path / "source"
    store = ArtifactStore(root / "artifacts")
    journal = DevJournal(root, "run_dev_synthetic")
    task = {
        "task_id": "synthetic-public-task",
        "task_version": 2,
        "task_content_hash": sha256_json("public synthetic fixture"),
    }
    write_json(journal.envelope_path, task)
    state = {
        "public_task": task,
        "mutation_scope_budget": {"max_diff_lines": 50},
        "visible_check_status": [{"check_id": "visible", "status": "NOT_RUN"}],
    }
    schema_inputs = {
        "finish_enabled": False,
        "check_ids": ["visible"],
        "allowed_tools": [
            "read_file",
            "replace_text",
            "run_check",
            "run_probe",
            "search_files",
            "stop_task",
        ],
        "read_paths": [],
    }
    schemas = dev_tool_schemas(**schema_inputs)
    cases, history, action_ids = [], [], []
    for number in range(1, 33):
        items = assemble_model_input(
            system_prompt="Synthetic public task only", state=state, history=copy.deepcopy(history)
        )
        metadata = history_metadata(items)
        artifact = store.put_json(items).model_dump(mode="json")
        context = store.put_json(state).model_dump(mode="json")
        event = journal.append(
            "turn_started",
            {
                "turn_id": f"turn_{number}",
                "model_input_artifact": artifact,
                "context_artifact": context,
                "native_history": metadata,
                "available_tool_names": schema_inputs["allowed_tools"],
                "targeted_read_paths": [],
                "max_parallel_reads": 4,
                "transcript_action_ids": list(action_ids),
            },
        )
        medium = {
            **sampler.SETTINGS,
            "input": items,
            "tools": schemas,
            "reasoning": {"effort": "medium"},
        }
        high = {**medium, "reasoning": {"effort": "high"}}
        journal.append(
            "provider_call_started",
            {"turn_id": f"turn_{number}", "request_hash": sha256_json(medium)},
        )
        if number in (6, 21, 32):
            cases.append(
                {
                    "case_id": f"C{len(cases) + 1}",
                    "source_turn_number": number,
                    "source_turn_id": f"turn_{number}",
                    "turn_started_journal_line": event["sequence"],
                    "input_artifact": artifact,
                    "canonical_context_artifact": context,
                    "native_history": metadata,
                    "tool_schema_inputs": schema_inputs,
                    "tools_hash": sha256_json(schemas),
                    "schema_order": [s["name"] for s in schemas],
                    "state_hash": sha256_json(state),
                    "scope_budget": state["mutation_scope_budget"],
                    "continuation_items": number - 1,
                    "prior_action_count": number - 1,
                    "historical_input_count": 100,
                    "medium_request_hash": sha256_json(medium),
                    "high_request_hash": sha256_json(high),
                }
            )
        action_id = f"old_call_{number}"
        history.extend(
            [
                {
                    "type": "reasoning",
                    "id": f"r{number}",
                    "encrypted_content": f"opaque{number}",
                    "summary": [],
                },
                {
                    "type": "function_call",
                    "call_id": action_id,
                    "name": "read_file",
                    "arguments": "{}",
                },
                {
                    "type": "function_call_output",
                    "call_id": action_id,
                    "output": "public observation",
                },
            ]
        )
        action_ids.append(action_id)
        journal.append("action_finished", {"result": {"action_id": action_id}})
    design = tmp_path / "design"
    design.mkdir()
    (design / "rubric.json").write_text('{"review_only":"RUBRIC_SENTINEL"}', encoding="utf-8")
    (design / "protocol.md").write_text("Reviewer only protocol", encoding="utf-8")
    packet = {
        **task,
        "status": "PREPARED_NOT_EXECUTABLE",
        "dispatch_enabled": False,
        "official": False,
        "claim_eligible": False,
        "actual_provider_calls": 0,
        "actual_input_count_calls": 0,
        "actual_cost_nanos": 0,
        "runtime_hash": sampler.runtime_content_hash(),
        "model": sampler.MODEL,
        "fixed_request_settings": sampler.SETTINGS,
        "arms": [
            {"id": arm, "reasoning_effort": effort} for arm, effort in sampler.EFFORTS.items()
        ],
        "sampling_order": sampler.ORDER,
        "maximum_generation_calls": 6,
        "maximum_input_count_calls": 6,
        "samples_per_case_per_arm": 1,
        "maximum_tool_executions": 0,
        "maximum_correction_calls": 0,
        "maximum_sdk_retries": 0,
        "proposed_total_active_seconds": 1800,
        "proposed_total_cap_usd": "1.20",
        "source_run_id": journal.run_id,
        "source_journal_hash": sha256_bytes(journal.path.read_bytes()),
        "cases": cases,
    }
    packet_path = design / "packet.json"
    write_json(packet_path, packet)
    plan = sampler.load_plan(packet_path, root, sha256_bytes(packet_path.read_bytes()))
    approval = sampler.Approval(
        plan.packet_hash,
        sampler.sampler_hash(),
        tmp_path / "results",
        tmp_path / "ABSENT.env",
        Decimal("1.20"),
        sha256_json(sampler.price_identity()),
        datetime.now(UTC).date().isoformat(),
    )

    def forbidden(*args, **kwargs):
        pytest.fail("credential, live provider or task execution reached")

    monkeypatch.setattr(sampler, "load_exact_openai_api_key", forbidden)
    monkeypatch.setattr(sampler, "create_openai_client", forbidden)
    monkeypatch.setattr("patchloop.agent.model.create_openai_client", forbidden)
    monkeypatch.setattr("patchloop.dev.tools.DevToolGateway.execute", forbidden)
    return plan, approval


class FakeClient:
    max_retries = 0

    def __init__(
        self,
        *,
        count_value=100,
        edit_response=lambda r: None,
        count_error=False,
        create_error=False,
        clock=None,
    ):
        self.counted, self.created, self.responses_returned = [], [], []
        self.count_value = count_value
        self.edit_response = edit_response
        self.count_error, self.create_error, self.clock = count_error, create_error, clock
        self.responses = NS(input_tokens=NS(count=self.count), create=self.create)

    def factory(self, config):
        return OpenAIResponsesAdapter(config, api_key="fake-no-secret", client=self)

    def count(self, **request):
        self.counted.append(copy.deepcopy(request))
        if self.count_error:
            raise TimeoutError("SECRET_EXCEPTION_SENTINEL")
        return NS(input_tokens=self.count_value)

    def create(self, **request):
        self.created.append(copy.deepcopy(request))
        if self.create_error:
            raise TimeoutError("SECRET_EXCEPTION_SENTINEL")
        if self.clock is not None:
            self.clock[0] += 10
        number = len(self.created)
        arguments = {
            "path": "public.py",
            "start_line": 1,
            "end_line": 9,
            "turn_decision": {
                "mode": "inspect",
                "basis": "Check public implementation",
                "evidence_goal": "Find behavior owner",
                "memory_update": None,
            },
        }
        response = NS(
            id=f"response_{number}",
            model=sampler.MODEL,
            status="completed",
            incomplete_details=None,
            usage=NS(
                input_tokens=self.count_value,
                input_tokens_details=NS(cached_tokens=10),
                output_tokens=20,
                output_tokens_details=NS(reasoning_tokens=12),
            ),
            output=[
                NS(
                    type="reasoning",
                    id=f"new_reasoning_{number}",
                    encrypted_content=f"new_cipher_{number}",
                    status="completed",
                    summary=["PLAINTEXT_REASONING_SENTINEL"],
                    content="PLAINTEXT_REASONING_SENTINEL",
                ),
                NS(
                    type="function_call",
                    name="read_file",
                    call_id=f"new_call_{number}",
                    arguments=canonical_json(arguments),
                ),
            ],
        )
        self.edit_response(response)
        self.responses_returned.append(response)
        return response


def events(approval):
    envelope = json.loads((approval.result_root / "envelope.json").read_bytes())
    return DevJournal(approval.result_root, envelope["run_id"]).events()


def artifact_json(ref):
    return json.loads(Path(ref["path"]).read_bytes())


def test_six_frozen_cells_only_effort_changes_no_key_or_tool_execution(prepared):
    plan, approval = prepared
    before = {p: p.read_bytes() for p in plan.source_root.rglob("*") if p.is_file()}
    fake = FakeClient()
    result = sampler.collect(plan, approval, adapter_factory=fake.factory)
    assert result["terminal"] == "SAMPLES_COLLECTED"
    assert result["sample_count"] == result["provider_calls"] == result["input_count_calls"] == 6
    assert result["provider_free"] and result["tool_executions"] == 0
    assert result["task_acceptance"] == result["safety_state"] == "NOT_RUN"
    assert result["recorded_cost_nanos"] == 6 * 158250
    for cell, counted, sent in zip(plan.cells, fake.counted, fake.created, strict=True):
        assert (
            sampler.sha256_json({k: v for k, v in sent.items() if k != "timeout"})
            == cell.request_hash
        )
        assert sent["reasoning"]["effort"] == sampler.EFFORTS[cell.arm]
        assert sent["max_output_tokens"] == 25000 and sent["store"] is False
        assert counted["input"] == sent["input"] == json.loads(cell.request_json)["input"]
        assert "RUBRIC_SENTINEL" not in canonical_json(sent)
        assert "new_cipher_" not in canonical_json(sent)  # Never chain sampled output.
    assert all(p.read_bytes() == content for p, content in before.items())
    rows = events(approval)
    assert len([e for e in rows if e["event_type"] == "provider_call_finished"]) == 6
    recorded = [e["payload"] for e in rows if e["event_type"] == "sample_recorded"]
    assert [(e["case_id"], e["arm"]) for e in recorded] == list(sampler.ORDER)
    for row in recorded:
        continuation = artifact_json(row["continuation_ref"]["artifact"])
        assert [i["type"] for i in continuation["output_order"]] == [
            "reasoning",
            "function_call_ref",
        ]
        public = artifact_json(row["public_artifact"])
        assert public["batch_shape"] == "parallel_read"
        assert not {"arm", "reasoning_effort", "cost_nanos", "latency"} & public.keys()
    for path in approval.result_root.rglob("*"):
        if path.is_file():
            assert b"PLAINTEXT_REASONING_SENTINEL" not in path.read_bytes()
            assert b"SECRET_EXCEPTION_SENTINEL" not in path.read_bytes()
    journal_bytes = next((approval.result_root / "runs").glob("*.jsonl")).read_bytes()
    assert b"new_cipher_" not in journal_bytes
    assert sampler.inspect_result(approval.result_root) == result


@pytest.mark.parametrize(
    "field,value",
    [
        ("sampler_hash", "wrong"),
        ("packet_hash", "wrong"),
        ("max_cost_usd", Decimal("2")),
        ("pricing_hash", "wrong"),
        ("pricing_verified_on", "2000-01-01"),
    ],
)
def test_exact_approval_rejects_before_calls(prepared, field, value):
    plan, approval = prepared
    fake = FakeClient()
    with pytest.raises(ContractError):
        sampler.collect(plan, replace(approval, **{field: value}), adapter_factory=fake.factory)
    assert fake.counted == fake.created == []
    assert not approval.result_root.exists()


@pytest.mark.parametrize("change", ["settings", "order", "cutoff", "mask", "history", "runtime"])
def test_tampered_packet_rejected_even_with_new_packet_hash(prepared, change):
    plan, approval = prepared
    packet = json.loads(plan.packet_path.read_bytes())
    if change == "settings":
        packet["fixed_request_settings"]["max_output_tokens"] = 4096
    elif change == "order":
        packet["sampling_order"].reverse()
    elif change == "cutoff":
        packet["cases"][0]["source_turn_number"] = 7
    elif change == "mask":
        packet["cases"][0]["tool_schema_inputs"]["allowed_tools"].remove("read_file")
    elif change == "history":
        packet["cases"][0]["input_artifact"] = packet["cases"][2]["input_artifact"]
    else:
        packet["runtime_hash"] = "wrong"
    write_json(plan.packet_path, packet)
    with pytest.raises(ContractError):
        sampler.load_plan(
            plan.packet_path, plan.source_root, sha256_bytes(plan.packet_path.read_bytes())
        )
    assert not approval.result_root.exists()


def test_fixed_capacity_for_all_remaining_cells_stops_before_create(prepared):
    plan, approval = prepared
    # Current cell fits $1.20, but all six full ceilings no longer fit together.
    fake = FakeClient(count_value=1_000_000)
    result = sampler.collect(plan, approval, adapter_factory=fake.factory)
    assert result["terminal"] == "COST_CAP_REACHED"
    assert len(fake.counted) == 1 and not fake.created
    assert result["recorded_cost_nanos"] == 0


@pytest.mark.parametrize(
    "kind,expected",
    [
        ("count", "COUNT_TIMEOUT_OR_UNKNOWN"),
        ("transport", "PROVIDER_TIMEOUT_OR_UNKNOWN"),
        ("usage", "PROVIDER_TIMEOUT_OR_UNKNOWN"),
        ("cached", "PROVIDER_TIMEOUT_OR_UNKNOWN"),
        ("ceiling", "PROVIDER_TIMEOUT_OR_UNKNOWN"),
        ("model", "PROVIDER_TIMEOUT_OR_UNKNOWN"),
        ("encrypted", "PROVIDER_CONTINUATION_ERROR"),
    ],
)
def test_uncertainty_stops_entire_pilot_and_never_logs_raw_errors(prepared, kind, expected):
    plan, approval = prepared

    def alter(response):
        if kind == "usage":
            response.usage = None
        elif kind == "cached":
            response.usage.input_tokens_details.cached_tokens = 101
        elif kind == "ceiling":
            response.usage.output_tokens = 25001
        elif kind == "model":
            response.model = "wrong-snapshot"
        elif kind == "encrypted":
            response.output[0].encrypted_content = None

    fake = FakeClient(
        edit_response=alter, count_error=kind == "count", create_error=kind == "transport"
    )
    result = sampler.collect(plan, approval, adapter_factory=fake.factory)
    assert result["terminal"] == expected
    assert len(fake.counted) == 1 and len(fake.created) <= 1
    assert result["total_cost_known"] == (kind in {"count", "encrypted"})
    assert not any(
        b"SECRET_EXCEPTION_SENTINEL" in p.read_bytes()
        for p in approval.result_root.rglob("*")
        if p.is_file()
    )


def test_reasoning_only_incomplete_is_recorded_without_correction(prepared):
    plan, approval = prepared

    def alter(response):
        response.status = "incomplete"
        response.incomplete_details = NS(reason="max_output_tokens")
        response.output = response.output[:1]

    fake = FakeClient(edit_response=alter)
    result = sampler.collect(plan, approval, adapter_factory=fake.factory)
    assert result["terminal"] == "SAMPLES_COLLECTED"
    assert len(fake.created) == 6
    for row in events(approval):
        assert row["event_type"] != "protocol_correction"
        if row["event_type"] == "sample_recorded":
            public = artifact_json(row["payload"]["public_artifact"])
            assert public["error_code"] == "incomplete_response" and public["tool_calls"] == []
            assert row["payload"]["continuation_ref"]["reasoning_item_count"] == 1


def test_returned_mutation_is_not_applied(prepared):
    plan, approval = prepared

    def alter(response):
        response.output[1].name = "replace_text"
        response.output[1].arguments = canonical_json(
            {
                "path": "public.py",
                "old_text": "a",
                "new_text": "b",
                "turn_decision": {"mode": "mutate", "basis": "Public repair"},
            }
        )

    fake = FakeClient(edit_response=alter)
    result = sampler.collect(plan, approval, adapter_factory=fake.factory)
    assert result["sample_count"] == 6 and not (approval.result_root / "public.py").exists()


def test_deadline_lowers_timeouts_and_stops_next_count(prepared):
    plan, approval = prepared
    timer = [0.0]
    fake = FakeClient(clock=timer)

    def checkpoint(stage):
        if stage == "sample_recorded":
            timer[0] = 1800.0

    result = sampler.collect(
        plan, approval, adapter_factory=fake.factory, clock=lambda: timer[0], checkpoint=checkpoint
    )
    assert result["terminal"] == "LIMIT_REACHED"
    assert len(fake.created) == len(fake.counted) == 1
    assert 0 < fake.created[0]["timeout"] <= 1800


class ProcessKilled(BaseException):
    pass


@pytest.mark.parametrize(
    "stage,expected",
    [
        ("dispatch_recorded", "PROVIDER_TIMEOUT_OR_UNKNOWN"),
        ("provider_returned", "PROVIDER_TIMEOUT_OR_UNKNOWN"),
        ("usage_recorded", "INTERRUPTED"),
        ("sample_recorded", "INTERRUPTED"),
    ],
)
def test_crash_receipt_is_read_only_and_same_root_cannot_retry(prepared, stage, expected):
    plan, approval = prepared
    fake = FakeClient()

    def kill(current):
        if current == stage:
            raise ProcessKilled()

    with pytest.raises(ProcessKilled):
        sampler.collect(plan, approval, adapter_factory=fake.factory, checkpoint=kill)
    before = {p: p.read_bytes() for p in approval.result_root.rglob("*") if p.is_file()}
    receipt = sampler.inspect_result(approval.result_root)
    assert receipt["terminal"] == expected and receipt["resume_allowed"] is False
    with pytest.raises(ContractError, match="already exists"):
        sampler.collect(plan, approval, adapter_factory=fake.factory)
    assert all(p.read_bytes() == value for p, value in before.items())
    assert len(fake.counted) == 1 and len(fake.created) <= 1


def test_corrupt_continuation_stops_after_durable_usage(prepared):
    plan, approval = prepared
    fake = FakeClient()

    def corrupt(stage):
        if stage == "continuation_stored":
            for path in (approval.result_root / "objects").rglob("*"):
                if path.is_file() and b"new_cipher_" in path.read_bytes():
                    path.write_bytes(b"corrupt")

    result = sampler.collect(plan, approval, adapter_factory=fake.factory, checkpoint=corrupt)
    assert result["terminal"] == "PROVIDER_CONTINUATION_ERROR"
    assert result["recorded_cost_nanos"] > 0 and len(fake.created) == 1
    assert any(e["event_type"] == "provider_call_finished" for e in events(approval))


def test_validation_entrypoint_has_no_dispatch_or_credential_path(prepared, capsys):
    plan, _ = prepared
    assert (
        sampler.main(
            [
                "validate",
                "--packet",
                str(plan.packet_path),
                "--packet-hash",
                plan.packet_hash,
                "--source-state-root",
                str(plan.source_root),
            ]
        )
        == 0
    )
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "VALIDATED_NOT_EXECUTED"
    assert result["provider_calls"] == result["input_count_calls"] == 0


def test_parallel_function_ids_and_continuation_order_are_preserved(prepared):
    plan, approval = prepared

    def parallel(response):
        second = copy.deepcopy(response.output[1])
        second.call_id += "_second"
        response.output.append(second)

    fake = FakeClient(edit_response=parallel)
    result = sampler.collect(plan, approval, adapter_factory=fake.factory)
    assert result["sample_count"] == 6
    for row in events(approval):
        if row["event_type"] == "sample_recorded":
            record = row["payload"]
            public = artifact_json(record["public_artifact"])
            continuation = artifact_json(record["continuation_ref"]["artifact"])
            ids = [c["action_id"] for c in public["tool_calls"]]
            assert len(ids) == 2 and ids[1] == ids[0] + "_second"
            assert ids == [
                i["action_id"]
                for i in continuation["output_order"]
                if i["type"] == "function_call_ref"
            ]


def test_continuation_action_mismatch_stops_before_next_count(prepared):
    plan, approval = prepared
    fake = FakeClient()

    def factory(config):
        adapter = fake.factory(config)
        execute = adapter.execute_request

        def mismatched(*args, **kwargs):
            turn = execute(*args, **kwargs)
            return replace(
                turn,
                provider_continuation=(
                    turn.provider_continuation[0],
                    FunctionCallContinuationRef("wrong_call"),
                ),
            )

        adapter.execute_request = mismatched
        return adapter

    result = sampler.collect(plan, approval, adapter_factory=factory)
    assert result["terminal"] == "PROVIDER_CONTINUATION_ERROR"
    assert len(fake.created) == len(fake.counted) == 1


def test_invalid_tool_batch_is_outcome_not_correction(prepared):
    plan, approval = prepared
    fake = FakeClient(edit_response=lambda r: setattr(r.output[1], "name", "unavailable_tool"))
    result = sampler.collect(plan, approval, adapter_factory=fake.factory)
    assert result["sample_count"] == len(fake.created) == 6
    assert not any(
        e["event_type"] in {"protocol_correction", "action_started"} for e in events(approval)
    )
    for row in events(approval):
        if row["event_type"] == "sample_recorded":
            assert artifact_json(row["payload"]["public_artifact"])["batch_shape"] is None


def test_unknown_durable_usage_crash_inspects_as_unknown(prepared):
    plan, approval = prepared
    fake = FakeClient(edit_response=lambda r: setattr(r, "usage", None))

    def kill(stage):
        if stage == "usage_recorded":
            raise ProcessKilled()

    with pytest.raises(ProcessKilled):
        sampler.collect(plan, approval, adapter_factory=fake.factory, checkpoint=kill)
    receipt = sampler.inspect_result(approval.result_root)
    assert receipt["terminal"] == "PROVIDER_TIMEOUT_OR_UNKNOWN"
    assert receipt["total_cost_known"] is False
    assert receipt["sample_count"] == 0


def test_terminal_projection_failure_does_not_duplicate_terminal(prepared, monkeypatch):
    plan, approval = prepared
    fake = FakeClient()
    write = ArtifactStore.write_text_immutable

    def fail_projection(store, path, content):
        if Path(path).name == "result.json":
            raise OSError("simulated result projection failure")
        return write(store, path, content)

    monkeypatch.setattr(ArtifactStore, "write_text_immutable", fail_projection)
    result = sampler.collect(plan, approval, adapter_factory=fake.factory)
    assert result["terminal"] == "SAMPLES_COLLECTED"
    assert sampler.inspect_result(approval.result_root) == result
    assert len([e for e in events(approval) if e["event_type"] == "terminal"]) == 1


def test_existing_output_claim_rejects_concurrent_collect(prepared):
    plan, approval = prepared
    fake = FakeClient()
    blocked = []

    def concurrent(stage):
        if stage == "dispatch_recorded":
            with pytest.raises(ContractError, match="already exists"):
                sampler.collect(plan, approval, adapter_factory=fake.factory)
            blocked.append(True)

    result = sampler.collect(plan, approval, adapter_factory=fake.factory, checkpoint=concurrent)
    assert result["sample_count"] == 6 and len(blocked) == 6
    assert len(fake.counted) == len(fake.created) == 6


def test_second_request_timeout_uses_shared_remaining_time(prepared):
    plan, approval = prepared
    timer = [0.0]
    fake = FakeClient(clock=timer)
    result = sampler.collect(plan, approval, adapter_factory=fake.factory, clock=lambda: timer[0])
    assert result["terminal"] == "SAMPLES_COLLECTED"
    assert [r["timeout"] for r in fake.created] == [1800, 1790, 1780, 1770, 1760, 1750]


def test_source_artifact_tampering_fails_before_client(prepared):
    plan, approval = prepared
    path = Path(plan.packet["cases"][0]["input_artifact"]["path"])
    path.write_bytes(path.read_bytes() + b" ")
    fake = FakeClient()
    with pytest.raises(ContractError):
        sampler.collect(plan, approval, adapter_factory=fake.factory)
    assert fake.counted == fake.created == []
    assert not approval.result_root.exists()


def test_outputs_must_be_outside_protected_roots(prepared):
    plan, approval = prepared
    fake = FakeClient()
    for root in (
        plan.source_root / "new-results",
        plan.packet_path.parent / "new-results",
        sampler.repository_root() / "new-sampler-results",
    ):
        with pytest.raises(ContractError, match="outside"):
            sampler.collect(plan, replace(approval, result_root=root), adapter_factory=fake.factory)
        assert not root.exists()
    assert fake.created == fake.counted == []


def test_schema_property_order_survives_count_dispatch_and_durable_capture(prepared):
    plan, approval = prepared
    original = dev_tool_schemas(**plan.packet["cases"][0]["tool_schema_inputs"])
    # Content hashes alone cannot detect this model-visible property order change.
    sorted_tools = json.loads(canonical_json(original))
    assert sha256_json(original) == sha256_json(sorted_tools)
    assert json.dumps(original) != json.dumps(sorted_tools)
    fake = FakeClient()
    result = sampler.collect(plan, approval, adapter_factory=fake.factory)
    assert result["sample_count"] == 6
    for counted, request in zip(fake.counted, fake.created, strict=True):
        assert json.dumps(request["tools"]) == json.dumps(original)
        assert json.dumps(counted["tools"]) == json.dumps(original)
    for row in events(approval):
        if row["event_type"] == "input_count_started":
            payload = row["payload"]
            stored = Path(payload["request_artifact"]["path"]).read_bytes()
            assert sha256_bytes(stored) == payload["ordered_request_hash"]
            assert json.dumps(json.loads(stored)["tools"]) == json.dumps(original)
