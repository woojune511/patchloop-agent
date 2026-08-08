from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from patchloop.errors import ContractError
from patchloop.memory import d102_maintainer_assisted_decisions as d102

ROOT = Path(__file__).resolve().parents[1]


def test_d102_checked_in_gate_exactly_validates() -> None:
    result = d102.validate_d102_decision_candidate_gate(repository=ROOT)

    assert result["gate_validation"] == "pass"
    assert result["decision_count"] == 5
    assert result["approved_group_count"] == 3
    assert result["continued_hold_group_count"] == 2
    assert result["approval_receipt_present"] is False
    assert result["admission_seal_created"] is False
    assert result["admitted_memory_rule_count"] == 0
    assert result["memory_index_build_authorized"] is False
    assert result["core_campaign_unlocked"] is False


def test_d102_exact_decision_mapping_and_assisted_provenance() -> None:
    result = d102.validate_d102_decision_candidate(repository=ROOT)

    assert [row["order"] for row in result["decisions"]] == [1, 2, 3, 4, 5]
    assert [row["decision"] for row in result["decisions"]] == [
        "approve",
        "approve",
        "continue_hold",
        "continue_hold",
        "approve",
    ]
    assert {row["reviewer_kind"] for row in result["decisions"]} == {"maintainer_assisted"}
    assert {row["reviewer"] for row in result["decisions"]} == {
        "maintainer-confirmed-system-recommendation"
    }
    assert result["preview_entry_count"] == 3


@pytest.mark.parametrize("target", ["journal", "candidate"])
def test_d102_exact_artifact_tampering_fails_closed(
    tmp_path: Path,
    target: str,
) -> None:
    journal = tmp_path / "decisions.jsonl"
    candidate = tmp_path / "candidate.json"
    shutil.copyfile(ROOT / d102.DEFAULT_JOURNAL_PATH, journal)
    shutil.copyfile(ROOT / d102.DEFAULT_CANDIDATE_PATH, candidate)
    selected = journal if target == "journal" else candidate
    selected.write_bytes(selected.read_bytes() + b" ")

    with pytest.raises(ContractError, match="byte count drifted"):
        d102.validate_d102_decision_candidate(
            repository=ROOT,
            journal_path=journal,
            candidate_path=candidate,
        )


def test_d102_gate_tampering_fails_closed(tmp_path: Path) -> None:
    gate = tmp_path / "gate.json"
    payload = json.loads((ROOT / d102.DEFAULT_GATE_PATH).read_text(encoding="utf-8"))
    payload["semantic_body"]["authority"]["memory_index_build_authorized"] = True
    gate.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(ContractError, match="exact bytes drifted"):
        d102.validate_d102_decision_candidate_gate(gate, repository=ROOT)


def test_d102_rebuild_is_deterministic_and_authority_stays_closed() -> None:
    first = d102.build_d102_decision_candidate_gate(repository=ROOT)
    second = d102.build_d102_decision_candidate_gate(repository=ROOT)

    assert d102.encode_d102_gate(first) == d102.encode_d102_gate(second)
    authority = first["semantic_body"]["authority"]
    assert authority["human_independent_technical_review_claimed"] is False
    assert authority["full_five_group_review_finalized"] is False
    assert authority["explicit_candidate_approval_pending"] is True
    assert authority["approval_receipt_present"] is False
    assert authority["admission_seal_created"] is False
    assert authority["admitted_memory_rule_count"] == 0
    assert authority["memory_admission_unlocked"] is False
    assert authority["memory_index_source_authoring_unlocked"] is False
    assert authority["memory_index_build_authorized"] is False
    assert authority["core_campaign_unlocked"] is False
    assert authority["provider_calls_made"] == 0
    assert authority["evaluator_calls_made"] == 0
    assert authority["added_model_cost_usd"] == 0
