from __future__ import annotations

import copy
import json
from dataclasses import replace
from pathlib import Path

import pytest

from diagnostics import decision_sampler as sampler
from diagnostics import fresh_state_design as design
from patchloop.artifacts import ArtifactStore
from patchloop.dev.conversation import CONVERSATION_INSTRUCTIONS, STATE_KIND, TASK_MESSAGE
from patchloop.errors import ContractError, RecoveryError
from patchloop.util import sha256_bytes, sha256_json, sha256_text


def span(content: str, start: int, *, file_hash: str = "current") -> dict:
    return {
        "path": "a.py",
        "file_hash": file_hash,
        "start_line": start,
        "end_line": start + content.count("\n"),
        "content": content,
    }


def call(action_id: str, name: str, arguments: dict) -> dict:
    return {
        "type": "function_call",
        "call_id": action_id,
        "name": name,
        "arguments": design.wire_json(arguments),
    }


def output(action_id: str, name: str, body: dict) -> dict:
    return {
        "type": "function_call_output",
        "call_id": action_id,
        "output": design.wire_json(
            {
                "action_id": action_id,
                "tool": name,
                "status": "succeeded",
                "output": body,
            }
        ),
    }


@pytest.fixture
def control() -> dict:
    initial = {
        "public_task": {"title": "PUBLIC_REQUIREMENT", "constraints": {"max_diff_lines": 50}},
        "old_note": "SUPERSEDED_STATE_SENTINEL",
    }
    state = {
        "current_diff": {"patch_hash": "diff_current", "patch": "PUBLIC_CURRENT_PATCH"},
        "current_public_failure": {"message": "PUBLIC_CHECK_FAILURE", "diff_hash": "diff_current"},
        "remaining_budget": {"accepted_mutations": 1, "model_calls": 9, "tool_actions": 68},
        "mutation_scope_budget": {"current_diff_lines": 49, "max_diff_lines": 50},
        "working_notes": {"findings": [], "open_question": None},
        "current_sources": [
            {
                "path": "a.py",
                "file_hash": "current",
                "edit_permission": "allowed",
                "content_delivery": {
                    "edit1": {
                        "output.mutation_evidence": [[11, 11]],
                        "output.revalidated_spans[0]": [[10, 10]],
                        "output.revalidated_spans[1]": [[20, 21]],
                    }
                },
            }
        ],
    }
    alias = {
        "path": "a.py",
        "file_hash": "current",
        "start_line": 10,
        "end_line": 10,
        "origin": "revalidated_after_mutation",
        "content_hash": sha256_text("alpha"),
        "content_delivery": [
            {
                "action_id": "read1",
                "field": "output.spans[0]",
                "file_hash": "before",
                "start_line": 10,
                "end_line": 10,
                "target_start_line": 10,
            }
        ],
    }
    items = [
        {"role": "system", "content": "UNCHANGED_CODING_POLICY\n" + CONVERSATION_INSTRUCTIONS},
        {"role": "developer", "content": design.wire_json(initial)},
        copy.deepcopy(TASK_MESSAGE),
        {
            "type": "reasoning",
            "id": "rs1",
            "encrypted_content": "OPAQUE_CIPHER_SENTINEL",
            "summary": [],
        },
        call("read1", "read_file", {"path": "a.py", "start_line": 10, "end_line": 11}),
        output("read1", "read_file", {"spans": [span("alpha\nbeta", 10, file_hash="before")]}),
        call(
            "edit1",
            "replace_text",
            {
                "path": "a.py",
                "old_text": "beta",
                "new_text": "BETA",
                "hypothesis": "PUBLIC_UNVERIFIED_HYPOTHESIS",
            },
        ),
        output(
            "edit1",
            "replace_text",
            {"mutation_evidence": span("BETA", 11), "revalidated_spans": [alias, span("\n", 20)]},
        ),
        {"role": "developer", "content": design.wire_json({"kind": STATE_KIND, "state": state})},
    ]
    return {
        **sampler.SETTINGS,
        "input": items,
        "tools": [
            {
                "name": "replace_text",
                "parameters": {"properties": {"z_first": {}, "a_second": {}}},
            }
        ],
        "reasoning": {"effort": "medium"},
    }


def plan_for(control: dict, root: Path) -> sampler.FrozenPlan:
    cell = sampler.Cell(
        "C3", "A", design.wire_json(control), sha256_json(control), 153464, "turn_synthetic", 4, ()
    )
    packet = {
        "source_run_id": "run_dev_test",
        "source_journal_hash": "journal",
        "runtime_hash": "runtime",
        "task_id": "synthetic",
        "task_version": "v2",
        "task_content_hash": "task",
    }
    return sampler.FrozenPlan(
        root / "source.json", "source", packet, (cell,), root / "source-state", {"packet": "source"}
    )


