from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError
from typer.testing import CliRunner

from patchloop.cli import app
from patchloop.contracts import D099ReviewProposal, D100GroupDecisionRecord, MemoryEntry
from patchloop.errors import ContractError
from patchloop.memory import d099_review, d100_group_admission
from patchloop.util import canonical_json, sha256_bytes, sha256_text

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL = ROOT / d099_review.DEFAULT_PROPOSAL_PATH
SOURCE_GATE = ROOT / d100_group_admission.DEFAULT_SOURCE_GATE_PATH


def _proposal() -> D099ReviewProposal:
    return D099ReviewProposal.model_validate_json(PROPOSAL.read_text(encoding="utf-8"))


def _copy_portable_repository(tmp_path: Path) -> tuple[Path, Path]:
    repository = tmp_path / "clean-repository"
    relative_paths = [
        Path(d099_review.SOURCE_REPORT_PATH),
        Path("data/dataset-manifest.yaml"),
        d099_review.DEFAULT_PROPOSAL_PATH,
        *(
            Path("tasks/dev-train") / source["task_id"] / "public.yaml"
            for source in d099_review.SOURCE_SPECS
        ),
        *(
            d099_review.PATCH_ARTIFACT_ROOT / f"{source['run_id']}.submitted.patch"
            for source in d099_review.SOURCE_SPECS
        ),
    ]
    for relative in dict.fromkeys(relative_paths):
        source = ROOT / relative
        destination = repository / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    return repository, repository / d099_review.DEFAULT_PROPOSAL_PATH


def _record(
    journal: Path,
    group: str,
    decision: str,
    action_id: str,
    expected_tail: str | None,
    *,
    proposal_path: Path = PROPOSAL,
    repository: Path = ROOT,
    reviewer: str = "maintainer-geonj",
    rationale: str = "Public evidence supports this explicit synthetic test decision.",
) -> dict:
    return d100_group_admission.record_d100_group_decision(
        proposal_path,
        journal,
        semantic_group_id=group,
        decision=decision,
        reviewer_kind="synthetic",
        reviewer=reviewer,
        rationale=rationale,
        action_id=action_id,
        expected_tail=expected_tail,
        repository=repository,
    )


def _complete_journal(
    journal: Path,
    *,
    approve_candidates: bool = True,
    proposal_path: Path = PROPOSAL,
    repository: Path = ROOT,
) -> list[dict]:
    records: list[dict] = []
    tail = None
    for index, group in enumerate(_proposal().semantic_body.groups, start=1):
        decision = (
            "approve"
            if approve_candidates and group.disposition == "candidate"
            else "continue_hold"
        )
        record = _record(
            journal,
            group.semantic_group_id,
            decision,
            f"synthetic-{index}",
            tail,
            proposal_path=proposal_path,
            repository=repository,
        )
        records.append(record)
        tail = record["decision_hash"]
    return records


