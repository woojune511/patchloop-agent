"""Deterministic failure taxonomy from verifier-visible outcomes."""

from __future__ import annotations

import uuid
from pathlib import Path

from patchloop.contracts import FailureRecord, Phase, RunResult, VerdictState
from patchloop.runtime import runtime_root


def classify_failure(result: RunResult, split: str) -> FailureRecord | None:
    if result.scope_compliant_success:
        return None
    if result.verdicts.scope_policy == VerdictState.FAIL:
        cause = "scope-policy-violation"
    elif result.verdicts.regression_tests == VerdictState.FAIL:
        cause = "regression-test-failure"
    elif result.verdicts.hidden_tests == VerdictState.FAIL:
        cause = "hidden-acceptance-failure"
    elif any(value == VerdictState.ERROR for value in result.verdicts.model_dump().values()):
        cause = "verifier-infrastructure-error"
    else:
        cause = "unknown-evaluation-failure"
    symptoms = [
        f"{item.check_type}:{item.check_id}:{item.state.value}"
        for item in result.verifier_results
        if item.state != VerdictState.PASS
    ]
    record = FailureRecord(
        failure_id=f"fail_{uuid.uuid4().hex}",
        run_id=result.run_id,
        primary_cause=cause,
        observed_symptoms=symptoms,
        phase=Phase.REVIEW,
        recoverability="unknown",
        evidence=[
            {
                "verifier_result_id": item.verifier_result_id,
                "evidence_artifact_ids": item.evidence_artifact_ids,
            }
            for item in result.verifier_results
            if item.state != VerdictState.PASS
        ],
        confidence=1.0,
        classification_method="deterministic-verdict-priority-v1",
        review_status="unreviewed",
    )
    directory = runtime_root() / "failures" / split
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{record.failure_id}.json"
    path.write_text(record.model_dump_json(indent=2), encoding="utf-8")
    return record


def failure_path(split: str, failure_id: str) -> Path:
    return runtime_root() / "failures" / split / f"{failure_id}.json"