def prepare_fixture(control: dict, root: Path) -> tuple[sampler.FrozenPlan, Path]:
    plan = plan_for(control, root)
    target = root / "design"
    target.mkdir()
    (target / "protocol.md").write_text("REVIEW_ONLY_SENTINEL", encoding="utf-8")
    (target / "rubric.json").write_text('{"model_visible":false}', encoding="utf-8")
    design.prepare(plan, target)
    return plan, target


def tree_hashes(root: Path) -> dict:
    return {
        str(p.relative_to(root)): sha256_bytes(p.read_bytes())
        for p in root.rglob("*")
        if p.is_file()
    }


def test_fresh_payload_preserves_every_current_field_and_public_action(control: dict) -> None:
    before = design.wire_json(control)
    fresh = design.fresh_request(control)
    payload = json.loads(fresh["input"][1]["content"])
    assert {k: v for k, v in payload.items() if k not in design.EXTRA_FIELDS} == (
        design.reconstruct_state(control["input"])
    )
    assert payload["public_evidence_archive"] == [
        i
        for i in control["input"]
        if i.get("type")
        in {
            "function_call",
            "function_call_output",
        }
    ]
    assert all("type" not in item for item in fresh["input"])
    assert fresh["input"][2] == control["input"][2]
    assert design.wire_json(fresh["tools"]) == design.wire_json(control["tools"])
    assert {k: v for k, v in fresh.items() if k != "input"} == {
        k: v for k, v in control.items() if k != "input"
    }
    assert before == design.wire_json(control)
    encoded = design.wire_json(fresh)
    assert "OPAQUE_CIPHER_SENTINEL" not in encoded
    assert "SUPERSEDED_STATE_SENTINEL" not in encoded
    assert "PUBLIC_UNVERIFIED_HYPOTHESIS" in encoded
    assert "PUBLIC_REQUIREMENT" in encoded


def test_materialization_resolves_alias_and_preserves_gaps_and_blank_lines(control: dict) -> None:
    fresh = design.fresh_request(control)
    sources = json.loads(fresh["input"][1]["content"])["source_bodies"]
    assert len(sources) == 1 and sources[0]["file_hash"] == "current"
    assert sources[0]["spans"] == [
        {
            "start_line": 10,
            "end_line": 11,
            "content": "alpha\nBETA",
            "content_hash": sha256_text("alpha\nBETA"),
        },
        {"start_line": 20, "end_line": 21, "content": "\n", "content_hash": sha256_text("\n")},
    ]


def test_parallel_call_order_preserved_inside_data_archive(control: dict) -> None:
    items = control["input"]
    second_call = copy.deepcopy(items[4])
    second_call["call_id"] = "read2"
    second_output = copy.deepcopy(items[5])
    second_output["call_id"] = "read2"
    body = json.loads(second_output["output"])
    body["action_id"] = "read2"
    second_output["output"] = design.wire_json(body)
    items[4:6] = [items[4], second_call, items[5], second_output]
    archive = json.loads(design.fresh_request(control)["input"][1]["content"])[
        "public_evidence_archive"
    ]
    assert [i["call_id"] for i in archive] == ["read1", "read2", "read1", "read2", "edit1", "edit1"]


@pytest.mark.parametrize("change", ["range", "hash", "alias_hash", "gap", "truncated", "conflict"])
def test_invalid_current_source_rejected(control: dict, change: str) -> None:
    view = json.loads(control["input"][-1]["content"])
    group = view["state"]["current_sources"][0]
    body = json.loads(control["input"][7]["output"])
    if change == "range":
        group["content_delivery"]["edit1"]["output.mutation_evidence"] = [[11, 12]]
    elif change == "hash":
        group["file_hash"] = "other_hash"
    elif change == "alias_hash":
        body["output"]["revalidated_spans"][0]["content_hash"] = "wrong_hash"
    elif change == "gap":
        body["output"]["revalidated_spans"][0]["end_line"] = 11
    elif change == "truncated":
        body["output"]["mutation_evidence"]["end_line"] = 12
    else:
        group["inline_spans"] = [{"start_line": 11, "end_line": 11, "content": "conflicting"}]
    control["input"][-1]["content"] = design.wire_json(view)
    control["input"][7]["output"] = design.wire_json(body)
    with pytest.raises(ContractError):
        design.fresh_request(control)


@pytest.mark.parametrize(
    "field,value",
    [
        ("summary", [{"text": "PLAINTEXT_SENTINEL"}]),
        ("text", "PLAINTEXT_SENTINEL"),
        ("encrypted_content", ""),
    ],
)
def test_invalid_reasoning_fails_without_exposing_plaintext(
    control: dict, field: str, value
) -> None:
    control["input"][3][field] = value
    with pytest.raises(ContractError, match="invalid encrypted input history") as caught:
        design.fresh_request(control)
    assert "PLAINTEXT_SENTINEL" not in str(caught.value)


