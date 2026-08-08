from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from pydantic import ValidationError
from typer.testing import CliRunner

from patchloop.cli import app
from patchloop.contracts import D099ReviewProposal
from patchloop.errors import ContractError
from patchloop.memory import d099_review
from patchloop.memory.review import validate_review_proposal
from patchloop.util import canonical_json, sha256_bytes, sha256_text

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL = (
    ROOT / "reports" / "memory-development" / "d099-public-evidence-review-dedup-proposal.json"
)
RUNTIME = ROOT / ".patchloop"


def _load_proposal(path: Path = PROPOSAL) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _rehash(payload: dict) -> None:
    body_hash = sha256_text(canonical_json(payload["semantic_body"]))
    payload["semantic_body_hash"] = body_hash
    payload["proposal_id"] = f"d099_{body_hash.removeprefix('sha256:')}"


def _write_payload(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


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


def _state_fingerprint() -> dict[str, tuple[int, int, str] | None]:
    result: dict[str, tuple[int, int, str] | None] = {}
    for suffix in ("", "-wal", "-shm"):
        path = Path(f"{RUNTIME / 'state.sqlite3'}{suffix}")
        if not path.exists():
            result[suffix or "database"] = None
            continue
        stat = path.stat()
        result[suffix or "database"] = (
            stat.st_size,
            stat.st_mtime_ns,
            sha256_bytes(path.read_bytes()),
        )
    return result


def test_d099_exact_portable_proposal_has_non_admitting_partition() -> None:
    result = d099_review.validate_d099_review_proposal(PROPOSAL, repository=ROOT)

    assert result["review_source_count"] == 9
    assert result["semantic_group_count"] == 5
    assert (result["candidate_group_count"], result["candidate_source_count"]) == (3, 6)
    assert (result["hold_group_count"], result["hold_source_count"]) == (2, 3)
    assert result["selected_public_event_refs"] == 74
    assert result["raw_evidence_validation"] == "not_requested"
    assert result["human_admission_status"] == "pending"
    assert result["admitted_memory_rule_count"] == 0
    assert result["d099_review_history_written"] is False
    assert result["memory_admission_unlocked"] is False
    assert result["d099_memory_index_built"] is False
    assert result["d099_memory_index_frozen"] is False
    assert result["historical_memory_artifacts_modified"] is False
    assert result["core_campaign_unlocked"] is False


def test_d099_group_membership_and_dispositions_are_exact() -> None:
    proposal = D099ReviewProposal.model_validate(_load_proposal())
    groups = {group.semantic_group_id: group for group in proposal.semantic_body.groups}

    assert list(groups) == [group["semantic_group_id"] for group in d099_review.GROUP_SPECS]
    assert {
        group_id: [(member.run_id, member.failure_record_id) for member in group.members]
        for group_id, group in groups.items()
    } == {
        group_id: list(members) for group_id, members in d099_review.EXPECTED_GROUP_MEMBERS.items()
    }
    assert {
        group.semantic_group_id for group in groups.values() if group.disposition == "candidate"
    } == {
        "platform-emulation-matrix-gap",
        "request-context-propagation-gap",
        "exception-origin-state-conflation",
    }
    assert {
        group.semantic_group_id for group in groups.values() if group.disposition == "hold"
    } == {"interrupt-lifecycle-unresolved", "diagnostic-contract-unresolved"}


def test_d099_clean_machine_validation_needs_no_runtime(tmp_path: Path) -> None:
    repository, proposal_path = _copy_portable_repository(tmp_path)
    assert not (repository / ".patchloop").exists()

    result = d099_review.validate_d099_review_proposal(
        proposal_path,
        repository=repository,
    )

    assert result["ok"] is True
    assert result["raw_evidence_validation"] == "not_requested"
    assert not (repository / ".patchloop").exists()


def test_d099_raw_audit_exactly_rebuilds_and_preserves_sqlite_bundle() -> None:
    before = _state_fingerprint()

    result = d099_review.validate_d099_review_proposal(
        PROPOSAL,
        repository=ROOT,
        root=RUNTIME,
        require_raw_evidence=True,
    )

    assert result["raw_evidence_validation"] == "pass"
    assert _state_fingerprint() == before


def test_d099_builder_exactly_rebuilds_checked_in_proposal() -> None:
    rebuilt = d099_review.build_d099_review_proposal(
        repo_root=ROOT,
        root=RUNTIME,
        materialize_patches=False,
    )
    assert canonical_json(rebuilt) == canonical_json(_load_proposal())


def test_d099_raw_requirement_does_not_silently_downgrade(tmp_path: Path) -> None:
    repository, proposal_path = _copy_portable_repository(tmp_path)

    with pytest.raises(ContractError, match="raw evidence was required"):
        d099_review.validate_d099_review_proposal(
            proposal_path,
            repository=repository,
            require_raw_evidence=True,
        )


def test_d099_rejects_d098_source_seal_tamper(tmp_path: Path) -> None:
    repository, proposal_path = _copy_portable_repository(tmp_path)
    source_report = repository / d099_review.SOURCE_REPORT_PATH
    source_report.write_bytes(source_report.read_bytes() + b"\n")

    with pytest.raises(ContractError, match="source seal byte count drifted"):
        d099_review.validate_d099_review_proposal(
            proposal_path,
            repository=repository,
        )


def test_d099_rejects_portable_patch_tamper(tmp_path: Path) -> None:
    repository, proposal_path = _copy_portable_repository(tmp_path)
    payload = _load_proposal(proposal_path)
    patch = repository / payload["semantic_body"]["sources"][0]["submitted_patch"]["path"]
    patch.write_bytes(patch.read_bytes() + b"\n")

    with pytest.raises(ContractError, match="portable submitted patch hash drifted"):
        d099_review.validate_d099_review_proposal(
            proposal_path,
            repository=repository,
        )


def test_d099_rejects_rehashed_semantic_tamper(tmp_path: Path) -> None:
    repository, proposal_path = _copy_portable_repository(tmp_path)
    payload = _load_proposal(proposal_path)
    payload["semantic_body"]["sources"][0]["assessment"] = "Changed public assessment."
    _rehash(payload)
    _write_payload(proposal_path, payload)

    with pytest.raises(ContractError, match="exact semantic body drifted"):
        d099_review.validate_d099_review_proposal(
            proposal_path,
            repository=repository,
        )


def test_d099_leak_scan_does_not_echo_leaking_text(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, proposal_path = _copy_portable_repository(tmp_path)
    payload = _load_proposal(proposal_path)
    leaking_text = "diff --git a/example.py b/example.py"
    payload["semantic_body"]["sources"][0]["assessment"] = leaking_text
    _rehash(payload)
    _write_payload(proposal_path, payload)
    monkeypatch.setattr(d099_review, "EXPECTED_SEMANTIC_BODY_HASH", None)
    monkeypatch.setattr(d099_review, "EXPECTED_PROPOSAL_FILE_SHA", None)
    monkeypatch.setattr(d099_review, "EXPECTED_PROPOSAL_BYTES", None)

    with pytest.raises(ContractError) as captured:
        d099_review.validate_d099_review_proposal(
            proposal_path,
            repository=repository,
        )
    assert str(captured.value) == "D-099 proposal text leak scan failed"
    assert leaking_text not in str(captured.value)


def test_d099_candidate_and_hold_payloads_are_mutually_exclusive() -> None:
    candidate = _load_proposal()
    candidate_group = candidate["semantic_body"]["groups"][0]
    candidate_group["proposed_rule"] = None
    candidate_group["unresolved_reason"] = "Improperly mixed hold state."
    candidate_group["next_review_actions"] = ["Review it."]
    with pytest.raises(ValidationError, match="candidate groups require only"):
        D099ReviewProposal.model_validate(candidate)

    hold = _load_proposal()
    hold_group = hold["semantic_body"]["groups"][2]
    hold_group["proposed_rule"] = hold["semantic_body"]["groups"][0]["proposed_rule"]
    with pytest.raises(ValidationError, match="hold groups require only"):
        D099ReviewProposal.model_validate(hold)


def test_d099_is_not_accepted_by_historical_v1_validator() -> None:
    with pytest.raises(ContractError, match="proposal validation failed"):
        validate_review_proposal(PROPOSAL, repository=ROOT, root=RUNTIME)


def test_d099_cli_reports_portable_validation() -> None:
    result = CliRunner().invoke(
        app,
        ["memory", "validate-d099-review", str(PROPOSAL)],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["review_source_count"] == 9
    assert payload["raw_evidence_validation"] == "not_requested"
