from __future__ import annotations

import copy
import json
import shutil
import socket
import sys
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from test_decision_sampler import FakeClient, ProcessKilled, events

from diagnostics import decision_sampler as shared
from diagnostics import model_state_review as review
from diagnostics import model_state_sampler as sampler
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import RegisteredCheck
from patchloop.dev.contracts import PublicTurnDecision, RequestedTool
from patchloop.dev.conversation import assemble_model_input, history_metadata
from patchloop.dev.model import MOCK_MUTATIONS
from patchloop.dev.tools import dev_tool_schemas
from patchloop.errors import RecoveryError
from patchloop.repository import run_git
from patchloop.util import canonical_json, sha256_bytes, sha256_json


@pytest.fixture
def factorial(tmp_path, monkeypatch, gateway_factory, smoke_package):
    gateway, journal, workspace = gateway_factory()
    source = MOCK_MUTATIONS["csv-quoted-newline"]
    public = smoke_package.public.model_copy(
        update={
            "repository": smoke_package.public.repository.model_copy(
                update={
                    "base_commit": run_git(workspace, "rev-parse", "HEAD").stdout.strip(),
                }
            ),
            "visible_checks": [
                RegisteredCheck(
                    id="simple",
                    command=[
                        sys.executable,
                        "-c",
                        "from mini_data_utils.csvlite import parse_rows; "
                        "assert parse_rows('a,b\\n') == [['a','b']]",
                    ],
                    timeout_seconds=10,
                ),
                RegisteredCheck(
                    id="multiline",
                    command=[
                        sys.executable,
                        "-c",
                        "from mini_data_utils.csvlite import parse_rows; "
                        "assert parse_rows('\"a\\nb\",c\\n') == [['a\\nb','c']]",
                    ],
                    timeout_seconds=10,
                ),
            ],
        }
    )
    package = smoke_package.model_copy(
        update={"public": public, "task_content_hash": sha256_json(public.model_dump(mode="json"))}
    )
    gateway.public_task = public
    names = ["search_files", "read_file", "replace_text", "run_check", "stop_task"]
    state = {
        "public_task": public.model_dump(mode="json"),
        "workflow_gate": "needs_mutation",
        "current_diff": {"patch": "", "patch_hash": sha256_bytes(b"")},
        "available_tool_names": names,
        "current_sources": [],
        "remaining_budget": {"model_calls": 27, "tool_actions": 87, "accepted_mutations": 4},
        "visible_check_status": [
            {"check_id": c.id, "status": "NOT_RUN"} for c in public.visible_checks
        ],
        "working_notes": {"findings": [], "open_question": None},
    }
    items = assemble_model_input(system_prompt="PUBLIC_SYSTEM", state=state, history=[])
    journal.append("turn_started", {"turn_id": "first"})
    result = gateway.execute(
        RequestedTool(
            name="read_file",
            action_id="read_source",
            arguments={"path": source.path, "start_line": 1, "end_line": 80},
            turn_decision=PublicTurnDecision(
                mode="inspect", basis="Public source", evidence_goal="Observe parser"
            ),
        )
    )
    span = result.output["spans"][0]
    state["current_sources"] = [
        {
            "path": source.path,
            "file_hash": span["file_hash"],
            "edit_permission": "allowed",
            "content_delivery": {
                "read_source": {"output.spans[0]": [[span["start_line"], span["end_line"]]]}
            },
        }
    ]
    history = [
        {
            "type": "reasoning",
            "id": "old_reasoning",
            "encrypted_content": "OLD_OPAQUE",
            "summary": [],
        },
        {"type": "function_call", "call_id": "read_source", "name": "read_file", "arguments": "{}"},
        {
            "type": "function_call_output",
            "call_id": "read_source",
            "output": canonical_json(result.model_dump(mode="json")),
        },
    ]
    store = ArtifactStore(journal.root / "artifacts")
    for turn in (2, 3):
        state["remaining_budget"]["model_calls"] -= 1
        items = assemble_model_input(
            system_prompt="unused",
            state=state,
            history=history if turn == 2 else [],
            previous_input=items,
        )
        turn_id = f"selected_{turn}"
        journal.append(
            "turn_started",
            {
                "turn_id": turn_id,
                "native_history": history_metadata(items),
                "model_input_artifact": store.put_json(items).model_dump(mode="json"),
                "context_artifact": store.put_json(state).model_dump(mode="json"),
                "max_parallel_reads": 4,
                "targeted_read_paths": [],
                "available_tool_names": names,
                "transcript_action_ids": ["read_source"],
            },
        )
        request = {
            **shared.SETTINGS,
            "input": items,
            "reasoning": {"effort": "medium"},
            "tools": dev_tool_schemas(
                finish_enabled=False,
                check_ids=[c.id for c in public.visible_checks],
                allowed_tools=names,
            ),
        }
        journal.append(
            "provider_call_started",
            {"turn_id": turn_id, "input_tokens": 100, "request_hash": sha256_json(request)},
        )
    journal.append("future_result", {"sentinel": "FUTURE_RESULT_SENTINEL"})
    envelope = {
        "runtime_hash": "old-runtime",
        "model": sampler.MINI.model_id,
        "reasoning_effort": "medium",
        "public_spec_hash": sha256_json(state["public_task"]),
        "task_id": public.task_id,
        "task_version": public.task_version,
        "task_content_hash": package.task_content_hash,
    }
    journal.envelope_path.write_text(canonical_json(envelope), encoding="utf-8")
    (journal.root / ".env").write_text("SECRET_CREDENTIAL_SENTINEL")
    (journal.root / "private.yaml").write_text(
        "PRIVATE_SPEC_SENTINEL HIDDEN_PATH_SENTINEL REFERENCE_PATCH_SENTINEL"
    )
    clone = journal.root / "workspaces" / journal.run_id / "repo"
    shutil.copytree(workspace, clone)
    monkeypatch.setattr(sampler, "SOURCE_ID", journal.run_id)
    monkeypatch.setattr(
        sampler,
        "SOURCE_HASHES",
        {
            ".jsonl": sha256_bytes(journal.path.read_bytes()),
            ".envelope.json": sha256_bytes(journal.envelope_path.read_bytes()),
        },
    )
    monkeypatch.setattr(sampler, "CASE_TURNS", {"C1": 2, "C2": 3})
    monkeypatch.setattr(review, "load_task_package", lambda _: package)

    def forbidden(*args, **kwargs):
        pytest.fail("network or credential reached")

    monkeypatch.setattr(shared, "load_exact_openai_api_key", forbidden)
    monkeypatch.setattr(shared, "create_openai_client", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    packet_root = tmp_path / "packet"
    sampler.prepare(journal.root, packet_root)
    packet = packet_root / "packet.json"
    plan = sampler.load_plan(packet, journal.root, sha256_bytes(packet.read_bytes()))
    approval = shared.Approval(
        plan.packet_hash,
        sampler.sampler_hash(),
        tmp_path / "result",
        tmp_path / "ABSENT.env",
        Decimal("5.00"),
        plan.packet["pricing_hash"],
        datetime.now(UTC).date().isoformat(),
    )
    return plan, approval, package


class MultiClient(FakeClient):
    def create(self, **kwargs):
        response = super().create(**kwargs)
        response.model = kwargs["model"]
        return response


def snapshot(*roots):
    return {p: p.read_bytes() for root in roots for p in root.rglob("*") if p.is_file()}


def test_factor_isolation_complete_source_archive_and_no_future_or_secrets(factorial):
    plan, _, _ = factorial
    before = snapshot(plan.source_root, plan.packet_path.parent)
    checked = sampler.load_plan(plan.packet_path, plan.source_root, plan.packet_hash)
    assert plan.cells == checked.cells and before == snapshot(
        plan.source_root, plan.packet_path.parent
    )
    assert [(c.case_id, c.arm, c.sample_number) for c in plan.cells] == list(sampler.SCHEDULE)
    for case in sampler.CASE_TURNS:
        requests = {c.arm: json.loads(c.request_json) for c in plan.cells if c.case_id == case}
        a, b, c, d = [requests[arm] for arm in "ABCD"]
        assert a["input"] == c["input"] and b["input"] == d["input"]
        payloads = [json.loads(r["input"][1]["content"]) for r in (a, b, c, d)]
        past = [p.pop(sampler.FIELD) for p in payloads]
        assert past[0] == past[2] and past[0] and past[1] == past[3] == []
        assert payloads[0] == payloads[1] == payloads[2] == payloads[3]
        assert payloads[0]["source_bodies"][0]["spans"][0]["content"]
        archive = payloads[0]["public_evidence_archive"]
        assert [i["call_id"] for i in archive] == ["read_source", "read_source"]
        assert len(a["input"]) == 3 and len(b["input"]) == 3
        for request in requests.values():
            text = canonical_json(request)
            for forbidden in (
                "OLD_OPAQUE",
                "FUTURE_RESULT_SENTINEL",
                "PRIVATE_SPEC_SENTINEL",
                "HIDDEN_PATH_SENTINEL",
                "REFERENCE_PATCH_SENTINEL",
                "SECRET_CREDENTIAL_SENTINEL",
            ):
                assert forbidden not in text
    assert sampler.PROTOCOL.input_token_limit == 272000
    assert shared.OUTPUT_CEILING == 25000


def test_sixteen_independent_responses_two_prices_one_cap_no_plain_reasoning(factorial):
    plan, approval, _ = factorial
    before = snapshot(plan.source_root, plan.packet_path.parent)
    fake = MultiClient()
    result = sampler.collect(plan, approval, adapter_factory=fake.factory)
    assert result["terminal"] == "SAMPLES_COLLECTED", result
    assert result["provider_calls"] == result["sample_count"] == result["input_count_calls"] == 16
    assert result["completed_comparison_blocks"] == 4 and result["partial_block_samples"] == 0
    assert result["recorded_cost_nanos"] == 8 * (158250 + 527500)
    assert result["tool_executions"] == 0 and result["task_acceptance"] == "NOT_RUN"
    for cell, counted, sent in zip(plan.cells, fake.counted, fake.created, strict=True):
        assert sent["model"] == sampler.PROFILES[cell.arm].model_id == counted["model"]
        assert sent["input"] == counted["input"] == json.loads(cell.request_json)["input"]
        assert sent["max_output_tokens"] == 25000 and "new_cipher" not in canonical_json(sent)
    assert before == snapshot(plan.source_root, plan.packet_path.parent)
    assert shared.inspect_result(approval.result_root) == result
    for data in snapshot(approval.result_root).values():
        assert b"PLAINTEXT_REASONING_SENTINEL" not in data
        assert b"SECRET_EXCEPTION_SENTINEL" not in data
    recorded = [e["payload"] for e in events(approval) if e["event_type"] == "sample_recorded"]
    assert all(r["continuation_ref"] for r in recorded)


def test_block_reservation_stops_before_count_never_lowers_output(factorial):
    plan, approval, _ = factorial
    fake = MultiClient(count_value=272000)

    def full_usage(response):
        response.usage.output_tokens = 25000
        response.usage.input_tokens_details.cached_tokens = 0

    fake.edit_response = full_usage
    result = sampler.collect(plan, approval, adapter_factory=fake.factory)
    assert result["terminal"] == "COST_CAP_REACHED"
    assert result["sample_count"] == result["input_count_calls"] == 4
    assert result["recorded_cost_nanos"] == 2743000000
    assert result["completed_comparison_blocks"] == 1 and result["uncollected_cells"] == 12
    assert all(r["max_output_tokens"] == 25000 for r in fake.created)


@pytest.mark.parametrize("failure", ["count", "transport", "billing", "cipher", "input_limit"])
def test_uncertainty_stops_every_arm_without_retry(factorial, failure):
    plan, approval, _ = factorial
    fake = MultiClient()
    if failure == "count":
        fake.count_error = True
    elif failure == "transport":
        fake.create_error = True
    elif failure == "input_limit":
        fake.count_value = 272001
    else:

        def break_response(response):
            if failure == "billing":
                response.usage = None
            else:
                response.output[0].encrypted_content = None

        fake.edit_response = break_response
    result = sampler.collect(plan, approval, adapter_factory=fake.factory)
    assert result["terminal"] != "SAMPLES_COLLECTED"
    assert result["sample_count"] == 0 and result["provider_calls"] <= 1
    assert len(fake.created) <= 1 and len(fake.counted) == 1
    assert shared.inspect_result(approval.result_root) == result


@pytest.mark.parametrize("failure", ["second_transport", "wrong_larger_model"])
def test_mid_block_uncertainty_preserves_first_sample_and_stops_other_models(factorial, failure):
    plan, approval, _ = factorial
    fake = MultiClient()
    if failure == "second_transport":
        fake.edit_response = lambda _: setattr(fake, "create_error", True)
    else:
        original = fake.responses.create

        def wrong_model(**kwargs):
            response = original(**kwargs)
            if len(fake.created) == 2:
                response.model = sampler.MINI.model_id
            return response

        fake.responses.create = wrong_model
    result = sampler.collect(plan, approval, adapter_factory=fake.factory)
    assert result["terminal"] == "PROVIDER_TIMEOUT_OR_UNKNOWN"
    assert result["sample_count"] == 1 and result["partial_block_samples"] == 1
    assert result["provider_calls"] == result["input_count_calls"] == 2
    assert len(fake.created) == 2 and result["total_cost_known"] is False
    assert [r["model"] for r in fake.created] == [sampler.MINI.model_id, sampler.LARGE.model_id]
    assert shared.inspect_result(approval.result_root) == result


@pytest.mark.parametrize("point", ["dispatch_recorded", "usage_recorded", "sample_recorded"])
def test_process_death_only_inspects_never_replays(factorial, point):
    plan, approval, _ = factorial
    fake = MultiClient()

    def killed(at):
        if at == point:
            raise ProcessKilled()

    with pytest.raises(ProcessKilled):
        sampler.collect(plan, approval, adapter_factory=fake.factory, checkpoint=killed)
    before = snapshot(approval.result_root)
    status = shared.inspect_result(approval.result_root)
    assert status["resume_allowed"] is False
    assert before == snapshot(approval.result_root)
    with pytest.raises(shared.ContractError):
        sampler.collect(plan, approval, adapter_factory=fake.factory)


@pytest.mark.parametrize(
    "target", ["source", "request", "rubric", "pricing", "runtime", "approval"]
)
def test_tampering_rejected_before_credentials_or_output_directory(factorial, monkeypatch, target):
    plan, approval, _ = factorial
    if target == "source":
        path = plan.source_root / "runs" / (sampler.SOURCE_ID + ".jsonl")
        path.write_bytes(path.read_bytes() + b" ")
    elif target == "request":
        ref = plan.packet["request_artifacts"]["C1"]["A"]
        from pathlib import Path

        Path(ref["path"]).write_bytes(b"tampered")
    elif target in {"rubric", "pricing"}:
        (plan.packet_path.parent / f"{target}.json").write_text("tampered")
    elif target == "runtime":
        monkeypatch.setattr(shared, "runtime_content_hash", lambda: "changed")
    else:
        approval = replace(approval, pricing_hash=sha256_json(shared.price_identity()))
    with pytest.raises((shared.ContractError, RecoveryError)):
        sampler.collect(plan, approval, adapter_factory=MultiClient().factory)
    assert not approval.result_root.exists()


def test_invalid_current_delivery_does_not_read_files_or_invent_sources(factorial):
    plan, _, _ = factorial
    events_, envelope = sampler.source_events(plan.source_root)
    original, _, _ = sampler.cutoff_request(events_, envelope, plan.source_root, 2)
    bad = copy.deepcopy(original)
    record = json.loads(bad["input"][-1]["content"])
    record["state"]["current_sources"][0]["content_delivery"] = {"absent": {"spans": [[1, 5]]}}
    bad["input"][-1]["content"] = canonical_json(record)
    with pytest.raises(shared.ContractError):
        sampler.factorial_requests(bad)
