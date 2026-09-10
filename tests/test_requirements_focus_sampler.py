from __future__ import annotations

import copy
import json
import socket
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from test_decision_sampler import FakeClient, ProcessKilled, events

from diagnostics import decision_sampler as shared
from diagnostics import requirements_focus_sampler as sampler
from patchloop.artifacts import ArtifactStore
from patchloop.dev.conversation import assemble_model_input, history_metadata, reconstruct_state
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import dev_tool_schemas
from patchloop.errors import ContractError, RecoveryError
from patchloop.util import canonical_json, sha256_bytes, sha256_json


@pytest.fixture
def prepared_focus(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("network, credential or task execution reached")

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(shared, "load_exact_openai_api_key", forbidden)
    monkeypatch.setattr(shared, "create_openai_client", forbidden)
    monkeypatch.setattr("patchloop.dev.tools.DevToolGateway.execute", forbidden)
    source = tmp_path / "source"
    journal = DevJournal(source, "run_dev_focus_fixture")
    store = ArtifactStore(source / "artifacts")
    task = {
        "task_id": "synthetic-public",
        "task_version": 2,
        "issue": {"title": "PUBLIC_TITLE", "description": "PUBLIC_REQUIRED_BEHAVIOR"},
        "visible_checks": [{"id": "visible", "command": ["python", "-c", "PUBLIC_CHECK"]}],
    }
    names = ["search_files", "read_file", "replace_text", "run_check", "run_probe", "stop_task"]
    state = {
        "public_task": task,
        "workflow_gate": "needs_mutation",
        "current_diff": {"patch": "", "patch_hash": sha256_bytes(b"")},
        "last_successful_mutation": None,
        "available_tool_names": names,
        "remaining_budget": {"model_calls": 27, "tool_actions": 87, "accepted_mutations": 4},
        "visible_check_status": [{"check_id": "visible", "status": "NOT_RUN"}],
        "working_notes": {"findings": ["PUBLIC_MODEL_NOTE"], "open_question": "PUBLIC_Q"},
        "current_sources": [{"path": "public.py", "content_delivery": "PUBLIC_SOURCE_REF"}],
    }
    envelope = {
        "runtime_hash": "historical-runtime",
        "model": shared.MODEL,
        "reasoning_effort": "medium",
        "public_spec_hash": sha256_json(task),
        "task_id": task["task_id"],
        "task_version": 2,
        "task_content_hash": sha256_json("opaque-task-identity"),
    }
    journal.envelope_path.write_text(canonical_json(envelope), encoding="utf-8")
    items = assemble_model_input(system_prompt="PUBLIC_SYSTEM", state=state, history=[])
    journal.append("turn_started", {"turn_id": "first"})
    observed = {
        "action_id": "old_read",
        "tool": "read_file",
        "status": "succeeded",
        "output": {"spans": [], "body": "PUBLIC_OBSERVED_SOURCE"},
    }
    journal.append("action_finished", {"result": observed})
    history = [
        {"type": "reasoning", "id": "r1", "encrypted_content": "OLD_OPAQUE", "summary": []},
        {"type": "function_call", "call_id": "old_read", "name": "read_file", "arguments": "{}"},
        {"type": "function_call_output", "call_id": "old_read", "output": canonical_json(observed)},
    ]
    state["latest_tool_results"] = ["old_read"]
    items = assemble_model_input(
        system_prompt="unused", state=state, history=history, previous_input=items
    )
    turn = {
        "turn_id": "selected",
        "native_history": history_metadata(items),
        "model_input_artifact": store.put_json(items).model_dump(mode="json"),
        "context_artifact": store.put_json(state).model_dump(mode="json"),
        "max_parallel_reads": 4,
        "targeted_read_paths": [],
        "available_tool_names": names,
        "transcript_action_ids": ["old_read"],
    }
    journal.append("turn_started", turn)
    control = {
        **shared.SETTINGS,
        "input": items,
        "reasoning": {"effort": "medium"},
        "tools": dev_tool_schemas(finish_enabled=False, check_ids=["visible"], allowed_tools=names),
    }
    journal.append(
        "provider_call_started",
        {"turn_id": "selected", "input_tokens": 100, "request_hash": sha256_json(control)},
    )
    journal.append(
        "turn_decision_recorded", {"turn_id": "selected", "future": "FUTURE_ACTION_NOT_MODEL_INPUT"}
    )
    (source / "private.yaml").write_text("PRIVATE_SPEC_SENTINEL REFERENCE_PATCH_SENTINEL")
    (source / ".env").write_text("CREDENTIAL_SENTINEL")
    monkeypatch.setattr(sampler, "SOURCE_ID", journal.run_id)
    monkeypatch.setattr(sampler, "TURN_NUMBER", 2)
    monkeypatch.setattr(
        sampler,
        "SOURCE_HASHES",
        {
            ".jsonl": sha256_bytes(journal.path.read_bytes()),
            ".envelope.json": sha256_bytes(journal.envelope_path.read_bytes()),
        },
    )
    packet_root = tmp_path / "packet"
    sampler.prepare(source, packet_root)
    packet = packet_root / "packet.json"
    plan = sampler.load_plan(packet, source, sha256_bytes(packet.read_bytes()))
    approval = shared.Approval(
        plan.packet_hash,
        sampler.sampler_hash(),
        tmp_path / "result",
        tmp_path / "ABSENT.env",
        Decimal("1.20"),
        sha256_json(shared.price_identity()),
        datetime.now(UTC).date().isoformat(),
    )
    return plan, approval


def snapshot(*roots):
    return {p: p.read_bytes() for root in roots for p in root.rglob("*") if p.is_file()}


def test_only_latest_state_repeats_all_verbatim_requirements(prepared_focus):
    plan, _ = prepared_focus
    a, b = [json.loads(c.request_json) for c in plan.cells[:2]]
    original = copy.deepcopy(a)
    assert a["input"][:-1] == b["input"][:-1]
    assert {k: v for k, v in a.items() if k != "input"} == {
        k: v for k, v in b.items() if k != "input"
    }
    sa, sb = [reconstruct_state(r["input"]) for r in (a, b)]
    card = sb.pop(sampler.FIELD)
    assert sa == sb and a == original
    assert card["issue"] == sa["public_task"]["issue"]
    assert card["visible_checks"] == sa["public_task"]["visible_checks"]
    assert sampler.FIELD not in sa["working_notes"]
    assert plan.packet["source_runtime_hash"] != plan.packet["runtime_hash"]
    assert plan.packet["historical_control_input_count"] == 100
    assert plan.packet["alternate_input_count"] is None
    assert plan.packet["maximum_tool_executions"] == 0
    for text in (c.request_json for c in plan.cells):
        for secret in (
            "FUTURE_ACTION_NOT_MODEL_INPUT",
            "PRIVATE_SPEC_SENTINEL",
            "REFERENCE_PATCH_SENTINEL",
            "CREDENTIAL_SENTINEL",
        ):
            assert secret not in text


def test_four_independent_mock_samples_no_tools_no_notes_forced(prepared_focus):
    plan, approval = prepared_focus
    before = snapshot(plan.source_root, plan.packet_path.parent)
    fake = FakeClient()
    result = sampler.collect(plan, approval, adapter_factory=fake.factory)
    assert result["terminal"] == "SAMPLES_COLLECTED" and result["provider_free"]
    assert result["provider_calls"] == result["input_count_calls"] == result["sample_count"] == 4
    assert result["tool_executions"] == 0
    assert result["task_acceptance"] == result["safety_state"] == "NOT_RUN"
    for cell, counted, sent in zip(plan.cells, fake.counted, fake.created, strict=True):
        assert sent["input"] == counted["input"] == json.loads(cell.request_json)["input"]
        assert sent["tools"] == counted["tools"]
        assert sent["reasoning"] == {"effort": "medium"} and sent["max_output_tokens"] == 25000
        assert "new_cipher_" not in canonical_json(sent)
    assert shared.inspect_result(approval.result_root) == result
    assert before == snapshot(plan.source_root, plan.packet_path.parent)
    for data in snapshot(approval.result_root).values():
        assert b"PLAINTEXT_REASONING_SENTINEL" not in data
        assert b"SECRET_EXCEPTION_SENTINEL" not in data
    recorded = [e["payload"] for e in events(approval) if e["event_type"] == "sample_recorded"]
    assert [(p["arm"], p["sample_number"]) for p in recorded] == list(
        sampler.PROTOCOL.sampling_order
    )


@pytest.mark.parametrize("target", ["source", "request", "rubric", "packet", "runtime", "sampler"])
def test_changed_identity_rejected_before_provider_or_result_root(
    prepared_focus, monkeypatch, target
):
    plan, approval = prepared_focus
    if target == "runtime":
        monkeypatch.setattr(shared, "runtime_content_hash", lambda: "changed")
    elif target == "sampler":
        monkeypatch.setattr(sampler, "sampler_hash", lambda: "changed")
    else:
        path = {
            "source": plan.source_root / "runs" / (sampler.SOURCE_ID + ".jsonl"),
            "request": plan.packet_path.parent / "rubric.json",
            "rubric": plan.packet_path.parent / "rubric.json",
            "packet": plan.packet_path,
        }[target]
        if target == "request":
            from pathlib import Path

            path = Path(plan.packet["request_artifacts"]["B"]["path"])
        path.write_bytes(path.read_bytes() + b" ")
    fake = FakeClient()
    with pytest.raises((ContractError, RecoveryError)):
        sampler.collect(plan, approval, adapter_factory=fake.factory)
    assert fake.counted == fake.created == [] and not approval.result_root.exists()


@pytest.mark.parametrize(
    "fault",
    [
        "already_present",
        "nonempty_diff",
        "post_mutation",
        "plain",
        "cipher_missing",
        "oversize",
        "no_latest",
    ],
)
def test_transform_failure_is_nonmutating(prepared_focus, fault):
    plan, _ = prepared_focus
    items = json.loads(plan.cells[0].request_json)["input"]
    record = json.loads(items[-1]["content"])
    if fault == "already_present":
        record["state"][sampler.FIELD] = {}
    elif fault == "nonempty_diff":
        record["state"]["current_diff"]["patch"] = "PATCH"
    elif fault == "post_mutation":
        record["state"]["last_successful_mutation"] = {"changed": True}
    elif fault == "plain":
        items[3]["text"] = "PLAINTEXT_REASONING_SENTINEL"
    elif fault == "cipher_missing":
        items[3]["encrypted_content"] = ""
    elif fault == "oversize":
        initial = json.loads(items[1]["content"])
        initial["public_task"]["issue"]["description"] = "long" * 16000
        items[1]["content"] = canonical_json(initial)
    items[-1]["content"] = sampler.wire(record).decode()
    if fault == "no_latest":
        items.pop()
    before = copy.deepcopy(items)
    with pytest.raises((ContractError, RecoveryError)):
        sampler.focus_requirements(items)
    assert items == before


@pytest.mark.parametrize(
    "failure,expected,counts,creates",
    [
        ("count_error", "COUNT_TIMEOUT_OR_UNKNOWN", 1, 0),
        ("create_error", "PROVIDER_TIMEOUT_OR_UNKNOWN", 1, 1),
        ("oversize", "INPUT_LIMIT_EXCEEDED", 1, 0),
    ],
)
def test_collection_uncertainty_stops_all_samples(
    prepared_focus, failure, expected, counts, creates
):
    plan, approval = prepared_focus
    fake = (
        FakeClient(count_value=272001) if failure == "oversize" else FakeClient(**{failure: True})
    )
    result = sampler.collect(plan, approval, adapter_factory=fake.factory)
    assert result["terminal"] == expected
    assert len(fake.counted) == counts and len(fake.created) == creates
    with pytest.raises(ContractError, match="exists"):
        sampler.collect(plan, approval, adapter_factory=fake.factory)


def test_killed_generation_is_read_only_unknown_never_resume(prepared_focus):
    plan, approval = prepared_focus
    fake = FakeClient()

    def killed(where):
        if where == "dispatch_recorded":
            raise ProcessKilled()

    with pytest.raises(ProcessKilled):
        sampler.collect(plan, approval, adapter_factory=fake.factory, checkpoint=killed)
    before = snapshot(approval.result_root)
    assert shared.inspect_result(approval.result_root)["terminal"] == "PROVIDER_TIMEOUT_OR_UNKNOWN"
    assert before == snapshot(approval.result_root)
    with pytest.raises(ContractError, match="exists"):
        sampler.collect(plan, approval, adapter_factory=fake.factory)


def test_prepare_validate_idempotence_and_wrong_grant(prepared_focus):
    plan, approval = prepared_focus
    before = snapshot(plan.source_root, plan.packet_path.parent)
    assert sampler.load_plan(plan.packet_path, plan.source_root, plan.packet_hash) == plan
    assert sampler.load_plan(plan.packet_path, plan.source_root, plan.packet_hash) == plan
    assert before == snapshot(plan.source_root, plan.packet_path.parent)
    with pytest.raises(ContractError):
        sampler.prepare(plan.source_root, plan.packet_path.parent)
    with pytest.raises(ContractError, match="cap"):
        sampler.collect(
            plan, replace(approval, max_cost_usd=Decimal("2")), adapter_factory=FakeClient().factory
        )
