from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from patchloop.contracts import FailureRecord, Phase
from patchloop.errors import ContractError
from patchloop.memory import review as memory_review
from patchloop.util import canonical_json, sha256_bytes, sha256_text


def _hash(character: str) -> str:
    return "sha256:" + (character * 64)


def _write_hashed_proposal(path: Path, payload: dict) -> None:
    unhashed = {key: value for key, value in payload.items() if key != "content_hash"}
    payload["content_hash"] = sha256_text(canonical_json(unhashed))
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _rule(pattern: str) -> dict:
    return {
        "failure_pattern": {
            "failure_class": "verification-failure",
            "phase": "REVIEW",
            "description": pattern,
        },
        "preconditions": ["The public control flow matches this failure pattern."],
        "diagnostic_evidence": ["Agent-visible evidence supports the causal assessment."],
        "recommended_actions": ["Recheck the complete public control-flow boundary."],
        "do_not_apply_when": ["The public control flow does not match the precondition."],
        "applicable_languages": ["python"],
        "confidence": 0.9,
    }


def _fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path, Path]:
    repository = tmp_path / "repo"
    runtime = tmp_path / "runtime"
    report_path = repository / "reports" / "campaign.json"
    proposal_path = repository / "reports" / "proposal.json"
    artifact_root = repository / "reports" / "artifacts"
    failure_root = runtime / "failures" / "dev-train"
    report_path.parent.mkdir(parents=True)
    artifact_root.mkdir(parents=True)
    failure_root.mkdir(parents=True)

    source_specs = [
        {
            "failure_id": "fail_one",
            "run_id": "run_one",
            "task_id": "task-one",
            "public_spec_hash": _hash("1"),
            "qualification_hash": _hash("a"),
            "source_evidence_hash": _hash("b"),
            "semantic_group_id": "group-structure",
            "disposition": "hold",
        },
        {
            "failure_id": "fail_two",
            "run_id": "run_two",
            "task_id": "task-two",
            "public_spec_hash": _hash("2"),
            "qualification_hash": _hash("c"),
            "source_evidence_hash": _hash("d"),
            "semantic_group_id": "group-exception-origin",
            "disposition": "candidate",
        },
        {
            "failure_id": "fail_three",
            "run_id": "run_three",
            "task_id": "task-two",
            "public_spec_hash": _hash("2"),
            "qualification_hash": _hash("e"),
            "source_evidence_hash": _hash("f"),
            "semantic_group_id": "group-exception-origin",
            "disposition": "candidate",
        },
    ]
    manifests: dict[str, SimpleNamespace] = {}
    sources: list[dict] = []
    portable_artifacts: list[dict] = []
    rows: list[dict] = []
    for index, spec in enumerate(source_specs, start=1):
        record = FailureRecord(
            failure_id=spec["failure_id"],
            run_id=spec["run_id"],
            primary_cause="hidden-acceptance-failure",
            phase=Phase.REVIEW,
            confidence=1,
            classification_method="test",
        )
        (failure_root / f"{record.failure_id}.json").write_text(
            record.model_dump_json(indent=2), encoding="utf-8"
        )
        manifests[record.run_id] = SimpleNamespace(
            task_id=spec["task_id"],
            task_version=1,
            public_spec_hash=spec["public_spec_hash"],
        )
        relative_patch = f"reports/artifacts/{record.run_id}.patch"
        patch_path = repository / relative_patch
        patch_path.write_text(f"public submitted patch {index}\n", encoding="utf-8")
        patch_hash = sha256_bytes(patch_path.read_bytes())
        portable_artifacts.append(
            {
                "role": "submitted-task-failure-diff",
                "run_id": record.run_id,
                "path": relative_patch,
                "sha256": patch_hash,
            }
        )
        sources.append(
            {
                **spec,
                "submitted_patch_path": relative_patch,
                "submitted_patch_sha256": patch_hash,
                "evidence_event_sequences": [1, 2, 3],
                "assessment": "Public trace evidence identifies a control-flow mismatch.",
                "causal_confidence": 0.9,
            }
        )
        rows.append(
            {
                "run_id": record.run_id,
                "task_id": spec["task_id"],
                "outcome_kind": "task_failure",
                "evaluation_reached": True,
                "qualified": True,
                "qualification_hash": spec["qualification_hash"],
                "source_evidence_hash": spec["source_evidence_hash"],
            }
        )

    excluded = [
        {"run_id": "run_budget_one", "reason": "exact_request_budget_exceeded"},
        {"run_id": "run_budget_two", "reason": "exact_request_budget_exceeded"},
    ]
    rows.extend(
        {
            "run_id": item["run_id"],
            "task_id": "budget-task",
            "outcome_kind": "agent_failure",
            "evaluation_reached": False,
            "terminal_reason": item["reason"],
        }
        for item in excluded
    )
    report = {
        "experiment_id": "campaign-v1",
        "execution_hash": _hash("9"),
        "campaign": {"suite_hash": _hash("8")},
        "runs": rows,
        "review_admission": {
            "task_failure_candidates": [spec["run_id"] for spec in source_specs],
            "budget_confounded_candidates": [item["run_id"] for item in excluded],
        },
        "portable_artifacts": portable_artifacts,
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    dataset_hash = _hash("7")
    proposal = {
        "schema_version": "memory-review-proposal-v1",
        "proposal_id": "proposal-test-v1",
        "producer": {
            "kind": "maintainer-assisted",
            "method": "test-public-trace-review-v1",
            "model_id": None,
            "response_artifact_hash": None,
        },
        "campaign": {
            "report_path": "reports/campaign.json",
            "report_sha256": sha256_bytes(report_path.read_bytes()),
            "experiment_id": "campaign-v1",
            "execution_hash": _hash("9"),
            "suite_hash": _hash("8"),
            "dataset_manifest_hash": dataset_hash,
        },
        "evidence_boundary": {
            "policy": "agent-visible-public-evidence-v1",
            "allowed_sources": ["public task", "agent-visible trace", "submitted patch"],
            "prohibited_sources_not_read": [
                "private task specification",
                "evaluator-only assertions",
                "reference solution",
            ],
            "generic_outcome_only": True,
        },
        "sources": sources,
        "groups": [
            {
                "semantic_group_id": "group-structure",
                "representative_run_id": "run_one",
                "member_failure_ids": ["fail_one"],
                "member_run_ids": ["run_one"],
                "relation": "single",
                "merge_rationale": "One independently observed structural pattern.",
                "dedup_confidence": 0.9,
                "disposition": "hold",
                "rule": _rule("A helper insertion changes an existing method boundary."),
            },
            {
                "semantic_group_id": "group-exception-origin",
                "representative_run_id": "run_two",
                "member_failure_ids": ["fail_two", "fail_three"],
                "member_run_ids": ["run_two", "run_three"],
                "relation": "semantic-duplicate",
                "merge_rationale": "Two repetitions exhibit the same exception-origin pattern.",
                "dedup_confidence": 0.95,
                "disposition": "candidate",
                "rule": _rule("One handler conflates failures from two processing stages."),
            },
        ],
        "excluded_runs": excluded,
        "human_review_status": "pending",
    }
    _write_hashed_proposal(proposal_path, proposal)

    class FakeState:
        def __init__(self, _: Path) -> None:
            pass

        def get_manifest(self, run_id: str) -> SimpleNamespace:
            return manifests[run_id]

        def list_events(self, run_id: str) -> list[SimpleNamespace]:
            assert run_id in manifests
            return [SimpleNamespace(sequence=sequence) for sequence in range(1, 11)]

    provenance = {
        spec["failure_id"]: (
            "memory-development",
            dataset_hash,
            spec["qualification_hash"],
            spec["source_evidence_hash"],
        )
        for spec in source_specs
    }
    monkeypatch.setattr(memory_review, "StateStore", FakeState)
    monkeypatch.setattr(
        memory_review,
        "require_frozen_dataset",
        lambda _: (SimpleNamespace(dataset_id="test"), dataset_hash, Path("manifest")),
    )
    monkeypatch.setattr(
        memory_review,
        "_require_memory_source",
        lambda record, **_: provenance[record.failure_id],
    )
    return proposal_path, repository, runtime


def test_validate_review_proposal_is_read_only_and_deduplicated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    proposal_path, repository, runtime = _fixture(tmp_path, monkeypatch)

    result = memory_review.validate_review_proposal(
        proposal_path,
        root=runtime,
        repository=repository,
    )

    assert result["source_count"] == 3
    assert result["semantic_group_count"] == 2
    assert result["producer_kind"] == "maintainer-assisted"
    assert result["candidate_group_count"] == 1
    assert result["hold_group_count"] == 1
    assert result["excluded_run_count"] == 2
    assert result["human_review_status"] == "pending"
    assert result["review_history_written"] is False
    assert not list((runtime / "failures").rglob("*.review-history.jsonl"))
    assert not (runtime / "memory").exists()


def test_validate_review_proposal_rejects_non_exact_candidate_coverage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    proposal_path, repository, runtime = _fixture(tmp_path, monkeypatch)
    proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
    report_path = repository / proposal["campaign"]["report_path"]
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["review_admission"]["task_failure_candidates"].append("run_missing")
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    proposal["campaign"]["report_sha256"] = sha256_bytes(report_path.read_bytes())
    _write_hashed_proposal(proposal_path, proposal)

    with pytest.raises(ContractError, match="exactly cover task failure"):
        memory_review.validate_review_proposal(
            proposal_path,
            root=runtime,
            repository=repository,
        )


def test_validate_review_proposal_rejects_group_membership_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    proposal_path, repository, runtime = _fixture(tmp_path, monkeypatch)
    proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
    proposal["groups"][1]["member_failure_ids"] = ["fail_two", "fail_one"]
    _write_hashed_proposal(proposal_path, proposal)

    with pytest.raises(ContractError, match="group failure membership mismatch"):
        memory_review.validate_review_proposal(
            proposal_path,
            root=runtime,
            repository=repository,
        )


@pytest.mark.parametrize(
    "leaking_text",
    [
        "diff --git a/module.py b/module.py",
        "Consult reference.patch for the exact solution.",
        "```python\ndef leaked_answer():\n    return True\n```",
        ".patchloop-hidden/tests/test_acceptance.py",
        "OPENAI_API_KEY=sk-proj-exampleSecretValue123456789",
    ],
)
def test_validate_review_proposal_rejects_leak_or_code_markers_without_echoing(
    leaking_text: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proposal_path, repository, runtime = _fixture(tmp_path, monkeypatch)
    proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
    proposal["sources"][0]["assessment"] = leaking_text
    _write_hashed_proposal(proposal_path, proposal)

    with pytest.raises(ContractError) as captured:
        memory_review.validate_review_proposal(
            proposal_path,
            root=runtime,
            repository=repository,
        )
    assert str(captured.value) == "memory review proposal leak scan failed"
    assert leaking_text not in str(captured.value)


def test_validate_review_proposal_recomputes_portable_patch_hash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    proposal_path, repository, runtime = _fixture(tmp_path, monkeypatch)
    proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
    patch_path = repository / proposal["sources"][0]["submitted_patch_path"]
    patch_path.write_text("changed after proposal\n", encoding="utf-8")

    with pytest.raises(ContractError, match="portable patch hash mismatch"):
        memory_review.validate_review_proposal(
            proposal_path,
            root=runtime,
            repository=repository,
        )


def test_validate_review_proposal_rejects_content_hash_tamper(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    proposal_path, repository, runtime = _fixture(tmp_path, monkeypatch)
    proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
    proposal["proposal_id"] = "changed-without-rehashing"
    proposal_path.write_text(json.dumps(proposal, indent=2), encoding="utf-8")

    with pytest.raises(ContractError, match="content hash mismatch"):
        memory_review.validate_review_proposal(
            proposal_path,
            root=runtime,
            repository=repository,
        )


def test_validate_review_proposal_rejects_unbound_model_self_review_claim(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    proposal_path, repository, runtime = _fixture(tmp_path, monkeypatch)
    proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
    proposal["producer"]["kind"] = "model-self-review"
    _write_hashed_proposal(proposal_path, proposal)

    with pytest.raises(ContractError, match="proposal validation failed"):
        memory_review.validate_review_proposal(
            proposal_path,
            root=runtime,
            repository=repository,
        )
