from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from patchloop.contracts import D099ReviewProposal
from patchloop.errors import ContractError
from patchloop.memory import d099_review, d100_group_admission, d101_group_admission
from patchloop.util import canonical_json, sha256_bytes, sha256_text

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL = ROOT / d099_review.DEFAULT_PROPOSAL_PATH
D100_GATE = ROOT / d100_group_admission.DEFAULT_SOURCE_GATE_PATH
PACKET_JSON = ROOT / d101_group_admission.DEFAULT_PACKET_JSON_PATH
PACKET_MARKDOWN = ROOT / d101_group_admission.DEFAULT_PACKET_MARKDOWN_PATH
SOURCE_GATE = ROOT / d101_group_admission.DEFAULT_SOURCE_GATE_PATH


def _proposal() -> D099ReviewProposal:
    return D099ReviewProposal.model_validate_json(PROPOSAL.read_bytes())


def _record_journal(
    journal: Path,
    *,
    decisions: dict[str, str] | None = None,
    reviewer_kind: str = "human",
) -> list[dict]:
    records: list[dict] = []
    tail = None
    for index, group in enumerate(_proposal().semantic_body.groups, start=1):
        decision = (
            decisions[group.semantic_group_id]
            if decisions is not None
            else ("approve" if group.disposition == "candidate" else "continue_hold")
        )
        record = d100_group_admission.record_d100_group_decision(
            PROPOSAL,
            journal,
            semantic_group_id=group.semantic_group_id,
            decision=decision,
            reviewer_kind=reviewer_kind,
            reviewer=f"fixture-{reviewer_kind}",
            rationale="Public evidence supports this explicit fixture decision.",
            action_id=f"fixture-{reviewer_kind}-{index}",
            expected_tail=tail,
            repository=ROOT,
        )
        records.append(record)
        tail = record["decision_hash"]
    return records


def _candidate(
    tmp_path: Path,
    *,
    decisions: dict[str, str] | None = None,
) -> tuple[dict, Path, Path]:
    journal = tmp_path / "decisions.jsonl"
    records = _record_journal(journal, decisions=decisions)
    payload = d101_group_admission.build_d101_admission_candidate(
        PACKET_JSON,
        PACKET_MARKDOWN,
        journal,
        journal_logical_path="reports/memory-development/review-decisions.jsonl",
        expected_journal_head=records[-1]["decision_hash"],
        expected_journal_record_count=len(records),
        expected_journal_file_sha256=sha256_bytes(journal.read_bytes()),
        prepared_at="2026-08-06T02:00:00Z",
        repository=ROOT,
    )
    candidate = tmp_path / "candidate.json"
    candidate.write_bytes(d101_group_admission.encode_d101_document(payload))
    return payload, candidate, journal


def _receipt(tmp_path: Path, candidate: Path) -> tuple[dict, Path]:
    parsed = json.loads(candidate.read_text(encoding="utf-8"))
    payload = d101_group_admission.build_d101_approval_receipt(
        candidate,
        candidate_logical_path="reports/memory-development/admission-candidate.json",
        approved_candidate_id=parsed["candidate_id"],
        approved_candidate_semantic_body_hash=parsed["semantic_body_hash"],
        approved_candidate_file_sha256=sha256_bytes(candidate.read_bytes()),
        approval_action_id="fixture-explicit-approval",
        approver_kind="human",
        approver_label="fixture-human-self-attestation",
        approval_reference="test:d101:explicit-approval",
        rationale="I explicitly approve this exact five-group candidate snapshot.",
        recorded_at="2026-08-06T02:01:00Z",
        repository=ROOT,
    )
    receipt = tmp_path / "receipt.json"
    receipt.write_bytes(d101_group_admission.encode_d101_document(payload))
    return payload, receipt


