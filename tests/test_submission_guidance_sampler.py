"""Same public input, latest guidance only; no provider or sampled tool execution."""

from __future__ import annotations

import copy
import json
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest
from test_decision_sampler import ProcessKilled, artifact_json, events
from test_failure_order_sampler import OrderedClient, snapshot

from diagnostics import decision_sampler as shared
from diagnostics import submission_guidance_sampler as sampler
from patchloop.agent.model import OpenAIResponsesAdapter
from patchloop.artifacts import ArtifactStore
from patchloop.dev import segments, working_plan
from patchloop.dev.conversation import assemble_model_input, history_metadata, reconstruct_state
from patchloop.dev.model import DEV_SYSTEM_PROMPT
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import dev_tool_schemas
from patchloop.errors import ContractError, RecoveryError
from patchloop.util import canonical_json, sha256_bytes, sha256_json


@pytest.fixture
def prepared_guidance(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("real credential/provider/task execution reached")

    monkeypatch.setattr(shared, "load_exact_openai_api_key", forbidden)
    monkeypatch.setattr(shared, "create_openai_client", forbidden)
    monkeypatch.setattr("patchloop.dev.tools.DevToolGateway.execute", forbidden)
    monkeypatch.setattr(sampler, "CHECKPOINTS", (("C1", "A1", 1), ("C2", "A3", 1)))
    root = tmp_path / "source"
    root.mkdir()
    public = {
        "task_id": "pyfakefs-makedirs-parent-traversal",
        "task_version": 2,
        "split": "dev-train",
        "issue": {"description": "PUBLIC_BEHAVIOR_GOAL"},
    }
    source = {
        "frozen": {
            "runtime_hash": shared.runtime_content_hash(),
            "task_id": public["task_id"],
            "task_version": 2,
            "task_content_hash": sha256_json("PRIVATE_CONTENT_HASH_ONLY"),
            "public_task": public,
        },
        "slots": [],
    }
    for label in ("A1", "A3"):
        state = {
            "public_task": public,
            "workflow_gate": "ready_to_submit",
            "current_diff": {"patch_hash": "current", "patch": "PUBLIC_CANDIDATE"},
            "visible_check_status": [
                {"check_id": "visible", "status": "PASS", "diff_hash": "current"}
            ],
            "remaining_budget": {"model_calls": 24, "accepted_mutations": 3},
            "action_horizon": {"completion_possible": True},
            "current_public_failure": None,
            "available_tool_names": [
                "finish_task",
                "read_file",
                "search_files",
                "run_probe",
                "replace_text",
                "stop_task",
            ],
            "completion_guidance": {
                "next_action": {"tool": "finish_task"},
                "message": sampler.RECOMMENDATION,
                "diff_hash": "current",
                "submission_ready": True,
            },
            "working_plan": {"plan": {"text": "PUBLIC_UNRESOLVED_PLAN", "revision": 3}},
            "working_notes": {
                "findings": ["PUBLIC_FINDING"],
                "open_question": "PUBLIC_QUESTION",
                "verification": {"unresolved_ids": ["v1"]},
            },
        }
        items = assemble_model_input(
            system_prompt=DEV_SYSTEM_PROMPT
            + "\n\n"
            + working_plan.instructions("brief-evidence-v1"),
            state=state,
            history=[],
            context_policy=segments.POLICY,
        )
        schemas = dev_tool_schemas(
            finish_enabled=True,
            check_ids=[],
            allowed_tools=state["available_tool_names"],
            read_paths=[],
            planning_policy="brief-evidence-v1",
        )
        request = OpenAIResponsesAdapter.request_payload(
            SimpleNamespace(config=shared.model_config("medium")),
            items,
            schemas,
            system_prompt=DEV_SYSTEM_PROMPT,
        )
        source_state = root / "state" / label
        journal = DevJournal(source_state, f"run_dev_guidance_{label}")
        store = ArtifactStore(source_state / "artifacts")
        turn = {
            "turn_id": f"turn_{label}",
            "max_parallel_reads": 4,
            "targeted_read_paths": [],
            "available_tool_names": state["available_tool_names"],
            "model_input_artifact": store.put_json(items).model_dump(mode="json"),
            "native_history": history_metadata(items, context_policy=segments.POLICY),
        }
        bundle = {"request": request, "turn": turn, "transition": None}
        boundary = {
            "artifact": store.put_json(bundle).model_dump(mode="json"),
            "boundary_id": turn["turn_id"],
            "request_hash": sha256_json(request),
        }
        journal.append(
            "input_count_finished",
            {"count_id": label, "input_tokens": 100, "request_hash": sha256_json(request)},
        )
        journal.append(
            "turn_started",
            {
                **turn,
                "prepared_input": boundary,
                "selected_count_id": label,
                "counted_request_hash": sha256_json(request),
            },
        )
        journal.append(
            "provider_call_started",
            {
                "turn_id": turn["turn_id"],
                "input_tokens": 100,
                "request_hash": sha256_json(request),
                "output_ceiling": 25000,
            },
        )
        journal.append(
            "turn_decision_recorded", {"turn_id": turn["turn_id"], "future": "FUTURE_NOT_INPUT"}
        )
        journal.append(
            "terminal",
            {"terminal": "EVALUATOR_FAIL", "evaluator": {"test": "PRIVATE_DETAIL_NOT_INPUT"}},
        )
        source["slots"].append(
            {
                "label": label,
                "request": {
                    "state_root": str(source_state),
                    "model": shared.MODEL,
                    "reasoning_effort": "medium",
                    "planning_policy": "brief-evidence-v1",
                    "context_policy": segments.POLICY,
                    "probe_policy": "none",
                    "enable_probes": True,
                },
            }
        )
    (root / "packet.json").write_text(canonical_json(source), encoding="utf-8")
    monkeypatch.setattr(sampler, "SOURCE_PACKET_HASH", sha256_json(source))
    packet_root = tmp_path / "design"
    receipt = sampler.prepare(root, packet_root)
    plan = sampler.load_plan(packet_root / "packet.json", root, receipt["packet_hash"])
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


def test_exact_two_field_contrast_with_unchanged_public_memory_and_order(prepared_guidance):
    plan, approval = prepared_guidance
    before = snapshot(plan.source_root, plan.packet_path.parent)
    requests = {(c.case_id, c.arm): json.loads(c.request_json) for c in plan.cells}
    assert len(plan.cells) == 8 and len(requests) == 4
    for case in ("C1", "C2"):
        a, b = requests[case, "A"], requests[case, "B"]
        changed, _ = sampler.facts_only(a)
        assert changed == b and a["input"][:-1] == b["input"][:-1]
        assert sampler.wire(a["tools"]) == sampler.wire(b["tools"])
        sa, sb = [reconstruct_state(r["input"], context_policy=segments.POLICY) for r in (a, b)]
        assert sb["completion_guidance"]["next_action"] is None
        assert sb["completion_guidance"]["message"] == sampler.FACTS
        sb["completion_guidance"] = sa["completion_guidance"]
        assert sa == sb
        assert a["input"][0]["content"].startswith(DEV_SYSTEM_PROMPT)
    for cell in plan.cells:
        assert all(
            s not in cell.request_json
            for s in ("FUTURE_NOT_INPUT", "PRIVATE_DETAIL_NOT_INPUT", "PRIVATE_CONTENT_HASH_ONLY")
        )
        assert (
            "PUBLIC_UNRESOLVED_PLAN" in cell.request_json
            and "PUBLIC_BEHAVIOR_GOAL" in cell.request_json
        )
    fake = OrderedClient()
    result = sampler.collect(plan, approval, adapter_factory=fake.factory)
    assert result["terminal"] == "SAMPLES_COLLECTED"
    assert result["sample_count"] == result["provider_calls"] == result["input_count_calls"] == 8
    assert result["tool_executions"] == 0
    assert result["task_acceptance"] == result["safety_state"] == "NOT_RUN"
    assert fake.sequence == ["count", "create"] * 8
    for cell, sent in zip(plan.cells, fake.created, strict=True):
        request = {k: v for k, v in sent.items() if k != "timeout"}
        assert sampler.wire(request).decode() == cell.request_json
        assert sent["max_output_tokens"] == 25000 and sent["reasoning"] == {"effort": "medium"}
        assert not any(i.get("type") == "reasoning" for i in sent["input"])
    assert snapshot(plan.source_root, plan.packet_path.parent) == before
    assert shared.inspect_result(approval.result_root) == result
    for raw in snapshot(approval.result_root).values():
        assert b"PLAINTEXT_REASONING_SENTINEL" not in raw
    samples = [e["payload"] for e in events(approval) if e["event_type"] == "sample_recorded"]
    assert [(s["case_id"], s["arm"], s["sample_number"]) for s in samples] == list(sampler.SCHEDULE)
    assert all(s["continuation_ref"] for s in samples)
    assert all("arm" not in artifact_json(s["public_artifact"]) for s in samples)


@pytest.mark.parametrize("change", ["failure", "diff", "no_probe", "no_mutation", "guidance"])
def test_ineligible_views_fail_without_change(prepared_guidance, change):
    plan, _ = prepared_guidance
    request = json.loads(plan.cells[0].request_json)
    record = json.loads(request["input"][-1]["content"])
    state = record["state"]
    if change == "failure":
        state["current_public_failure"] = {"public": "CURRENT_FAILURE"}
    elif change == "diff":
        state["visible_check_status"][0]["diff_hash"] = "old"
    elif change == "no_probe":
        request["tools"] = [s for s in request["tools"] if s["name"] != "run_probe"]
    elif change == "no_mutation":
        state["remaining_budget"]["accepted_mutations"] = 0
    else:
        state["completion_guidance"]["message"] = "changed recommendation"
    request["input"][-1]["content"] = canonical_json(record)
    before = copy.deepcopy(request)
    with pytest.raises(ContractError):
        sampler.facts_only(request)
    assert request == before


@pytest.mark.parametrize("change", ["source_packet", "journal", "artifact", "runtime", "review"])
def test_drift_fails_before_new_root_or_provider(prepared_guidance, monkeypatch, change):
    plan, approval = prepared_guidance
    if change == "source_packet":
        (plan.source_root / "packet.json").write_text("{}", encoding="utf-8")
    elif change == "journal":
        journal = DevJournal(plan.source_root / "state/A1", "run_dev_guidance_A1")
        journal.append("new_event", {})
    elif change == "artifact":
        ref = plan.packet["request_artifacts"]["C1/A"]
        from pathlib import Path

        Path(ref["path"]).write_text("tampered", encoding="utf-8")
    elif change == "runtime":
        monkeypatch.setattr(shared, "runtime_content_hash", lambda: "changed")
    else:
        (plan.packet_path.parent / "protocol.md").write_text("changed", encoding="utf-8")
    with pytest.raises((ContractError, RecoveryError)):
        sampler.collect(plan, approval, adapter_factory=OrderedClient().factory)
    assert not approval.result_root.exists()


def test_cap_admits_whole_pairs_and_never_reduces_output(prepared_guidance):
    plan, approval = prepared_guidance

    def maximum(response):
        response.usage.output_tokens = 25000
        response.usage.input_tokens_details.cached_tokens = 0

    fake = OrderedClient(count_value=60000, edit_response=maximum)
    result = sampler.collect(plan, approval, adapter_factory=fake.factory)
    assert result["terminal"] == "COST_CAP_REACHED"
    assert result["sample_count"] == result["input_count_calls"] == 6
    assert result["partial_block_samples"] == 0 and result["uncollected_cells"] == 2
    assert result["recorded_cost_nanos"] == 945000000
    assert all(r["max_output_tokens"] == 25000 for r in fake.created)


@pytest.mark.parametrize(
    "kind,terminal",
    [
        ("count", "COUNT_TIMEOUT_OR_UNKNOWN"),
        ("create", "PROVIDER_TIMEOUT_OR_UNKNOWN"),
        ("usage", "PROVIDER_TIMEOUT_OR_UNKNOWN"),
    ],
)
def test_uncertainty_stops_all_pairs_without_retry(prepared_guidance, kind, terminal):
    plan, approval = prepared_guidance

    def invalid(response):
        if kind == "usage":
            response.usage.input_tokens += 1

    fake = OrderedClient(
        count_error=kind == "count", create_error=kind == "create", edit_response=invalid
    )
    result = sampler.collect(plan, approval, adapter_factory=fake.factory)
    assert result["terminal"] == terminal and result["input_count_calls"] == 1
    assert result["sample_count"] == 0
    assert result["provider_calls"] == (kind != "count")
    with pytest.raises(ContractError, match="already exists"):
        sampler.collect(plan, approval, adapter_factory=fake.factory)
    for raw in snapshot(approval.result_root).values():
        assert b"SECRET_EXCEPTION_SENTINEL" not in raw


@pytest.mark.parametrize(
    "stage",
    [
        "dispatch_recorded",
        "provider_returned",
        "usage_recorded",
        "continuation_stored",
        "sample_recorded",
    ],
)
def test_crash_readonly_inspection_and_no_recollection(prepared_guidance, stage):
    plan, approval = prepared_guidance

    def kill(reached):
        if reached == stage:
            raise ProcessKilled()

    fake = OrderedClient()
    with pytest.raises(ProcessKilled):
        sampler.collect(plan, approval, adapter_factory=fake.factory, checkpoint=kill)
    before = snapshot(approval.result_root)
    receipt = shared.inspect_result(approval.result_root)
    assert receipt["resume_allowed"] is False
    assert receipt["provider_calls"] == receipt["input_count_calls"] == 1
    assert snapshot(approval.result_root) == before
    with pytest.raises(ContractError):
        sampler.collect(plan, approval, adapter_factory=fake.factory)


def test_input_bound_and_exact_cap_reject_before_generation(prepared_guidance):
    plan, approval = prepared_guidance
    fake = OrderedClient(count_value=60001)
    with pytest.raises(ContractError, match="cap mismatch"):
        sampler.collect(
            plan, replace(approval, max_cost_usd=Decimal("1.21")), adapter_factory=fake.factory
        )
    result = sampler.collect(plan, approval, adapter_factory=fake.factory)
    assert result["terminal"] == "INPUT_LIMIT_EXCEEDED"
    assert result["provider_calls"] == 0 and len(fake.counted) == 1


def test_cli_validate_is_no_call_and_preserves_boundaries(prepared_guidance, capsys):
    plan, _ = prepared_guidance
    assert (
        sampler.main(
            [
                "validate",
                "--source-root",
                str(plan.source_root),
                "--packet",
                str(plan.packet_path),
                "--packet-hash",
                plan.packet_hash,
            ]
        )
        == 0
    )
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "VALIDATED_NOT_EXECUTED" and result["tool_executions"] == 0


def test_frozen_runtime_builder_property_order_not_sorted_cas(prepared_guidance):
    plan, _ = prepared_guidance
    request = json.loads(plan.cells[0].request_json)
    mutation = next(s for s in request["tools"] if s["name"] == "replace_text")
    assert list(mutation["parameters"]["properties"])[0] == "path"
    assert sampler.wire(request) != canonical_json(request).encode()
    assert sha256_bytes(sampler.wire(request)) != sha256_json(request)
