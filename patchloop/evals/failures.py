"""Deterministic failure taxonomy from verifier-visible outcomes."""

from __future__ import annotations

import uuid
from pathlib import Path

from patchloop.contracts import (
    FailureRecord,
    Phase,
    RunOutcomeKind,
    RunResult,
    VerdictState,
)
from patchloop.errors import ContractError
from patchloop.runtime import runtime_root


def _failure_root(root: str | Path | None) -> Path:
    return Path(root) if root is not None else runtime_root()


def classify_failure(
    result: RunResult,
    split: str,
    *,
    root: str | Path | None = None,
    phase: Phase = Phase.REVIEW,
) -> FailureRecord | None:
    """Persist one failure record without copying private check identities.

    Verifier check IDs can reveal hidden evaluator structure. The classifier
    therefore records only the public check category and terminal state. The
    full verifier result remains linked by its opaque result/artifact IDs.
    """

    verifier_states = result.verdicts.model_dump().values()
    if (
        result.scope_compliant_success
        or result.outcome_kind == RunOutcomeKind.INFRASTRUCTURE_ERROR
        or (
            result.evaluation_status == "completed"
            and any(
                state in {VerdictState.ERROR, VerdictState.NOT_RUN}
                for state in verifier_states
            )
        )
    ):
        return None
    if result.outcome_kind == RunOutcomeKind.AGENT_FAILURE:
        cause = "agent-execution-failure"
    elif result.verdicts.scope_policy == VerdictState.FAIL:
        cause = "scope-policy-violation"
    elif result.verdicts.regression_tests == VerdictState.FAIL:
        cause = "regression-test-failure"
    elif result.verdicts.hidden_tests == VerdictState.FAIL:
        cause = "hidden-acceptance-failure"
    else:
        cause = "unknown-evaluation-failure"
    symptoms = [
        f"{item.check_type}:{item.state.value}"
        for item in result.verifier_results
        if item.state != VerdictState.PASS
    ]
    if result.outcome_kind == RunOutcomeKind.AGENT_FAILURE:
        error_type = (result.terminal_error or {}).get("type", "unknown")
        symptoms = [f"agent-error:{error_type}"]
    failure_identity = f"{result.run_id}:{cause}:{phase.value}"
    record = FailureRecord(
        failure_id=f"fail_{uuid.uuid5(uuid.NAMESPACE_URL, failure_identity).hex}",
        run_id=result.run_id,
        primary_cause=cause,
        observed_symptoms=symptoms,
        phase=phase,
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
    directory = _failure_root(root) / "failures" / split
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{record.failure_id}.json"
    content = record.model_dump_json(indent=2)
    if path.exists():
        existing = FailureRecord.model_validate_json(path.read_text(encoding="utf-8"))
        if existing != record:
            raise ContractError(f"failure record identity conflict: {record.failure_id}")
    else:
        path.write_text(content, encoding="utf-8")
    return record


def failure_path(
    split: str,
    failure_id: str,
    *,
    root: str | Path | None = None,
) -> Path:
    return _failure_root(root) / "failures" / split / f"{failure_id}.json"
