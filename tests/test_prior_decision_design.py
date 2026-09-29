import copy
import json
from pathlib import Path

import pytest

from diagnostics import prior_decision_design as d
from patchloop.errors import ContractError
from patchloop.util import canonical_json, sha256_bytes


def original():
    return {"reviewer_instruction": d.base.QUESTION, "data": {"evidence": {
        "recent_attempt_result_next_question": [{"action_id": "probe1", "result": "failed",
            "next_question": "Other advice remains", "turn_decision": {
                "basis": "Prior causal explanation", "plan_update": "Prior proposed repair"}}],
        "program": "print('turn_decision'); assert output == 'fallback'",
        "output": canonical_json({"stdout": "actual observation", "diff_hash": "current"}),
        "question": "Does this explicit default survive?", "expected": "fallback",
        "setup": {"status": "passed"}, "source": "src[key]", "diff_hash": "current"}}}


def test_only_decision_removed_observations_and_advice_preserved():
    source = original()
    before = copy.deepcopy(source)
    pair, audit = d.project(source)
    assert source == before == pair["A"]
    removed = pair["A"]["data"]["evidence"]["recent_attempt_result_next_question"][0][
        "turn_decision"]
    expected = copy.deepcopy(source)
    del expected["data"]["evidence"]["recent_attempt_result_next_question"][0]["turn_decision"]
    assert pair["B"] == expected
    assert audit["removed"][0]["turn_decision"] == removed
    assert audit["reconstruction_matches_original"]
    assert audit["utf8_bytes"]["B"] < audit["utf8_bytes"]["A"]


@pytest.mark.parametrize("location", ["structured", "encoded", "nested_encoded", "prose"])
def test_duplicate_decisions_reject_without_mutating_evidence(location):
    source = original()
    duplicate = {"plan_update": "Prior proposed repair"}
    if location == "encoded":
        duplicate = canonical_json(duplicate)
    elif location == "nested_encoded":
        duplicate = canonical_json({"output": canonical_json(duplicate)})
    elif location == "prose":
        duplicate = "Quoted: Prior   causal\nexplanation."
    source["data"]["evidence"]["other"] = duplicate
    before = copy.deepcopy(source)
    with pytest.raises(ContractError, match="duplicate"):
        d.project(source)
    assert source == before


@pytest.mark.parametrize("change", ["question", "context", "no_decision"])
def test_unsupported_inputs_reject(change):
    source = original()
    if change == "question":
        source["reviewer_instruction"] = "New question"
    elif change == "context":
        source["data"]["surrounding_context"] = {}
    else:
        del source["data"]["evidence"]["recent_attempt_result_next_question"][0]["turn_decision"]
    with pytest.raises(ContractError):
        d.project(source)


def test_prepare_validate_and_tamper_without_credentials(tmp_path, monkeypatch):
    source_path = tmp_path / "source.json"
    source_path.write_text("source identity")
    pair, audit = d.project(original())
    projected = {c: (pair, audit) for c in ("C1", "C2", "C3", "C4")}
    monkeypatch.setattr(d, "inputs", lambda *args: projected)

    def forbidden(*args, **kwargs):
        pytest.fail("provider or credential accessed")

    monkeypatch.setattr(d.base.shared, "load_exact_openai_api_key", forbidden)
    monkeypatch.setattr(d.base.shared, "create_openai_client", forbidden)
    root = tmp_path / "new"
    d.prepare(source_path, sha256_bytes(source_path.read_bytes()), root)
    assert d.validate(root / "packet.json")["views"] == 8
    packet = json.loads((root / "packet.json").read_bytes())
    assert not packet["dispatch_enabled"]
    ref = packet["cases"]["C4"]["views"]["B"]
    Path(ref["path"]).write_text("changed output")
    with pytest.raises(ContractError, match="source CAS"):
        d.validate(root / "packet.json")
    with pytest.raises(ContractError, match="fresh external"):
        d.prepare(source_path, "hash", root)