def _seal(
    tmp_path: Path,
    candidate: Path,
    receipt: Path,
    journal: Path,
) -> tuple[dict, Path]:
    payload = d101_group_admission.build_d101_admission_seal(
        candidate,
        receipt,
        journal,
        candidate_logical_path="reports/memory-development/admission-candidate.json",
        receipt_logical_path="reports/memory-development/approval-receipt.json",
        sealed_at="2026-08-06T02:02:00Z",
        repository=ROOT,
    )
    seal = tmp_path / "seal.json"
    seal.write_bytes(d101_group_admission.encode_d101_document(payload))
    return payload, seal


def _rehash(payload: dict, *, prefix: str, id_key: str) -> None:
    body_hash = sha256_text(canonical_json(payload["semantic_body"]))
    payload["semantic_body_hash"] = body_hash
    payload[id_key] = f"{prefix}_{body_hash.removeprefix('sha256:')}"


def test_d101_packet_and_markdown_exactly_rebuild() -> None:
    packet = d101_group_admission.build_d101_review_packet(repository=ROOT)

    assert d101_group_admission.encode_d101_document(packet) == PACKET_JSON.read_bytes()
    assert (
        d101_group_admission.render_d101_review_packet_markdown(packet)
        == PACKET_MARKDOWN.read_bytes()
    )
    result = d101_group_admission.validate_d101_review_packet(
        PACKET_JSON,
        PACKET_MARKDOWN,
        repository=ROOT,
    )
    assert result["packet_validation"] == "pass"
    assert result["semantic_group_count"] == 5
    assert result["candidate_group_count"] == 3
    assert result["hold_group_count"] == 2
    assert result["production_human_decision_records"] == 0
    assert result["memory_admission_unlocked"] is False


def test_d101_packet_preserves_d099_and_d100_group_bindings() -> None:
    packet = json.loads(PACKET_JSON.read_text(encoding="utf-8"))
    proposal = _proposal()
    d100 = json.loads(D100_GATE.read_text(encoding="utf-8"))
    groups = packet["semantic_body"]["groups"]

    assert [group["semantic_group_id"] for group in groups] == [
        group.semantic_group_id for group in proposal.semantic_body.groups
    ]
    assert [
        (
            group["semantic_group_id"],
            group["semantic_group_fingerprint"],
            group["disposition"],
            group["proposed_rule_hash"],
        )
        for group in groups
    ] == [
        (
            group["semantic_group_id"],
            group["semantic_group_fingerprint"],
            group["disposition"],
            group["proposed_rule_hash"],
        )
        for group in d100["semantic_body"]["group_bindings"]
    ]
    assert (
        sum(
            len(group["sources"])
            for group in groups
            if group["disposition"] == "candidate"
        )
        == 6
    )
    assert sum(len(group["sources"]) for group in groups if group["disposition"] == "hold") == 3
    assert all(group["decision_status"] == "not_made" for group in groups)


def test_d101_markdown_is_plain_korean_and_needs_no_internal_identifiers() -> None:
    text = PACKET_MARKDOWN.read_text(encoding="utf-8")

    assert text.startswith("# 실패 경험에서 만든 조언 5가지 검토\n")
    assert "[x]" not in text.lower()
    for order, group in enumerate(_proposal().semantic_body.groups, start=1):
        copy = d101_group_admission.KOREAN_REVIEW_COPY[group.semantic_group_id]
        title = copy["title"]
        assert title in text
        section = text.split(f"## {order}. {title}", 1)[1].split("\n## ", 1)[0]
        if group.proposed_rule is not None:
            assert "- **기억에 추가**" in section
        else:
            assert "- **기억에 추가**" not in section
        assert group.semantic_group_id not in text
        assert group.semantic_fingerprint not in text
        if group.proposed_rule is not None:
            assert d100_group_admission._rule_hash(group) not in text
    for internal_term in (
        "semantic group",
        "candidate",
        "continue_hold",
        "approve",
        "reject",
        "fingerprint",
        "dedup",
        "D-099",
        "D-100",
        "D-101",
        "receipt",
        "seal",
        "index/core",
    ):
        assert internal_term not in text
    assert "진행해줘" in text
    assert "내부 이름이나 긴 식별값을 복사할 필요가 없습니다" in text