def test_unmatched_action_rejected(control: dict) -> None:
    control["input"][7]["call_id"] = "different_action"
    with pytest.raises(ContractError, match="public action pairing"):
        design.fresh_request(control)


def test_future_injection_breaks_original_control_identity(control: dict, tmp_path: Path) -> None:
    plan = plan_for(control, tmp_path)
    control["input"].append({"role": "developer", "content": "FUTURE_RESULT_SENTINEL"})
    altered = replace(plan.cells[0], request_json=design.wire_json(control))
    with pytest.raises(ContractError, match="control request hash"):
        design.compile_design(replace(plan, cells=(altered,)))


def test_prepare_and_validate_are_provider_free_deterministic_and_do_not_rewrite(
    control: dict,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*args, **kwargs):
        raise AssertionError("credential/provider/tool access is forbidden during preparation")

    for name in ("load_exact_openai_api_key", "create_openai_client", "validate_tool_batch"):
        monkeypatch.setattr(sampler, name, forbidden)
    for name in ("count_input_tokens_v2", "execute_request"):
        monkeypatch.setattr(sampler.OpenAIResponsesAdapter, name, forbidden)
    plan, root = prepare_fixture(control, tmp_path)
    before = tree_hashes(root)
    first = design.validate_design(plan, root / "packet.json")
    assert first == design.validate_design(plan, root / "packet.json")
    assert first["actual_provider_calls"] == first["actual_input_count_calls"] == 0
    assert before == tree_hashes(root)
    packet = json.loads((root / "packet.json").read_bytes())
    fresh = json.loads(Path(packet["request_artifacts"]["B"]["path"]).read_bytes())
    assert "REVIEW_ONLY_SENTINEL" not in design.wire_json(fresh)
    with pytest.raises(ContractError, match="already exists"):
        design.prepare(plan, root)
    assert before == tree_hashes(root)


@pytest.mark.parametrize(
    "field,value",
    [
        ("dispatch_enabled", True),
        ("actual_provider_calls", 1),
        ("proposed_total_cap_usd", "2.00"),
        ("maximum_generation_calls_proposal", 6),
        ("source_turn_number", 33),
        ("runtime_hash", "other_runtime"),
        ("reasoning_effort", "high"),
    ],
)
def test_changed_design_contract_rejected(control: dict, tmp_path: Path, field: str, value) -> None:
    plan, root = prepare_fixture(control, tmp_path)
    packet = json.loads((root / "packet.json").read_bytes())
    packet[field] = value
    (root / "packet.json").write_text(design.wire_json(packet), encoding="utf-8")
    with pytest.raises(ContractError, match="design contract mismatch"):
        design.validate_design(plan, root / "packet.json")


@pytest.mark.parametrize("change", ["drop_result", "scope", "tools_order", "future", "cipher"])
def test_rehashed_but_changed_request_rejected(control: dict, tmp_path: Path, change: str) -> None:
    plan, root = prepare_fixture(control, tmp_path)
    packet = json.loads((root / "packet.json").read_bytes())
    request = json.loads(Path(packet["request_artifacts"]["B"]["path"]).read_bytes())
    payload = json.loads(request["input"][1]["content"])
    if change == "drop_result":
        payload["public_evidence_archive"].pop()
    elif change == "scope":
        payload["mutation_scope_budget"]["max_diff_lines"] = 500
    elif change == "tools_order":
        props = request["tools"][0]["parameters"]["properties"]
        request["tools"][0]["parameters"]["properties"] = dict(reversed(list(props.items())))
    elif change == "future":
        payload["future_result"] = "FUTURE_RESULT_SENTINEL"
    else:
        request["input"].append(copy.deepcopy(control["input"][3]))
    request["input"][1]["content"] = design.wire_json(payload)
    packet["request_artifacts"]["B"] = (
        ArtifactStore(root)
        .put_text(design.wire_json(request), "application/json")
        .model_dump(mode="json")
    )
    (root / "packet.json").write_text(design.wire_json(packet), encoding="utf-8")
    with pytest.raises(ContractError, match="prepared request differs"):
        design.validate_design(plan, root / "packet.json")


def test_corrupt_artifact_and_changed_rubric_rejected(control: dict, tmp_path: Path) -> None:
    plan, root = prepare_fixture(control, tmp_path)
    (root / "rubric.json").write_text("changed", encoding="utf-8")
    with pytest.raises(ContractError, match="review file hash"):
        design.validate_design(plan, root / "packet.json")
    packet = json.loads((root / "packet.json").read_bytes())
    Path(packet["request_artifacts"]["A"]["path"]).write_bytes(b"tampered")
    with pytest.raises(RecoveryError, match="integrity"):
        design.validate_design(plan, root / "packet.json")
