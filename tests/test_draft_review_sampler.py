from __future__ import annotations

import copy
import json
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from test_decision_sampler import FakeClient, ProcessKilled, events
from test_requirements_focus_sampler import prepared_focus, snapshot  # noqa: F401

from diagnostics import decision_sampler as shared
from diagnostics import draft_review_sampler as sampler
from patchloop.artifacts import ArtifactStore
from patchloop.dev.conversation import reconstruct_state
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError, RecoveryError
from patchloop.util import canonical_json, sha256_bytes, sha256_json


@pytest.fixture
def prepared_review(prepared_focus, tmp_path, monkeypatch):  # noqa: F811 - imported pytest fixture
    baseline_plan, _ = prepared_focus
    baseline = json.loads(baseline_plan.cells[0].request_json)
    draft_root = tmp_path / "draft-source"
    store = ArtifactStore(draft_root)
    journal = DevJournal(draft_root, "run_dev_draft_fixture")
    store.write_text_immutable(
        draft_root / "envelope.json",
        canonical_json(
            {
                "source_run_id": baseline_plan.packet["source_run_id"],
                "task_content_hash": baseline_plan.packet["task_content_hash"],
            }
        ),
    )
    public = {
        **shared.BOUNDARIES,
        "response_status": "completed",
        "error_code": None,
        "tool_calls": [
            {
                "name": "replace_text",
                "action_id": "unexecuted_draft_call",
                "arguments": {
                    "path": "public.py",
                    "old_text": "PUBLIC_BEFORE",
                    "new_text": "PUBLIC_AFTER",
                    "occurrence": 1,
                    "hypothesis": "PUBLIC_DRAFT_HYPOTHESIS",
                    "expected_behavior": "PUBLIC_DRAFT_EXPECTATION",
                    "causal_revision": None,
                    "turn_decision": {
                        "mode": "mutate",
                        "basis": "PUBLIC_DRAFT_BASIS",
                        "evidence_goal": None,
                        "memory_update": None,
                    },
                },
            }
        ],
        "not_projected": "PRIVATE_RUBRIC_OR_METADATA_SENTINEL",
    }
    public_ref = store.put_json(public)
    opaque = store.put_json({"encrypted_content": "DRAFT_OPAQUE_NOT_FOR_MODEL"})
    journal.append(
        "sample_recorded",
        {
            "arm": "A",
            "sample_number": 1,
            "sample_id": "first_sample",
            "source_turn_id": baseline_plan.packet["source_turn_id"],
            "request_hash": sha256_json(baseline),
            "ordered_request_hash": sha256_bytes(sampler.source.wire(baseline)),
            "public_artifact": public_ref.model_dump(mode="json"),
            "continuation_ref": opaque.model_dump(mode="json"),
        },
    )
    later = store.put_text("LATER_SAMPLE_OR_ANALYSIS_NOT_FOR_MODEL")
    journal.append("sample_recorded", {"public_artifact": later.model_dump(mode="json")})
    journal.append("terminal", {"terminal": "SAMPLES_COLLECTED"})
    monkeypatch.setattr(sampler, "DRAFT_RUN_ID", journal.run_id)
    monkeypatch.setattr(
        sampler,
        "DRAFT_HASHES",
        {
            str(path.relative_to(draft_root)).replace("\\", "/"): sha256_bytes(path.read_bytes())
            for path in (draft_root / "envelope.json", journal.path)
        },
    )
    monkeypatch.setattr(sampler, "DRAFT_PUBLIC_HASH", public_ref.content_hash)
    root = tmp_path / "review-packet"
    sampler.prepare(baseline_plan.source_root, draft_root, root)
    packet_path = root / "packet.json"
    plan = sampler.load_plan(
        packet_path, baseline_plan.source_root, draft_root, sha256_bytes(packet_path.read_bytes())
    )
    approval = shared.Approval(
        plan.packet_hash,
        sampler.sampler_hash(),
        tmp_path / "review-result",
        tmp_path / "ABSENT.env",
        Decimal("1.20"),
        sha256_json(shared.price_identity()),
        datetime.now(UTC).date().isoformat(),
    )
    return plan, approval, baseline, draft_root