def _tree_fingerprint(root: Path) -> dict[str, tuple[int, int, str]]:
    if not root.exists():
        return {}
    return {
        path.relative_to(root).as_posix(): (
            path.stat().st_size,
            path.stat().st_mtime_ns,
            sha256_bytes(path.read_bytes()),
        )
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_d100_status_keeps_production_authority_closed() -> None:
    result = d100_group_admission.d100_mechanism_status(PROPOSAL, repository=ROOT)

    assert result["schema_version"] == "memory-group-review-mechanism-status-d100-v1"
    assert result["decision_journal_contract_implemented"] is True
    assert result["group_aware_preview_implemented"] is True
    assert result["semantic_group_count"] == 5
    assert result["production_human_decision_records"] == 0
    assert result["group_review_completed"] is False
    assert result["admitted_memory_rule_count"] == 0
    assert result["preview_entry_count"] == 0
    assert result["memory_admission_unlocked"] is False
    assert result["memory_index_build_authorized"] is False
    assert result["memory_index_built"] is False
    assert result["core_campaign_unlocked"] is False
    assert result["provider_calls_made"] == 0


def test_d100_records_hash_chain_and_idempotent_retry(tmp_path: Path) -> None:
    journal = tmp_path / "decisions.jsonl"
    first = _record(
        journal,
        "platform-emulation-matrix-gap",
        "approve",
        "action-platform",
        None,
    )
    retry = _record(
        journal,
        "platform-emulation-matrix-gap",
        "approve",
        "action-platform",
        None,
    )
    second = _record(
        journal,
        "request-context-propagation-gap",
        "reject",
        "action-context",
        first["decision_hash"],
    )

    assert first["appended"] is True
    assert retry["appended"] is False
    assert retry["idempotent_retry"] is True
    assert retry["decision_hash"] == first["decision_hash"]
    assert second["sequence"] == 2
    assert second["previous_decision_hash"] == first["decision_hash"]
    assert journal.read_bytes().count(b"\n") == 2
    validated = d100_group_admission.validate_d100_decision_journal(
        PROPOSAL,
        journal,
        repository=ROOT,
    )
    assert validated["record_count"] == 2
    assert validated["decided_group_count"] == 2
    assert validated["complete_group_decisions"] is False


def test_d100_rejects_action_conflict_and_stale_tail(tmp_path: Path) -> None:
    journal = tmp_path / "decisions.jsonl"
    first = _record(
        journal,
        "platform-emulation-matrix-gap",
        "approve",
        "action-one",
        None,
    )
    with pytest.raises(ContractError, match="action ID was reused"):
        _record(
            journal,
            "platform-emulation-matrix-gap",
            "reject",
            "action-one",
            first["decision_hash"],
        )
    with pytest.raises(ContractError, match="action ID was reused"):
        _record(
            journal,
            "platform-emulation-matrix-gap",
            "approve",
            "action-one",
            first["decision_hash"],
        )
    with pytest.raises(ContractError, match="expected journal tail"):
        _record(
            journal,
            "request-context-propagation-gap",
            "approve",
            "action-two",
            None,
        )
    assert journal.read_bytes().count(b"\n") == 1


def test_d100_hold_cannot_be_approved_and_leak_is_not_echoed(tmp_path: Path) -> None:
    journal = tmp_path / "decisions.jsonl"
    with pytest.raises(ContractError, match="hold groups cannot be approved"):
        _record(
            journal,
            "interrupt-lifecycle-unresolved",
            "approve",
            "hold-approve",
            None,
        )
    leaking = "OPENAI_API_KEY=not-a-real-secret-value"
    with pytest.raises(ContractError) as captured:
        _record(
            journal,
            "platform-emulation-matrix-gap",
            "reject",
            "leaking-rationale",
            None,
            rationale=leaking,
        )
    assert str(captured.value) == "D-100 rationale leak scan failed"
    assert leaking not in str(captured.value)
    assert not journal.exists()


def test_d100_correction_supersedes_latest_group_decision(tmp_path: Path) -> None:
    journal = tmp_path / "decisions.jsonl"
    first = _record(
        journal,
        "platform-emulation-matrix-gap",
        "approve",
        "initial-platform",
        None,
    )
    correction = _record(
        journal,
        "platform-emulation-matrix-gap",
        "reject",
        "correct-platform",
        first["decision_hash"],
    )

    assert correction["event_kind"] == "DecisionCorrected"
    assert correction["supersedes_decision_hash"] == first["decision_hash"]
    assert correction["proposed_rule_hash"] is None


def test_d100_writer_lock_prevents_a_forked_append(tmp_path: Path) -> None:
    journal = tmp_path / "decisions.jsonl"
    with (
        d100_group_admission._journal_lock(journal),
        pytest.raises(ContractError, match="already has a writer"),
    ):
        _record(
            journal,
            "platform-emulation-matrix-gap",
            "approve",
            "contending-writer",
            None,
        )
    assert not journal.exists()


def test_d100_os_lock_rejects_a_subprocess_writer(tmp_path: Path) -> None:
    journal = tmp_path / "decisions.jsonl"
    child = """
import sys
from patchloop.errors import ContractError
from patchloop.memory.d100_group_admission import record_d100_group_decision

try:
    record_d100_group_decision(
        sys.argv[1],
        sys.argv[2],
        semantic_group_id="platform-emulation-matrix-gap",
        decision="approve",
        reviewer_kind="synthetic",
        reviewer="subprocess-test",
        rationale="Synthetic cross-process writer contention test.",
        action_id="subprocess-contention",
        expected_tail=None,
        repository=sys.argv[3],
    )
except ContractError as exc:
    if "already has a writer" in str(exc):
        raise SystemExit(0)
    print(str(exc), file=sys.stderr)
    raise SystemExit(3)
raise SystemExit(2)
"""
    with d100_group_admission._journal_lock(journal):
        result = subprocess.run(
            [sys.executable, "-c", child, str(PROPOSAL), str(journal), str(ROOT)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    assert result.returncode == 0, result.stderr
    assert not journal.exists()


def test_d100_append_calls_fsync(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    journal = tmp_path / "decisions.jsonl"
    fsynced: list[int] = []
    monkeypatch.setattr(d100_group_admission.os, "fsync", fsynced.append)

    _record(
        journal,
        "platform-emulation-matrix-gap",
        "approve",
        "fsync-observed",
        None,
    )

    assert len(fsynced) == 1


def test_d100_projector_maps_three_groups_to_three_templates(tmp_path: Path) -> None:
    journal = tmp_path / "decisions.jsonl"
    _complete_journal(journal)

    preview = d100_group_admission.project_d100_memory_entry_preview(
        PROPOSAL,
        journal,
        repository=ROOT,
    )
    body = preview["semantic_body"]
    assert body["approved_group_ids"] == [
        "platform-emulation-matrix-gap",
        "request-context-propagation-gap",
        "exception-origin-state-conflation",
    ]
    assert body["continued_hold_group_ids"] == [
        "interrupt-lifecycle-unresolved",
        "diagnostic-contract-unresolved",
    ]
    assert len(body["entries"]) == 3
    assert sum(len(item["template"]["source_run_ids"]) for item in body["entries"]) == 6
    assert all(item["template"]["validation_count"] == 0 for item in body["entries"])
    assert all("index_version" not in item["template"] for item in body["entries"])
    assert all("embedding" not in item["template"] for item in body["entries"])
    assert body["authority"]["projection_only"] is True
    assert body["authority"]["external_head_anchor_validated"] is False
    assert body["authority"]["admission_seal_created"] is False
    assert body["authority"]["admitted_memory_rule_count"] == 0
    assert body["authority"]["memory_index_build_authorized"] is False

    proposal = _proposal()
    groups = {group.semantic_group_id: group for group in proposal.semantic_body.groups}
    for item in body["entries"]:
        group = groups[item["provenance"]["semantic_group_id"]]
        rule = group.proposed_rule
        assert rule is not None
        template = item["template"]
        assert template["failure_pattern"] == {
            "failure_class": rule.failure_class,
            "phase": rule.phase.value,
            "description": rule.description,
        }
        assert template["preconditions"] == rule.preconditions
        assert template["diagnostic_evidence"] == rule.diagnostic_evidence
        assert template["recommended_actions"] == rule.recommended_actions
        assert template["do_not_apply_when"] == rule.do_not_apply_when
        assert template["confidence"] == rule.confidence
        assert template["source_run_ids"] == [member.run_id for member in group.members]
        with pytest.raises(ValidationError):
            MemoryEntry.model_validate(template)


def test_d100_complete_hold_projection_creates_no_templates(tmp_path: Path) -> None:
    journal = tmp_path / "decisions.jsonl"
    _complete_journal(journal, approve_candidates=False)

    preview = d100_group_admission.project_d100_memory_entry_preview(
        PROPOSAL,
        journal,
        repository=ROOT,
    )
    assert preview["semantic_body"]["approved_group_ids"] == []
    assert preview["semantic_body"]["entries"] == []
    assert len(preview["semantic_body"]["continued_hold_group_ids"]) == 5


def test_d100_preview_identity_is_independent_of_reviewer_metadata(tmp_path: Path) -> None:
    first_journal = tmp_path / "first.jsonl"
    second_journal = tmp_path / "second.jsonl"
    _complete_journal(first_journal)
    tail = None
    for index, group in enumerate(_proposal().semantic_body.groups, start=1):
        decision = "approve" if group.disposition == "candidate" else "continue_hold"
        record = _record(
            second_journal,
            group.semantic_group_id,
            decision,
            f"other-{index}",
            tail,
            reviewer="different-maintainer",
            rationale="A different public-only rationale reaches the same explicit decision.",
        )
        tail = record["decision_hash"]

    first = d100_group_admission.project_d100_memory_entry_preview(
        PROPOSAL, first_journal, repository=ROOT
    )
    second = d100_group_admission.project_d100_memory_entry_preview(
        PROPOSAL, second_journal, repository=ROOT
    )
    assert [
        entry["template"]["proposed_memory_id"] for entry in first["semantic_body"]["entries"]
    ] == [entry["template"]["proposed_memory_id"] for entry in second["semantic_body"]["entries"]]
    assert first["preview_id"] != second["preview_id"]


def test_d100_preview_requires_complete_group_decisions(tmp_path: Path) -> None:
    journal = tmp_path / "decisions.jsonl"
    _record(
        journal,
        "platform-emulation-matrix-gap",
        "approve",
        "only-one",
        None,
    )
    with pytest.raises(ContractError, match="decision for every semantic group"):
        d100_group_admission.project_d100_memory_entry_preview(
            PROPOSAL,
            journal,
            repository=ROOT,
        )


def test_d100_projection_descriptor_uses_the_parsed_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    journal = tmp_path / "decisions.jsonl"
    records = _complete_journal(journal)
    original_content = journal.read_bytes()
    original_read = d100_group_admission._read_journal
    correction: dict[str, object] = {}
    injected = False

    def racing_read(*args: object, **kwargs: object):
        nonlocal injected, correction
        snapshot = original_read(*args, **kwargs)
        if not injected:
            injected = True
            monkeypatch.setattr(d100_group_admission, "_read_journal", original_read)
            correction = _record(
                journal,
                "platform-emulation-matrix-gap",
                "reject",
                "concurrent-correction",
                records[-1]["decision_hash"],
            )
            monkeypatch.setattr(d100_group_admission, "_read_journal", racing_read)
        return snapshot

    monkeypatch.setattr(d100_group_admission, "_read_journal", racing_read)
    preview = d100_group_admission.project_d100_memory_entry_preview(
        PROPOSAL,
        journal,
        repository=ROOT,
    )

    descriptor = preview["semantic_body"]["journal"]
    assert descriptor["record_count"] == 5
    assert descriptor["head_decision_hash"] == records[-1]["decision_hash"]
    assert descriptor["file_sha256"] == sha256_bytes(original_content)
    assert descriptor["file_sha256"] != sha256_bytes(journal.read_bytes())
    assert correction["decision_hash"] != descriptor["head_decision_hash"]


@pytest.mark.parametrize(
    "tamper",
    ["truncated", "blank", "edited", "reordered", "noncanonical"],
)
def test_d100_journal_tampering_fails_closed(tmp_path: Path, tamper: str) -> None:
    journal = tmp_path / "decisions.jsonl"
    first = _record(
        journal,
        "platform-emulation-matrix-gap",
        "approve",
        "tamper-one",
        None,
    )
    _record(
        journal,
        "request-context-propagation-gap",
        "reject",
        "tamper-two",
        first["decision_hash"],
    )
    lines = journal.read_text(encoding="utf-8").splitlines()
    if tamper == "truncated":
        journal.write_text("\n".join(lines), encoding="utf-8")
    elif tamper == "blank":
        journal.write_text(f"{lines[0]}\n\n{lines[1]}\n", encoding="utf-8")
    elif tamper == "edited":
        payload = json.loads(lines[0])
        payload["rationale"] = "Edited after review."
        journal.write_text(
            canonical_json(payload) + "\n" + lines[1] + "\n",
            encoding="utf-8",
        )
    elif tamper == "reordered":
        journal.write_text(f"{lines[1]}\n{lines[0]}\n", encoding="utf-8")
    else:
        payload = json.loads(lines[0])
        journal.write_text(
            json.dumps(payload, ensure_ascii=False) + "\n" + lines[1] + "\n",
            encoding="utf-8",
        )

    with pytest.raises(ContractError):
        d100_group_admission.validate_d100_decision_journal(
            PROPOSAL,
            journal,
            repository=ROOT,
        )


def test_d100_external_anchor_detects_complete_suffix_deletion(tmp_path: Path) -> None:
    journal = tmp_path / "decisions.jsonl"
    records = _complete_journal(journal)
    correction = _record(
        journal,
        "platform-emulation-matrix-gap",
        "reject",
        "suffix-correction",
        records[-1]["decision_hash"],
    )
    lines = journal.read_text(encoding="utf-8").splitlines()
    journal.write_bytes(("\n".join(lines[:-1]) + "\n").encode("utf-8"))

    structural = d100_group_admission.validate_d100_decision_journal(
        PROPOSAL,
        journal,
        repository=ROOT,
    )
    assert structural["complete_group_decisions"] is True
    assert structural["external_head_anchor_validated"] is False
    with pytest.raises(ContractError, match="external journal anchor does not match"):
        d100_group_admission.project_d100_memory_entry_preview(
            PROPOSAL,
            journal,
            repository=ROOT,
            expected_head=correction["decision_hash"],
            expected_record_count=6,
        )


def test_d100_schema_rejects_unknown_fields(tmp_path: Path) -> None:
    journal = tmp_path / "decisions.jsonl"
    record = _record(
        journal,
        "platform-emulation-matrix-gap",
        "approve",
        "strict-schema",
        None,
    )
    record["unexpected"] = True
    with pytest.raises(ValidationError):
        D100GroupDecisionRecord.model_validate(record)


def test_d100_clean_repository_needs_no_runtime_or_legacy_store(tmp_path: Path) -> None:
    repository, proposal_path = _copy_portable_repository(tmp_path)
    journal = tmp_path / "portable-decisions.jsonl"
    assert not (repository / ".patchloop").exists()
    tail = None
    proposal = D099ReviewProposal.model_validate_json(proposal_path.read_text(encoding="utf-8"))
    for index, group in enumerate(proposal.semantic_body.groups, start=1):
        decision = "approve" if group.disposition == "candidate" else "continue_hold"
        record = _record(
            journal,
            group.semantic_group_id,
            decision,
            f"portable-{index}",
            tail,
            proposal_path=proposal_path,
            repository=repository,
        )
        tail = record["decision_hash"]

    preview = d100_group_admission.project_d100_memory_entry_preview(
        proposal_path,
        journal,
        repository=repository,
    )
    assert len(preview["semantic_body"]["entries"]) == 3
    assert not (repository / ".patchloop").exists()


def test_d100_rejects_proposal_swap_after_exact_validation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, proposal_path = _copy_portable_repository(tmp_path)
    original_validate = d100_group_admission.validate_d099_review_proposal

    def validate_then_swap(*args: object, **kwargs: object) -> dict:
        result = original_validate(*args, **kwargs)
        proposal_path.write_bytes(proposal_path.read_bytes() + b" ")
        return result

    monkeypatch.setattr(
        d100_group_admission,
        "validate_d099_review_proposal",
        validate_then_swap,
    )
    with pytest.raises(ContractError, match="changed during validation"):
        d100_group_admission.d100_mechanism_status(
            proposal_path,
            repository=repository,
        )


def test_d100_does_not_touch_d099_or_historical_memory(tmp_path: Path) -> None:
    proposal_before = (PROPOSAL.stat().st_mtime_ns, sha256_bytes(PROPOSAL.read_bytes()))
    memory_root = ROOT / ".patchloop" / "memory"
    memory_before = _tree_fingerprint(memory_root)
    journal = tmp_path / "decisions.jsonl"
    _complete_journal(journal)
    d100_group_admission.project_d100_memory_entry_preview(
        PROPOSAL,
        journal,
        repository=ROOT,
    )

    assert (PROPOSAL.stat().st_mtime_ns, sha256_bytes(PROPOSAL.read_bytes())) == proposal_before
    assert _tree_fingerprint(memory_root) == memory_before


def test_d100_cli_status_record_validate_and_preview(tmp_path: Path) -> None:
    runner = CliRunner()
    status = runner.invoke(app, ["memory", "d100-status", str(PROPOSAL)])
    assert status.exit_code == 0, status.output
    assert json.loads(status.stdout)["production_human_decision_records"] == 0

    journal = tmp_path / "decisions.jsonl"
    tail = "none"
    for index, group in enumerate(_proposal().semantic_body.groups, start=1):
        decision = "approve" if group.disposition == "candidate" else "continue_hold"
        result = runner.invoke(
            app,
            [
                "memory",
                "record-d100-decision",
                str(PROPOSAL),
                "--journal",
                str(journal),
                "--group",
                group.semantic_group_id,
                "--decision",
                decision,
                "--reviewer-kind",
                "synthetic",
                "--reviewer",
                "synthetic-cli-reviewer",
                "--rationale",
                "Synthetic public-only CLI contract test decision.",
                "--action-id",
                f"cli-{index}",
                "--expected-tail",
                tail,
            ],
        )
        assert result.exit_code == 0, result.output
        tail = json.loads(result.stdout)["decision_hash"]

    validated = runner.invoke(
        app,
        [
            "memory",
            "validate-d100-decisions",
            str(PROPOSAL),
            "--journal",
            str(journal),
            "--expected-head",
            tail,
            "--expected-record-count",
            "5",
        ],
    )
    assert validated.exit_code == 0, validated.output
    assert json.loads(validated.stdout)["complete_group_decisions"] is True
    assert json.loads(validated.stdout)["external_head_anchor_validated"] is True
    preview = runner.invoke(
        app,
        [
            "memory",
            "preview-d100-entries",
            str(PROPOSAL),
            "--journal",
            str(journal),
            "--expected-head",
            tail,
            "--expected-record-count",
            "5",
        ],
    )
    assert preview.exit_code == 0, preview.output
    assert len(json.loads(preview.stdout)["semantic_body"]["entries"]) == 3
    assert (
        json.loads(preview.stdout)["semantic_body"]["authority"][
            "external_head_anchor_validated"
        ]
        is True
    )


def test_d100_source_gate_exactly_rebuilds_current_implementation() -> None:
    expected = d100_group_admission.build_d100_source_gate(repository=ROOT)
    actual = json.loads(SOURCE_GATE.read_text(encoding="utf-8"))

    assert canonical_json(actual) == canonical_json(expected)
    validated = d100_group_admission.validate_d100_source_gate(
        SOURCE_GATE,
        repository=ROOT,
    )
    assert validated["source_gate_validation"] == "pass"
    assert (
        validated["schema_version"]
        == "memory-group-review-source-gate-validation-result-d100-v1"
    )
    assert validated["production_human_decision_records"] == 0
    assert validated["memory_index_built"] is False

    bindings = {
        item["semantic_group_id"]: (
            item["semantic_group_fingerprint"],
            item["proposed_rule_hash"],
        )
        for item in actual["semantic_body"]["group_bindings"]
    }
    assert bindings == {
        "platform-emulation-matrix-gap": (
            "sha256:2680ffacfdfe654288f9c9d9bfc399c2b07d2d0b52ee06b2201ebb6e72d2a45f",
            "sha256:913b11118e2db81c48497eaf1ec14e25ebb557f0e64cb8097bd2422d89ca0e64",
        ),
        "request-context-propagation-gap": (
            "sha256:195b37a651d16037d49d389c3ec30c9cdaa658239cb66e108cb25ed5464d6471",
            "sha256:6c2ba21aea2a2de3dd9cb25209d8d3a6709dd939e3f82eea8b0906677794a046",
        ),
        "interrupt-lifecycle-unresolved": (
            "sha256:bfd05d53347d867efccc0fa091408a2c36dc57695ae5ff99d16b76fefdbb1244",
            None,
        ),
        "diagnostic-contract-unresolved": (
            "sha256:b8238774a1399211fc7eb8d2452894e901f8b8291969641704a38c969a07fe8c",
            None,
        ),
        "exception-origin-state-conflation": (
            "sha256:e70e64a6af47eac96d9fe70943d6ea869a84757da4475edd5b972fb0654561fb",
            "sha256:330e5a73bc8f9815b6a2cec4d2c9bf3b3ba589e2addd2ec96d72288089710b6f",
        ),
    }


def test_d100_source_gate_rejects_rehashed_authority_tamper(tmp_path: Path) -> None:
    payload = json.loads(SOURCE_GATE.read_text(encoding="utf-8"))
    payload["semantic_body"]["authority"]["production_human_decision_records"] = 1
    body_hash = sha256_text(canonical_json(payload["semantic_body"]))
    payload["semantic_body_hash"] = body_hash
    payload["gate_id"] = f"d100_{body_hash.removeprefix('sha256:')}"
    tampered = tmp_path / "tampered-source-gate.json"
    tampered.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(ContractError):
        d100_group_admission.validate_d100_source_gate(
            tampered,
            repository=ROOT,
        )


def test_d100_source_gate_rejects_noncanonical_bytes(tmp_path: Path) -> None:
    modified = tmp_path / "noncanonical-source-gate.json"
    modified.write_bytes(SOURCE_GATE.read_bytes() + b"\n")

    with pytest.raises(ContractError, match="does not match the implementation"):
        d100_group_admission.validate_d100_source_gate(
            modified,
            repository=ROOT,
        )


def test_d100_cli_validates_source_gate() -> None:
    result = CliRunner().invoke(
        app,
        ["memory", "validate-d100-source-gate", str(SOURCE_GATE)],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["source_gate_validation"] == "pass"
