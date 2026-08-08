from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from patchloop.errors import ContractError
from patchloop.memory import d103_exact_candidate_admission as d103

ROOT = Path(__file__).resolve().parents[1]


def test_d103_checked_in_gate_exactly_validates() -> None:
    result = d103.validate_d103_exact_admission_gate(repository=ROOT)

    assert result["gate_validation"] == "pass"
    assert result["candidate_id"] == d103.d102.EXPECTED_CANDIDATE_ID
    assert result["receipt_id"] == d103.EXPECTED_RECEIPT_ID
    assert result["seal_id"] == d103.EXPECTED_SEAL_ID
    assert result["admitted_memory_rule_count"] == 3
    assert result["open_hold_group_count"] == 2
    assert result["memory_index_source_authoring_unlocked"] is True
    assert result["memory_index_build_authorized"] is False
    assert result["core_campaign_unlocked"] is False


def test_d103_receipt_is_exact_and_self_attested() -> None:
    result = d103.validate_d103_exact_admission(repository=ROOT)
    receipt = result["approval_receipt"]

    assert receipt["approval_action_id"] == "d103-exact-candidate-approval-1"
    assert receipt["approver_kind"] == "human"
    assert receipt["self_attested"] is True
    assert receipt["reviewer_identity_authenticated"] is False
    assert receipt["cryptographic_signature_verified"] is False
    assert receipt["approval_statement"] == d103.EXPECTED_APPROVAL_STATEMENT


def test_d103_seal_admits_only_the_three_approved_groups() -> None:
    result = d103.validate_d103_exact_admission(repository=ROOT)

    assert result["admitted_groups"] == list(d103.EXPECTED_ADMITTED_GROUPS)
    assert result["held_groups"] == list(d103.EXPECTED_HELD_GROUPS)


@pytest.mark.parametrize("target", ["receipt", "seal"])
def test_d103_exact_approval_artifact_tampering_fails_closed(
    tmp_path: Path,
    target: str,
) -> None:
    receipt = tmp_path / "receipt.json"
    seal = tmp_path / "seal.json"
    shutil.copyfile(ROOT / d103.DEFAULT_RECEIPT_PATH, receipt)
    shutil.copyfile(ROOT / d103.DEFAULT_SEAL_PATH, seal)
    selected = receipt if target == "receipt" else seal
    selected.write_bytes(selected.read_bytes() + b" ")

    with pytest.raises(ContractError, match="byte count drifted"):
        d103.validate_d103_exact_admission(
            repository=ROOT,
            receipt_path=receipt,
            seal_path=seal,
        )


def test_d103_gate_tampering_fails_closed(tmp_path: Path) -> None:
    gate = tmp_path / "gate.json"
    payload = json.loads((ROOT / d103.DEFAULT_GATE_PATH).read_text(encoding="utf-8"))
    payload["semantic_body"]["authority"]["memory_index_build_authorized"] = True
    gate.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(ContractError, match="exact bytes drifted"):
        d103.validate_d103_exact_admission_gate(gate, repository=ROOT)


def test_d103_gate_rebuild_is_deterministic() -> None:
    checked_in = (ROOT / d103.DEFAULT_GATE_PATH).read_bytes()
    rebuilt = d103.encode_d103_gate(d103.build_d103_exact_admission_gate(repository=ROOT))

    assert rebuilt == checked_in