def test_only_instruction_differs_on_identical_unexecuted_draft(prepared_review):
    plan, _, baseline, _ = prepared_review
    a, b = [json.loads(cell.request_json) for cell in plan.cells[:2]]
    assert a["input"][:-1] == b["input"][:-1] == baseline["input"][:-1]
    assert {k: v for k, v in a.items() if k != "input"} == {
        k: v for k, v in baseline.items() if k != "input"
    }
    sa, sb = [reconstruct_state(request["input"]) for request in (a, b)]
    ca, cb = [state.pop(sampler.FIELD) for state in (sa, sb)]
    assert ca.pop("harness_instruction") == sampler.INSTRUCTIONS["A"]
    assert cb.pop("harness_instruction") == sampler.INSTRUCTIONS["B"]
    assert ca == cb and ca["status"] == "not_applied_not_executed"
    assert ca["proposal"]["arguments"]["new_text"] == "PUBLIC_AFTER"
    assert sa == sb == reconstruct_state(baseline["input"])
    assert all(cell.historical_count is None for cell in plan.cells)
    assert plan.packet["fresh_token_counts"] == {"A": None, "B": None}
    assert plan.packet["unchanged_prefix_items"] == len(baseline["input"]) - 1
    assert plan.packet["reasoning_item_count"] == 1
    assert plan.packet["draft_source"]["draft_reasoning_included"] is False
    for cell in plan.cells:
        for sentinel in (
            "unexecuted_draft_call",
            "PRIVATE_RUBRIC_OR_METADATA_SENTINEL",
            "DRAFT_OPAQUE_NOT_FOR_MODEL",
            "LATER_SAMPLE_OR_ANALYSIS_NOT_FOR_MODEL",
            "PRIVATE_SPEC_SENTINEL",
            "REFERENCE_PATCH_SENTINEL",
            "CREDENTIAL_SENTINEL",
        ):
            assert sentinel not in cell.request_json
        assert "OLD_OPAQUE" in cell.request_json
    assert a["input"][-1] != baseline["input"][-1]


def test_four_fake_responses_keep_history_and_never_execute_drafts(prepared_review):
    plan, approval, _, draft_root = prepared_review
    before = snapshot(plan.source_root, plan.packet_path.parent, draft_root)
    fake = FakeClient()
    result = sampler.collect(plan, approval, adapter_factory=fake.factory)
    assert result["terminal"] == "SAMPLES_COLLECTED" and result["provider_free"]
    assert result["sample_count"] == result["input_count_calls"] == result["provider_calls"] == 4
    assert result["tool_executions"] == 0
    assert result["task_acceptance"] == result["safety_state"] == "NOT_RUN"
    for cell, counted, sent in zip(plan.cells, fake.counted, fake.created, strict=True):
        assert sent["input"] == counted["input"] == json.loads(cell.request_json)["input"]
        assert sent["tools"] == counted["tools"]
        assert sent["reasoning"] == {"effort": "medium"} and sent["max_output_tokens"] == 25000
        assert "new_cipher_" not in canonical_json(sent)
    assert shared.inspect_result(approval.result_root) == result
    assert before == snapshot(plan.source_root, plan.packet_path.parent, draft_root)
    for raw in snapshot(approval.result_root).values():
        assert b"PLAINTEXT_REASONING_SENTINEL" not in raw
    recorded = [e["payload"] for e in events(approval) if e["event_type"] == "sample_recorded"]
    assert [(r["arm"], r["sample_number"]) for r in recorded] == list(
        sampler.PROTOCOL.sampling_order
    )


def test_draft_reasoning_and_later_outputs_are_not_read(prepared_review, monkeypatch):
    plan, _, _, draft_root = prepared_review
    original = Path.read_bytes
    digest = sampler.DRAFT_PUBLIC_HASH.removeprefix("sha256:")
    only_public_object = draft_root / "objects/sha256" / digest[:2] / digest[2:]

    def guarded(path):
        if path.is_relative_to(draft_root / "objects") and path != only_public_object:
            pytest.fail("draft continuation or later sample content was read")
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", guarded)
    assert (
        sampler.load_plan(plan.packet_path, plan.source_root, draft_root, plan.packet_hash) == plan
    )
    for instruction in sampler.INSTRUCTIONS.values():
        for hint in ("EEXIST", "0o700", "0o755", "pyfakefs", "FakeOsModule", "mode"):
            # 'model-authored' is provenance, not a permissions hint.
            assert hint not in instruction.replace("model-authored", "")


