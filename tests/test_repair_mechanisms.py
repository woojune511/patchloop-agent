from __future__ import annotations

import ast
from pathlib import Path

import pytest
from repair_mechanism_expectations import ARM, EVIDENCE, JUDGMENT
from test_dev_context_v12 import observe
from test_dev_context_v12 import source_gateway as source_gateway
from test_dev_notes_v14 import note_call

from diagnostics import repair_mechanisms as ablation
from patchloop.dev import segments
from patchloop.dev.contracts import DevLimits
from patchloop.dev.model import DEV_SYSTEM_PROMPT
from patchloop.dev.model_state import compact_model_state
from patchloop.dev.thin_policy import system_prompt
from patchloop.dev.working_notes import memory_update_schema
from patchloop.runtime import repository_root


def test_active_checkout_is_exact_frozen_arm_and_factors_commute():
    root = repository_root()
    # An expected-arm environment variable cannot turn the production runtime into
    # an ablation, or hide a mislabeled full-suite run.
    expected = ablation.arm_sources(root, ARM)
    assert all((root / p).read_bytes() == text.encode() for p, text in expected.items())
    base = ablation.base_sources(root)
    assert ablation.arm_sources(root, "E1J1") == base
    e0 = ablation.arm_sources(root, "E0J1")
    j0 = ablation.arm_sources(root, "E1J0")
    assert {p for p in base if e0[p] != base[p]} == {
        "patchloop/dev/tools.py", "patchloop/dev/runner.py", "patchloop/dev/model.py"}
    assert {p for p in base if j0[p] != base[p]} == {
        "patchloop/dev/model_state.py", "patchloop/dev/working_plan.py", "patchloop/dev/model.py"}


@pytest.mark.parametrize("arm", ablation.ARMS)
def test_all_rendered_guidance_keeps_existing_size_and_common_contract(arm):
    source = ablation.arm_sources(repository_root(), arm)
    prompt = ablation.assignment(source["patchloop/dev/model.py"], "DEV_SYSTEM_PROMPT")[1]
    plan = ablation.assignment(source["patchloop/dev/working_plan.py"], "INSTRUCTIONS")[1]
    assert len(prompt) <= 8000
    assert len(prompt + "\n\n" + plan) <= 10809
    assert "at most one primary and one countercheck" in prompt
    assert "Cite minimal observed units and a competing" in prompt
    assert "do not mechanically gate actions or finish" in prompt
    assert "No additional check is mandatory" in plan
    assert "plan_update_reason (at most 800 characters)" in plan
    assert "model-authored, unverified working data" in plan
    assert ("closed_by_model" in prompt) == (arm[3] == "1")
    assert ("another path's success cannot replace that purpose" in prompt) == (arm[3] == "1")
    assert (ablation.E1_HELP in prompt) == (arm[1] == "1")
    for path, text in source.items():
        ast.parse(text, filename=path)


def test_runtime_prompt_and_limits_match_selected_contract():
    assert len(DEV_SYSTEM_PROMPT) <= 8000
    assert len(system_prompt("current", "brief-v1")) <= 10809
    assert ("closed_by_model" in DEV_SYSTEM_PROMPT) == JUDGMENT
    assert (ablation.E1_HELP in DEV_SYSTEM_PROMPT) == EVIDENCE
    limits = DevLimits()
    assert (limits.max_model_calls, limits.max_tool_actions,
            limits.max_accepted_mutations, limits.wall_time_seconds) == (40, 100, 4, 1800)
    assert (segments.MAX_INPUT_TOKENS, segments.MAX_REQUEST_BYTES,
            segments.MAX_ENCRYPTED_ITEM_BYTES) == (60000, 1048576, 262144)
    schema = memory_update_schema()["properties"]["open_question"]
    assert schema["properties"]["evidence"]["maxItems"] == 2


def test_evidence_factor_changes_gateway_selection_not_binding_or_anchors(
    source_gateway, monkeypatch,
):
    gateway, _, _ = source_gateway
    observe(gateway, "src.py", 1, 1, action_id="older")
    observe(gateway, "src.py", 4, 4, action_id="newer")
    update = {"findings": [], "open_question": {"text": "Is the older condition necessary?",
              "evidence": [{"kind": "source", "path": "src.py", "start_line": 1,
                            "end_line": 1, "role": "primary"}]}}
    gateway.record_working_notes_update([note_call("q", update)], turn_id="q")
    assert gateway.focus_source_references()
    question = gateway.working_notes()["open_question"]
    # A tiny synthetic capacity exercises exclusion; real requests remain at 24k.
    gateway.retained_source_chars = 6
    selected = gateway.prepare_context_projection()
    assert [s["content"] for s in selected.source_spans] == (["first"] if EVIDENCE else ["fourth"])
    assert gateway.context_spans() == list(selected.source_spans)
    assert gateway.working_notes()["open_question"] == question
    monkeypatch.setattr(gateway, "_source_projection_priorities", lambda: [("src.py", 4, 4, 0)])
    protected = gateway.prepare_context_projection()
    assert [s["content"] for s in protected.source_spans] == ["fourth"]
    assert protected.retained_content_chars == 6


def test_judgment_factor_preserves_data_but_changes_public_authority_labels():
    note = {"note_id": "n", "statement": "An untested hypothesis", "status": "current",
            "interpretation_status": "model_authored_unverified", "evidence": []}
    state = {"working_notes": {"findings": [note], "open_question": None,
              "verification": {"items": [{"status": "resolved", "statement": "Original purpose",
                "model_authored": True, "interpretation_status": "model_authored_unverified"}]}},
             "working_plan": {"plan": {"text": "Remaining work"}},
             "current_diff": {"patch_hash": "D", "patch": "UNCHANGED"}}
    view = compact_model_state(state, [])
    assert view["current_diff"] == state["current_diff"]
    assert view["working_plan"]["plan"] == state["working_plan"]["plan"]
    finding = view["working_notes"]["findings"][0]
    assert finding["interpretation_status"] == "model_authored_unverified"
    if JUDGMENT:
        assert finding["model_interpretation"] == note["statement"]
        assert finding["evidence_delivery"] == "not_requested"
        assert view["working_notes"]["verification"]["items"][0]["status"] == "closed_by_model"
    else:
        assert finding == note
        assert "role" not in view["working_plan"]
        assert view["working_notes"]["verification"]["items"][0]["status"] == "resolved"
    assert state["working_notes"]["findings"][0] == note


def test_preparation_rejects_product_checkout_and_unknown_factor(tmp_path):
    with pytest.raises(ValueError, match="calling/product"):
        ablation.prepare(repository_root(), "E0J0", tmp_path / "receipt")
    with pytest.raises(ValueError, match="Unknown"):
        ablation.arm_sources(Path("."), "invented")
    with pytest.raises(ValueError, match="exact occurrences"):
        ablation.replace_exact("changed", "expected", "replacement")
