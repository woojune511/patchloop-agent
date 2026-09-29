import copy
import json
from pathlib import Path

import pytest

from diagnostics import evidence_context_design as design
from patchloop.dev.conversation import WINDOW_RULES
from patchloop.errors import ContractError
from patchloop.util import canonical_json


def source():
    archive = {
        "kind": "harness_historical_public_evidence_v1", "sources": [], "observations": [],
        "instructions": WINDOW_RULES.instructions,
        "referenced_public_exchanges": [
            {"type": "function_call", "call_id": "p1", "name": "run_probe",
             "arguments": canonical_json({"python_source": "print('observation')",
                                          "question": "What happened?",
                                          "turn_decision": {"basis": "unverified prior belief"}})},
            {"type": "function_call_output", "call_id": "p1",
             "output": canonical_json({"action_id": "p1", "stdout": "setup failed",
                                       "diff_hash": "older", "setup_status": "failed"})},
        ],
    }
    state = {"current_diff": {"patch_hash": "current", "patch": "public diff"},
             "current_sources": [], "recent_probes": [{"action_id": "p1", "historical": True}],
             "visible_check_status": [{"status": "PASS", "diff_hash": "current"}],
             "working_plan": {"text": "unverified current plan"},
             "completion_guidance": {"next_action": "finish"},
             "last_successful_mutation": {"observed_post_image": "exact public source"},
             "working_notes": {"verification": {"observations": {"items": ["public result"]}}}}
    return {"tools": [{"name": "finish_task"}], "input": [
        {"role": "system", "content": "original coding instructions"},
        {"role": "developer", "content": canonical_json({"public_task": {
            "issue": "public requirement", "visible_checks": ["exact check code"]}})},
        {"role": "user", "content": "Proceed"},
        {"role": "developer", "content": canonical_json(archive)},
        {"role": "developer", "content": canonical_json({"kind": "harness_current_state",
                                                           "state": state})},
    ]}


def test_same_evidence_different_context_and_no_source_mutation():
    original = source()
    before = copy.deepcopy(original)
    views, receipt = design.project(original)
    assert original == before
    assert views["A"]["evidence"] == views["B"]["evidence"]
    assert set(views["B"]) == {"evidence"}
    assert views["B"]["evidence"]["current_diff"]["patch_hash"] == "current"
    assert views["B"]["evidence"]["last_successful_mutation"] == {
        "observed_post_image": "exact public source"}
    assert views["B"]["evidence"]["verification_observations"]["items"] == ["public result"]
    assert receipt["moved_public_decision_count"] == 1
    assert receipt["utf8_bytes"]["B"] < receipt["utf8_bytes"]["A"]


def test_prior_explanation_moves_but_probe_program_and_output_survive():
    original = source()
    views, _ = design.project(original)
    evidence = views["B"]["evidence"]
    exchange = evidence["public_archive"]["referenced_public_exchanges"]
    assert json.loads(exchange[0]["arguments"]) == {
        "python_source": "print('observation')", "question": "What happened?"}
    assert exchange[1] == json.loads(original["input"][3]["content"])[
        "referenced_public_exchanges"][1]
    assert "unverified prior belief" not in canonical_json(views["B"])
    assert "unverified current plan" not in canonical_json(views["B"])
    assert "unverified prior belief" in canonical_json(views["A"])


@pytest.mark.parametrize("change", ["reasoning", "archive"])
def test_unsupported_layout_is_rejected_instead_of_silently_truncated(change):
    original = source()
    if change == "reasoning":
        original["input"].insert(3, {"type": "reasoning", "encrypted_content": "opaque"})
    else:
        original["input"][3]["content"] = '{"kind":"unknown_archive"}'
    with pytest.raises(ContractError):
        design.project(original)


def test_prepare_only_writes_external_bound_artifacts(tmp_path, monkeypatch):
    views, receipt = design.project(source())
    monkeypatch.setattr(design, "load_sources", lambda: ({"C1": (views, receipt)}, {}))

    def forbidden(*args, **kwargs):
        pytest.fail("provider or credential path reached")

    monkeypatch.setattr(design.shared, "create_openai_client", forbidden)
    monkeypatch.setattr(design.shared, "load_exact_openai_api_key", forbidden)
    root = tmp_path / "external"
    packet = design.prepare(root)
    assert packet["status"] == "PREPARED_NOT_EXECUTABLE"
    assert packet["dispatch_enabled"] is False and packet["provider_calls"] == 0
    assert len(packet["cases"]["C1"]["views"]) == 2
    assert design.validate(root / "packet.json")["equal_evidence_within_pairs"]
    ref = packet["cases"]["C1"]["views"]["B"]
    Path(ref["path"]).write_text("{}")
    with pytest.raises(ContractError, match="artifact changed"):
        design.validate(root / "packet.json")
    with pytest.raises(ContractError, match="fresh external"):
        design.prepare(root)