@pytest.mark.parametrize(
    "target",
    [
        "source",
        "draft_journal",
        "draft_envelope",
        "draft_artifact",
        "request",
        "rubric",
        "packet",
        "runtime",
        "sampler",
    ],
)
def test_tamper_is_rejected_before_credentials_or_output_claim(
    prepared_review, monkeypatch, target
):
    plan, approval, _, draft_root = prepared_review
    if target == "runtime":
        monkeypatch.setattr(shared, "runtime_content_hash", lambda: "changed")
    elif target == "sampler":
        monkeypatch.setattr(sampler, "sampler_hash", lambda: "changed")
    else:
        digest = sampler.DRAFT_PUBLIC_HASH.removeprefix("sha256:")
        path = {
            "source": plan.source_root / "runs" / (plan.packet["source_run_id"] + ".jsonl"),
            "draft_journal": draft_root / "runs" / (sampler.DRAFT_RUN_ID + ".jsonl"),
            "draft_envelope": draft_root / "envelope.json",
            "draft_artifact": draft_root / "objects/sha256" / digest[:2] / digest[2:],
            "request": Path(plan.packet["request_artifacts"]["B"]["path"]),
            "rubric": plan.packet_path.parent / "rubric.json",
            "packet": plan.packet_path,
        }[target]
        path.write_bytes(path.read_bytes() + b" ")
    fake = FakeClient()
    with pytest.raises((ContractError, RecoveryError)):
        sampler.collect(plan, approval, adapter_factory=fake.factory)
    assert not approval.result_root.exists() and fake.counted == fake.created == []


@pytest.mark.parametrize("fault", ["wrong_arm", "post_edit", "duplicate_draft"])
def test_reconsider_failure_does_not_mutate_input(prepared_review, fault):
    plan, _, baseline, _ = prepared_review
    items = copy.deepcopy(baseline["input"])
    record = json.loads(items[-1]["content"])
    if fault == "post_edit":
        record["state"]["current_diff"]["patch"] = "changed"
    elif fault == "duplicate_draft":
        record["state"][sampler.FIELD] = {}
    items[-1]["content"] = sampler.source.wire(record).decode()
    before = copy.deepcopy(items)
    draft = reconstruct_state(json.loads(plan.cells[0].request_json)["input"])[sampler.FIELD][
        "proposal"
    ]
    with pytest.raises(ContractError):
        sampler.reconsider(items, draft, "unknown" if fault == "wrong_arm" else "A")
    assert items == before


def test_revalidation_is_read_only_and_grant_and_overlap_fail_before_dispatch(prepared_review):
    plan, approval, _, draft_root = prepared_review
    before = snapshot(plan.source_root, plan.packet_path.parent, draft_root)
    assert (
        sampler.load_plan(plan.packet_path, plan.source_root, draft_root, plan.packet_hash) == plan
    )
    assert (
        sampler.load_plan(plan.packet_path, plan.source_root, draft_root, plan.packet_hash) == plan
    )
    with pytest.raises(ContractError, match="fresh"):
        sampler.prepare(plan.source_root, draft_root, plan.packet_path.parent)
    for altered in (
        replace(approval, max_cost_usd=Decimal("2")),
        replace(approval, result_root=draft_root / "forbidden-result"),
    ):
        with pytest.raises(ContractError):
            sampler.collect(plan, altered, adapter_factory=FakeClient().factory)
        assert not altered.result_root.exists()
    assert before == snapshot(plan.source_root, plan.packet_path.parent, draft_root)


@pytest.mark.parametrize(
    "fault,expected",
    [
        ("count_error", "COUNT_TIMEOUT_OR_UNKNOWN"),
        ("create_error", "PROVIDER_TIMEOUT_OR_UNKNOWN"),
        ("oversize", "INPUT_LIMIT_EXCEEDED"),
    ],
)
def test_uncertainty_stops_the_whole_comparison_without_retry(prepared_review, fault, expected):
    plan, approval, _, _ = prepared_review
    fake = FakeClient(count_value=272001) if fault == "oversize" else FakeClient(**{fault: True})
    result = sampler.collect(plan, approval, adapter_factory=fake.factory)
    assert result["terminal"] == expected
    assert len(fake.counted) == 1 and len(fake.created) == int(fault == "create_error")
    with pytest.raises(ContractError, match="exists"):
        sampler.collect(plan, approval, adapter_factory=fake.factory)


def test_killed_dispatch_is_read_only_unknown_not_resume(prepared_review):
    plan, approval, _, _ = prepared_review

    def killed(where):
        if where == "dispatch_recorded":
            raise ProcessKilled()

    with pytest.raises(ProcessKilled):
        sampler.collect(plan, approval, adapter_factory=FakeClient().factory, checkpoint=killed)
    before = snapshot(approval.result_root)
    assert shared.inspect_result(approval.result_root)["terminal"] == "PROVIDER_TIMEOUT_OR_UNKNOWN"
    assert before == snapshot(approval.result_root)
    with pytest.raises(ContractError, match="exists"):
        sampler.collect(plan, approval, adapter_factory=FakeClient().factory)