def test_d101_korean_copy_has_no_fallback_for_missing_group(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    packet = json.loads(PACKET_JSON.read_text(encoding="utf-8"))
    incomplete = dict(d101_group_admission.KOREAN_REVIEW_COPY)
    incomplete.pop("diagnostic-contract-unresolved")
    monkeypatch.setattr(d101_group_admission, "KOREAN_REVIEW_COPY", incomplete)

    with pytest.raises(ContractError, match="exact group order"):
        d101_group_admission.render_d101_review_packet_markdown(packet)


def test_d101_rehashed_packet_or_markdown_drift_fails_closed(tmp_path: Path) -> None:
    packet = json.loads(PACKET_JSON.read_text(encoding="utf-8"))
    packet["semantic_body"]["warnings"][0] = "Public evidence was silently relabeled."
    _rehash(packet, prefix="d101packet", id_key="packet_id")
    packet_path = tmp_path / "packet.json"
    markdown_path = tmp_path / "packet.md"
    packet_path.write_bytes(d101_group_admission.encode_d101_document(packet))
    markdown_path.write_bytes(
        d101_group_admission.render_d101_review_packet_markdown(packet)
    )

    with pytest.raises(ContractError, match="exact evidence"):
        d101_group_admission.validate_d101_review_packet(
            packet_path,
            markdown_path,
            repository=ROOT,
        )

    packet_path.write_bytes(PACKET_JSON.read_bytes())
    markdown_path.write_bytes(PACKET_MARKDOWN.read_bytes() + b"\n")
    with pytest.raises(ContractError, match="Markdown"):
        d101_group_admission.validate_d101_review_packet(
            packet_path,
            markdown_path,
            repository=ROOT,
        )


def test_d101_candidate_embeds_exact_human_journal_and_preview(tmp_path: Path) -> None:
    payload, candidate, journal = _candidate(tmp_path)
    body = payload["semantic_body"]

    assert body["journal"]["record_count"] == 5
    assert body["journal"]["file_sha256"] == sha256_bytes(journal.read_bytes())
    assert [item["semantic_group_id"] for item in body["effective_decisions"]] == [
        group.semantic_group_id for group in _proposal().semantic_body.groups
    ]
    assert body["approved_group_count"] == 3
    assert body["rejected_group_count"] == 0
    assert body["continued_hold_group_count"] == 2
    assert len(body["preview"]["semantic_body"]["entries"]) == 3
    assert body["authority"]["explicit_candidate_approval_pending"] is True
    assert body["authority"]["memory_admission_unlocked"] is False
    result = d101_group_admission.validate_d101_admission_candidate(
        candidate,
        repository=ROOT,
        live_journal_path=journal,
        expected_candidate_file_sha256=sha256_bytes(candidate.read_bytes()),
    )
    assert result["candidate_validation"] == "pass"
    assert result["live_journal_validated"] is True


@pytest.mark.parametrize("wrong", ["head", "count", "file"])
def test_d101_candidate_requires_all_three_external_anchors(
    tmp_path: Path,
    wrong: str,
) -> None:
    journal = tmp_path / "decisions.jsonl"
    records = _record_journal(journal)
    kwargs = {
        "expected_journal_head": records[-1]["decision_hash"],
        "expected_journal_record_count": len(records),
        "expected_journal_file_sha256": sha256_bytes(journal.read_bytes()),
    }
    if wrong == "head":
        kwargs["expected_journal_head"] = "sha256:" + "0" * 64
    elif wrong == "count":
        kwargs["expected_journal_record_count"] = 4
    else:
        kwargs["expected_journal_file_sha256"] = "sha256:" + "0" * 64

    with pytest.raises(ContractError, match="anchor|file hash"):
        d101_group_admission.build_d101_admission_candidate(
            PACKET_JSON,
            PACKET_MARKDOWN,
            journal,
            journal_logical_path="reports/memory-development/decisions.jsonl",
            prepared_at="2026-08-06T02:00:00Z",
            repository=ROOT,
            **kwargs,
        )


def test_d101_candidate_rejects_incomplete_or_any_synthetic_history(tmp_path: Path) -> None:
    incomplete = tmp_path / "incomplete.jsonl"
    group = _proposal().semantic_body.groups[0]
    first = d100_group_admission.record_d100_group_decision(
        PROPOSAL,
        incomplete,
        semantic_group_id=group.semantic_group_id,
        decision="approve",
        reviewer_kind="human",
        reviewer="fixture-human",
        rationale="Public evidence supports this explicit fixture decision.",
        action_id="incomplete-one",
        expected_tail=None,
        repository=ROOT,
    )
    with pytest.raises(ContractError, match="every semantic group"):
        d101_group_admission.build_d101_admission_candidate(
            PACKET_JSON,
            PACKET_MARKDOWN,
            incomplete,
            journal_logical_path="reports/memory-development/incomplete.jsonl",
            expected_journal_head=first["decision_hash"],
            expected_journal_record_count=1,
            expected_journal_file_sha256=sha256_bytes(incomplete.read_bytes()),
            prepared_at="2026-08-06T02:00:00Z",
            repository=ROOT,
        )

    synthetic = tmp_path / "synthetic.jsonl"
    records = _record_journal(synthetic, reviewer_kind="synthetic")
    with pytest.raises(ContractError, match="synthetic"):
        d101_group_admission.build_d101_admission_candidate(
            PACKET_JSON,
            PACKET_MARKDOWN,
            synthetic,
            journal_logical_path="reports/memory-development/synthetic.jsonl",
            expected_journal_head=records[-1]["decision_hash"],
            expected_journal_record_count=5,
            expected_journal_file_sha256=sha256_bytes(synthetic.read_bytes()),
            prepared_at="2026-08-06T02:00:00Z",
            repository=ROOT,
        )


def test_d101_candidate_rejects_superseded_synthetic_row(tmp_path: Path) -> None:
    journal = tmp_path / "mixed.jsonl"
    records = _record_journal(journal, reviewer_kind="synthetic")
    correction = d100_group_admission.record_d100_group_decision(
        PROPOSAL,
        journal,
        semantic_group_id=_proposal().semantic_body.groups[0].semantic_group_id,
        decision="approve",
        reviewer_kind="human",
        reviewer="fixture-human",
        rationale="A human corrected the effective decision using public evidence.",
        action_id="human-correction",
        expected_tail=records[-1]["decision_hash"],
        repository=ROOT,
    )
    with pytest.raises(ContractError, match="synthetic"):
        d101_group_admission.build_d101_admission_candidate(
            PACKET_JSON,
            PACKET_MARKDOWN,
            journal,
            journal_logical_path="reports/memory-development/mixed.jsonl",
            expected_journal_head=correction["decision_hash"],
            expected_journal_record_count=6,
            expected_journal_file_sha256=sha256_bytes(journal.read_bytes()),
            prepared_at="2026-08-06T02:00:00Z",
            repository=ROOT,
        )


def test_d101_candidate_rebuild_rejects_embedded_tampering(tmp_path: Path) -> None:
    payload, candidate, _ = _candidate(tmp_path)
    payload["semantic_body"]["effective_decisions"][0]["reviewer"] = "tampered"
    _rehash(payload, prefix="d101candidate", id_key="candidate_id")
    candidate.write_bytes(d101_group_admission.encode_d101_document(payload))

    with pytest.raises(ContractError, match="semantic rebuild"):
        d101_group_admission.validate_d101_admission_candidate(
            candidate,
            repository=ROOT,
        )


def test_d101_candidate_live_journal_mismatch_fails(tmp_path: Path) -> None:
    _, candidate, journal = _candidate(tmp_path)
    parsed = json.loads(candidate.read_text(encoding="utf-8"))
    tail = parsed["semantic_body"]["journal"]["head_decision_hash"]
    d100_group_admission.record_d100_group_decision(
        PROPOSAL,
        journal,
        semantic_group_id=_proposal().semantic_body.groups[0].semantic_group_id,
        decision="reject",
        reviewer_kind="human",
        reviewer="fixture-human",
        rationale="A later public-evidence correction changes the live journal.",
        action_id="later-correction",
        expected_tail=tail,
        repository=ROOT,
    )

    with pytest.raises(ContractError, match="live decision journal differs"):
        d101_group_admission.validate_d101_admission_candidate(
            candidate,
            repository=ROOT,
            live_journal_path=journal,
        )


def test_d101_receipt_binds_exact_candidate_and_is_self_attested(tmp_path: Path) -> None:
    _, candidate, _ = _candidate(tmp_path)
    payload, receipt = _receipt(tmp_path, candidate)
    body = payload["semantic_body"]

    assert candidate.read_text(encoding="utf-8").strip()
    assert body["candidate"]["file_sha256"] == sha256_bytes(candidate.read_bytes())
    assert body["approval_statement"].startswith(
        "EXPLICITLY_APPROVE_EXACT_D101_CANDIDATE d101candidate_"
    )
    assert body["explicit_approval_receipt_recorded"] is True
    assert body["reviewer_identity_authenticated"] is False
    assert body["cryptographic_signature_verified"] is False
    result = d101_group_admission.validate_d101_approval_receipt(
        receipt,
        candidate,
        repository=ROOT,
    )
    assert result["receipt_validation"] == "pass"


@pytest.mark.parametrize("wrong", ["id", "semantic", "file"])
def test_d101_receipt_rejects_wrong_candidate_identity(tmp_path: Path, wrong: str) -> None:
    payload, candidate, _ = _candidate(tmp_path)
    values = {
        "approved_candidate_id": payload["candidate_id"],
        "approved_candidate_semantic_body_hash": payload["semantic_body_hash"],
        "approved_candidate_file_sha256": sha256_bytes(candidate.read_bytes()),
    }
    key = {
        "id": "approved_candidate_id",
        "semantic": "approved_candidate_semantic_body_hash",
        "file": "approved_candidate_file_sha256",
    }[wrong]
    values[key] = (
        "d101candidate_" + "0" * 64 if wrong == "id" else "sha256:" + "0" * 64
    )

    with pytest.raises(ContractError, match="does not match|external anchor"):
        d101_group_admission.build_d101_approval_receipt(
            candidate,
            candidate_logical_path="reports/memory-development/candidate.json",
            approval_action_id="wrong-binding",
            approver_kind="human",
            approver_label="fixture-human",
            approval_reference="test:d101:wrong",
            rationale="This exact binding should be rejected.",
            recorded_at="2026-08-06T02:01:00Z",
            repository=ROOT,
            **values,
        )


def test_d101_receipt_rejects_invalid_or_leaking_approval_metadata(tmp_path: Path) -> None:
    payload, candidate, _ = _candidate(tmp_path)
    common = {
        "candidate_logical_path": "reports/memory-development/candidate.json",
        "approved_candidate_id": payload["candidate_id"],
        "approved_candidate_semantic_body_hash": payload["semantic_body_hash"],
        "approved_candidate_file_sha256": sha256_bytes(candidate.read_bytes()),
        "approval_action_id": "metadata-check",
        "approver_kind": "human",
        "approver_label": "fixture-human",
        "approval_reference": "test:d101:metadata",
        "rationale": "I approve this exact candidate snapshot.",
        "recorded_at": "2026-08-06T02:01:00Z",
        "repository": ROOT,
    }
    with pytest.raises(ContractError, match="timezone-aware"):
        d101_group_admission.build_d101_approval_receipt(
            candidate,
            **{**common, "recorded_at": "2026-08-06T02:01:00"},
        )
    leaking = "OPENAI_API_KEY=fixture-not-a-real-secret"
    with pytest.raises(ContractError) as captured:
        d101_group_admission.build_d101_approval_receipt(
            candidate,
            **{**common, "rationale": leaking},
        )
    assert leaking not in str(captured.value)


def test_d101_receipt_rebuild_rejects_tampering(tmp_path: Path) -> None:
    _, candidate, _ = _candidate(tmp_path)
    payload, receipt = _receipt(tmp_path, candidate)
    payload["semantic_body"]["approval_statement"] += " altered"
    _rehash(payload, prefix="d101receipt", id_key="receipt_id")
    receipt.write_bytes(d101_group_admission.encode_d101_document(payload))

    with pytest.raises(ContractError, match="semantic rebuild"):
        d101_group_admission.validate_d101_approval_receipt(
            receipt,
            candidate,
            repository=ROOT,
        )


def test_d101_seal_admits_only_approved_entries_and_keeps_index_closed(
    tmp_path: Path,
) -> None:
    _, candidate, journal = _candidate(tmp_path)
    _, receipt = _receipt(tmp_path, candidate)
    payload, seal = _seal(tmp_path, candidate, receipt, journal)
    authority = payload["semantic_body"]["authority"]

    assert len(payload["semantic_body"]["admitted_entries"]) == 3
    assert authority["admitted_memory_rule_count"] == 3
    assert authority["open_hold_group_count"] == 2
    assert authority["group_review_finalized"] is False
    assert authority["memory_admission_unlocked"] is True
    assert authority["memory_index_source_authoring_unlocked"] is True
    assert authority["memory_index_build_authorized"] is False
    assert authority["memory_index_built"] is False
    assert authority["core_campaign_unlocked"] is False
    result = d101_group_admission.validate_d101_admission_seal(
        seal,
        candidate,
        receipt,
        journal,
        repository=ROOT,
        expected_seal_file_sha256=sha256_bytes(seal.read_bytes()),
    )
    assert result["seal_validation"] == "pass"


def test_d101_zero_approval_seal_finalizes_review_without_admission(tmp_path: Path) -> None:
    decisions = {
        group.semantic_group_id: "reject" for group in _proposal().semantic_body.groups
    }
    _, candidate, journal = _candidate(tmp_path, decisions=decisions)
    _, receipt = _receipt(tmp_path, candidate)
    payload, _ = _seal(tmp_path, candidate, receipt, journal)
    authority = payload["semantic_body"]["authority"]

    assert payload["semantic_body"]["admitted_entries"] == []
    assert authority["admitted_memory_rule_count"] == 0
    assert authority["open_hold_group_count"] == 0
    assert authority["group_review_finalized"] is True
    assert authority["memory_admission_unlocked"] is False
    assert authority["memory_index_source_authoring_unlocked"] is False


def test_d101_seal_rejects_live_journal_or_semantic_tampering(tmp_path: Path) -> None:
    _, candidate, journal = _candidate(tmp_path)
    _, receipt = _receipt(tmp_path, candidate)
    payload, seal = _seal(tmp_path, candidate, receipt, journal)
    tail = payload["semantic_body"]["journal"]["head_decision_hash"]
    d100_group_admission.record_d100_group_decision(
        PROPOSAL,
        journal,
        semantic_group_id=_proposal().semantic_body.groups[0].semantic_group_id,
        decision="reject",
        reviewer_kind="human",
        reviewer="fixture-human",
        rationale="A later correction invalidates the exact admission snapshot.",
        action_id="post-receipt-correction",
        expected_tail=tail,
        repository=ROOT,
    )
    with pytest.raises(ContractError, match="live decision journal differs"):
        d101_group_admission.validate_d101_admission_seal(
            seal,
            candidate,
            receipt,
            journal,
            repository=ROOT,
        )

    journal.write_bytes(
        b"".join(
            canonical_json(record).encode("utf-8") + b"\n"
            for record in json.loads(candidate.read_text(encoding="utf-8"))[
                "semantic_body"
            ]["journal_records"]
        )
    )
    payload["semantic_body"]["admitted_entries"] = []
    payload["semantic_body"]["authority"]["admitted_memory_rule_count"] = 0
    payload["semantic_body"]["authority"]["memory_admission_unlocked"] = False
    payload["semantic_body"]["authority"]["memory_index_source_authoring_unlocked"] = False
    _rehash(payload, prefix="d101seal", id_key="seal_id")
    seal.write_bytes(d101_group_admission.encode_d101_document(payload))
    with pytest.raises(ContractError, match="semantic rebuild"):
        d101_group_admission.validate_d101_admission_seal(
            seal,
            candidate,
            receipt,
            journal,
            repository=ROOT,
        )


def test_d101_exclusive_writer_is_idempotent_and_never_overwrites(tmp_path: Path) -> None:
    output = tmp_path / "nested" / "artifact.json"
    first = d101_group_admission.write_d101_new_exact(output, b"exact\n")
    before_mtime = output.stat().st_mtime_ns
    retry = d101_group_admission.write_d101_new_exact(output, b"exact\n")

    assert first["created"] is True
    assert retry["idempotent_retry"] is True
    assert output.stat().st_mtime_ns == before_mtime
    with pytest.raises(ContractError, match="different bytes"):
        d101_group_admission.write_d101_new_exact(output, b"different\n")
    assert output.read_bytes() == b"exact\n"


def test_d101_source_gate_exactly_rebuilds_and_keeps_authority_closed() -> None:
    expected = d101_group_admission.build_d101_source_gate(repository=ROOT)

    assert d101_group_admission.encode_d101_document(expected) == SOURCE_GATE.read_bytes()
    result = d101_group_admission.validate_d101_source_gate(
        SOURCE_GATE,
        repository=ROOT,
    )
    assert result["source_gate_validation"] == "pass"
    assert result["production_human_decision_records"] == 0
    assert result["admission_candidate_created"] is False
    assert result["approval_receipt_present"] is False
    assert result["admission_seal_created"] is False
    assert result["memory_admission_unlocked"] is False
    assert result["memory_index_build_authorized"] is False
    assert result["core_campaign_unlocked"] is False
    assert result["provider_calls_made"] == 0


def test_d101_preserves_exact_d100_source_gate() -> None:
    before = D100_GATE.read_bytes()
    result = d100_group_admission.validate_d100_source_gate(D100_GATE, repository=ROOT)

    assert result["source_gate_validation"] == "pass"
    assert D100_GATE.read_bytes() == before


def _copy_portable_repository(tmp_path: Path) -> Path:
    repository = tmp_path / "portable"
    paths = [
        Path(d099_review.SOURCE_REPORT_PATH),
        Path("data/dataset-manifest.yaml"),
        d099_review.DEFAULT_PROPOSAL_PATH,
        d100_group_admission.DEFAULT_SOURCE_GATE_PATH,
        d101_group_admission.DEFAULT_PACKET_JSON_PATH,
        d101_group_admission.DEFAULT_PACKET_MARKDOWN_PATH,
        d101_group_admission.DEFAULT_SOURCE_GATE_PATH,
        *d100_group_admission.SOURCE_IMPLEMENTATION_PATHS,
        *d101_group_admission.SOURCE_IMPLEMENTATION_PATHS,
        *(
            Path("tasks/dev-train") / source["task_id"] / "public.yaml"
            for source in d099_review.SOURCE_SPECS
        ),
        *(
            d099_review.PATCH_ARTIFACT_ROOT / f"{source['run_id']}.submitted.patch"
            for source in d099_review.SOURCE_SPECS
        ),
    ]
    for relative in dict.fromkeys(paths):
        destination = repository / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, destination)
    return repository


def test_d101_source_gate_validates_in_portable_repository(tmp_path: Path) -> None:
    repository = _copy_portable_repository(tmp_path)

    assert not (repository / ".patchloop").exists()
    result = d101_group_admission.validate_d101_source_gate(repository=repository)
    assert result["source_gate_validation"] == "pass"
    assert result["production_human_decision_records"] == 0
