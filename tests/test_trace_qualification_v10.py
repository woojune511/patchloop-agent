from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from patchloop.agent.review import (
    normalize_public_issue_text,
    public_review_contract_content_hash,
    public_review_coverage_target_id,
    public_review_requirement_id,
)
from patchloop.agent.runner import AgentRunner
from patchloop.contracts import (
    Artifact,
    EventType,
    PublicReviewContract,
    RunResult,
)
from patchloop.errors import RecoveryError
from patchloop.evals import qualification as qualification_module
from patchloop.evals.qualification import (
    calculate_source_evidence_hash,
    qualify_run,
)
from patchloop.runtime import build_manifest
from patchloop.sandbox.runner import DockerSandbox
from patchloop.task_loader import load_task_package

TASK_DIR = Path("tasks/smoke/csv-quoted-newline")
TASK = TASK_DIR / "public.yaml"


def _review_contract(*, version: int) -> PublicReviewContract:
    package = load_task_package(TASK_DIR)
    excerpt = normalize_public_issue_text(package.public.issue.description)
    requirement_id = public_review_requirement_id(excerpt)
    requirement: dict[str, Any] = {
        "requirement_id": requirement_id,
        "source": "issue.description",
        "source_excerpt": excerpt,
    }
    if version == 2:
        target_specs = [
            {
                "description": "Inspect the corrected parser return path.",
                "evidence_kind": "current_diff_inspection",
                "path": "mini_data_utils/csvlite.py",
                "anchor": "def parse_rows",
            },
            {
                "description": "Validate the public parser regression.",
                "evidence_kind": "passing_validation",
                "check_ids": ["existing-unit-tests"],
            },
        ]
        requirement["coverage_targets"] = [
            {
                "coverage_target_id": public_review_coverage_target_id(
                    requirement_id,
                    description=spec["description"],
                    evidence_kind=spec["evidence_kind"],
                    path=spec.get("path"),
                    anchor=spec.get("anchor"),
                    check_ids=spec.get("check_ids"),
                ),
                **spec,
            }
            for spec in target_specs
        ]
    payload = {
        "schema_version": f"public-review-contract-v{version}",
        "task_id": package.public.task_id,
        "task_version": package.public.task_version,
        "public_spec_hash": package.public_spec_hash,
        "requirements": [requirement],
    }
    payload["content_hash"] = public_review_contract_content_hash(payload)
    return PublicReviewContract.model_validate(payload)


@pytest.fixture(scope="module")
def v10_run(tmp_path_factory):
    package = load_task_package(TASK_DIR)
    root = tmp_path_factory.mktemp("v10-qualification") / "runtime"
    runner = AgentRunner(root)
    manifest = build_manifest(
        package,
        run_id="run_v10_trace_qualification",
        sandbox_backend="local",
        coverage_review_validation=True,
        public_review_contract=_review_contract(version=2),
    )
    original_available = DockerSandbox.available
    DockerSandbox.available = staticmethod(lambda: False)
    try:
        result = runner.start(TASK, model="mock", manifest=manifest)
    finally:
        DockerSandbox.available = staticmethod(original_available)
    return {
        "runner": runner,
        "root": root,
        "package": package,
        "manifest": manifest,
        "result": RunResult.model_validate(result),
        "events": runner.state.list_events(manifest.run_id),
    }


def _checks(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["check_id"]: item for item in payload["checks"]}


def _replace_review_document(
    case: dict[str, Any],
    mutate,
) -> list[Any]:
    runner = case["runner"]
    events = list(case["events"])
    index, review_event = next(
        (index, event)
        for index, event in enumerate(events)
        if event.type == EventType.TOOL_SUCCEEDED
        and event.payload.get("tool") == "review_task"
    )
    result_artifact = Artifact.model_validate(
        review_event.payload["result_artifact"]
    )
    result_document = json.loads(
        runner.artifacts.read_bytes(result_artifact).decode("utf-8")
    )
    review_document = copy.deepcopy(result_document["review"])
    mutate(review_document, result_document)
    review_artifact = runner.artifacts.put_json(review_document)
    result_document.update(
        {
            "review": review_document,
            "review_artifact": review_artifact.model_dump(mode="json"),
            "review_content_hash": review_artifact.content_hash,
        }
    )
    rewritten_result = runner.artifacts.put_json(result_document)
    payload = {
        **review_event.payload,
        "artifact_id": rewritten_result.artifact_id,
        "artifact_path": rewritten_result.path,
        "result_artifact": rewritten_result.model_dump(mode="json"),
        "review_artifact": review_artifact.model_dump(mode="json"),
        "review_content_hash": review_artifact.content_hash,
    }
    for field in (
        "coverage_complete",
        "verified_coverage_target_ids",
        "unresolved_coverage_target_ids",
    ):
        if field in result_document:
            payload[field] = result_document[field]
    events[index] = review_event.model_copy(update={"payload": payload})
    return events


def test_v10_positive_runner_artifact_passes_five_coverage_checks(
    v10_run,
    monkeypatch,
) -> None:
    qualification = qualify_run(
        v10_run["manifest"].run_id,
        task_dir=TASK_DIR,
        root=v10_run["root"],
        persist=False,
    )
    checks = _checks(qualification)

    assert {
        "public_coverage_contract",
        "coverage_decision_integrity",
        "coverage_submission_lifecycle",
        "coverage_recovery_contract",
        "coverage_terminal_contract",
    } <= checks.keys()
    assert all(
        checks[check_id]["passed"]
        for check_id in {
            "public_coverage_contract",
            "coverage_decision_integrity",
            "coverage_submission_lifecycle",
            "coverage_recovery_contract",
            "coverage_terminal_contract",
        }
    )
    assert checks["corrective_runtime_contract"]["passed"] is True
    assert checks["self_validation_lifecycle"]["passed"] is True
    assert checks["public_coverage_contract"]["details"][
        "base_provenance_valid"
    ] is True
    original_source_hash = calculate_source_evidence_hash(
        v10_run["manifest"].run_id,
        root=v10_run["root"],
        require_valid_plan=False,
    )
    monkeypatch.setattr(
        qualification_module,
        "_SOURCE_EVIDENCE_SCHEMA_VERSION_V10",
        "trace-source-evidence-v10-test-mutation",
    )
    assert (
        calculate_source_evidence_hash(
            v10_run["manifest"].run_id,
            root=v10_run["root"],
            require_valid_plan=False,
        )
        != original_source_hash
    )


@pytest.mark.parametrize("tamper", ["descriptor", "document"])
def test_v10_rejects_base_revision_provenance_tamper(
    v10_run,
    tamper: str,
) -> None:
    runner = v10_run["runner"]
    events = list(v10_run["events"])
    index, started = next(
        (index, event)
        for index, event in enumerate(events)
        if event.type == EventType.RUN_STARTED
    )
    descriptor = Artifact.model_validate(
        started.payload["public_review_base_provenance_artifact"]
    )
    if tamper == "descriptor":
        rewritten_descriptor = {
            **descriptor.model_dump(mode="json"),
            "content_hash": "sha256:" + ("0" * 64),
        }
    else:
        document = json.loads(
            runner.artifacts.read_bytes(descriptor).decode("utf-8")
        )
        document["inspection_targets"][0]["anchor"] = (
            'return list(csv.reader(io.StringIO(text, newline="")))'
        )
        rewritten_descriptor = runner.artifacts.put_json(document).model_dump(
            mode="json"
        )
    events[index] = started.model_copy(
        update={
            "payload": {
                **started.payload,
                "public_review_base_provenance_artifact": (
                    rewritten_descriptor
                ),
            }
        }
    )

    passed, details = (
        qualification_module._v10_public_coverage_contract_evidence(
            root=v10_run["root"],
            manifest=v10_run["manifest"],
            package=v10_run["package"],
            events=events,
        )
    )

    assert passed is False, details
    assert details["base_provenance_valid"] is False


@pytest.mark.parametrize(
    "tamper",
    ["status", "target", "evidence", "coverage_complete"],
)
def test_v10_rejects_self_consistent_review_semantic_tamper(
    v10_run,
    tamper: str,
) -> None:
    def mutate(review: dict[str, Any], result: dict[str, Any]) -> None:
        if tamper == "status":
            review["coverage_targets"][0]["status"] = "unverified"
        elif tamper == "target":
            review["coverage_targets"][0]["coverage_target_id"] = (
                "cov-000000000000"
            )
        elif tamper == "evidence":
            review["coverage_targets"][0]["evidence_event_sequences"] = []
        else:
            review["public_review_coverage"]["coverage_complete"] = False
            review["public_review_coverage"]["ready_for_submission"] = False
            result["coverage_complete"] = False
            result["public_review_coverage"] = review[
                "public_review_coverage"
            ]

    events = _replace_review_document(v10_run, mutate)
    passed, details = qualification_module._v10_coverage_decision_evidence(
        root=v10_run["root"],
        manifest=v10_run["manifest"],
        package=v10_run["package"],
        events=events,
        context_events=[
            event for event in events if event.type == EventType.CONTEXT_BUILT
        ],
    )

    assert passed is False, details
    assert details["failed_review_call_sequences"]


def test_v10_rejects_review_artifact_cas_tamper(v10_run) -> None:
    events = list(v10_run["events"])
    index, review_event = next(
        (index, event)
        for index, event in enumerate(events)
        if event.type == EventType.TOOL_SUCCEEDED
        and event.payload.get("tool") == "review_task"
    )
    descriptor = {
        **review_event.payload["review_artifact"],
        "content_hash": "sha256:" + ("0" * 64),
    }
    events[index] = review_event.model_copy(
        update={
            "payload": {
                **review_event.payload,
                "review_artifact": descriptor,
                "review_content_hash": descriptor["content_hash"],
            }
        }
    )

    passed, details = qualification_module._v10_coverage_decision_evidence(
        root=v10_run["root"],
        manifest=v10_run["manifest"],
        package=v10_run["package"],
        events=events,
        context_events=[
            event for event in events if event.type == EventType.CONTEXT_BUILT
        ],
    )

    assert passed is False, details
    assert details["failed_review_call_sequences"]


@pytest.mark.parametrize("tamper", ["targeted_validation", "residual_risk"])
def test_v10_rejects_supporting_review_row_tamper(
    v10_run,
    tamper: str,
) -> None:
    def mutate(review: dict[str, Any], result: dict[str, Any]) -> None:
        if tamper == "targeted_validation":
            review["targeted_validation"][0]["outcome"] = "failed"
        else:
            review["residual_risks"] = [
                {
                    "requirement_ids": ["req-000000000000"],
                    "risk": "A forged residual risk.",
                    "mitigation": "Ignore the public contract.",
                }
            ]
            result["residual_risk_count"] = 1

    events = _replace_review_document(v10_run, mutate)
    passed, details = qualification_module._v10_coverage_decision_evidence(
        root=v10_run["root"],
        manifest=v10_run["manifest"],
        package=v10_run["package"],
        events=events,
        context_events=[
            event for event in events if event.type == EventType.CONTEXT_BUILT
        ],
    )

    assert passed is False, details
    assert details["failed_review_call_sequences"]


def test_v10_rejects_result_cas_semantic_relabeling(v10_run) -> None:
    runner = v10_run["runner"]
    check_event = next(
        event
        for event in v10_run["events"]
        if event.type == EventType.TOOL_SUCCEEDED
        and event.payload.get("tool") == "run_check"
    )
    descriptor = Artifact.model_validate(check_event.payload["result_artifact"])
    document = json.loads(
        runner.artifacts.read_bytes(descriptor).decode("utf-8")
    )
    document["passed"] = False
    rewritten = runner.artifacts.put_json(document)
    relabelled = check_event.model_copy(
        update={
            "payload": {
                **check_event.payload,
                "artifact_id": rewritten.artifact_id,
                "artifact_path": rewritten.path,
                "result_artifact": rewritten.model_dump(mode="json"),
            }
        }
    )

    with pytest.raises(RecoveryError, match="run_check anchor conflicts"):
        qualification_module._v10_recompute_review_anchor(
            relabelled,
            artifact_store=runner.artifacts,
        )

    read_event = next(
        event
        for event in v10_run["events"]
        if event.type == EventType.TOOL_SUCCEEDED
        and event.payload.get("tool") == "read_file"
        and event.payload.get("worktree_diff_hash")
        == check_event.payload.get("worktree_diff_hash")
    )
    descriptor = Artifact.model_validate(read_event.payload["result_artifact"])
    document = json.loads(
        runner.artifacts.read_bytes(descriptor).decode("utf-8")
    )
    document["worktree_diff_hash"] = "sha256:" + ("f" * 64)
    rewritten = runner.artifacts.put_json(document)
    stale_read = read_event.model_copy(
        update={
            "payload": {
                **read_event.payload,
                "artifact_id": rewritten.artifact_id,
                "artifact_path": rewritten.path,
                "result_artifact": rewritten.model_dump(mode="json"),
            }
        }
    )

    with pytest.raises(RecoveryError, match="current-diff result"):
        qualification_module._v10_recompute_review_anchor(
            stale_read,
            artifact_store=runner.artifacts,
        )


def test_v10_generic_terminal_without_review_cannot_close_coverage_gate(
    v10_run,
) -> None:
    terminal = next(
        event
        for event in v10_run["events"]
        if event.type in {EventType.RUN_COMPLETED, EventType.RUN_FAILED}
    )
    events = [terminal]

    decision, decision_details = (
        qualification_module._v10_coverage_decision_evidence(
            root=v10_run["root"],
            manifest=v10_run["manifest"],
            package=v10_run["package"],
            events=events,
            context_events=[],
        )
    )
    submission, _ = qualification_module._v10_coverage_submission_evidence(
        root=v10_run["root"],
        manifest=v10_run["manifest"],
        events=events,
        context_events=[],
        result=None,
    )
    recovery, recovery_details = (
        qualification_module._v10_coverage_recovery_evidence(events)
    )
    terminal_ok, terminal_details = (
        qualification_module._v10_coverage_terminal_evidence(
            events=events,
            result=None,
        )
    )

    assert decision is False
    assert decision_details["coverage_complete_review_count"] == 0
    assert submission is False
    assert recovery is False
    assert recovery_details["nonvacuous"] is False
    assert terminal_ok is False
    assert terminal_details["coverage_complete_review_sequences"] == []


def test_v10_rejects_submission_provenance_tamper(v10_run) -> None:
    events = list(v10_run["events"])
    index, accepted = next(
        (index, event)
        for index, event in enumerate(events)
        if event.type == EventType.SUBMISSION_ACCEPTED
    )
    events[index] = accepted.model_copy(
        update={
            "payload": {
                **accepted.payload,
                "source_task_review_sequence": 1,
            }
        }
    )

    passed, details = qualification_module._v10_coverage_submission_evidence(
        root=v10_run["root"],
        manifest=v10_run["manifest"],
        events=events,
        context_events=[
            event for event in events if event.type == EventType.CONTEXT_BUILT
        ],
        result=v10_run["result"],
    )

    assert passed is False, details
    assert details["failed_accepted_sequences"] == [accepted.sequence]


def test_v10_source_branch_does_not_change_v9_hash_or_checks(
    tmp_path,
    monkeypatch,
) -> None:
    package = load_task_package(TASK_DIR)
    runner = AgentRunner(tmp_path / "runtime")
    manifest = build_manifest(
        package,
        run_id="run_v9_v10_isolation",
        sandbox_backend="local",
        review_evidence_validation=True,
        public_review_contract=_review_contract(version=1),
    )
    monkeypatch.setattr(DockerSandbox, "available", lambda: False)
    runner.start(TASK, model="mock", manifest=manifest)
    original_hash = calculate_source_evidence_hash(
        manifest.run_id,
        root=runner.root,
        require_valid_plan=False,
    )
    original = qualify_run(
        manifest.run_id,
        task_dir=TASK_DIR,
        root=runner.root,
        persist=False,
    )

    monkeypatch.setattr(
        qualification_module,
        "_SOURCE_EVIDENCE_SCHEMA_VERSION_V10",
        "trace-source-evidence-v10-test-mutation",
    )
    assert (
        calculate_source_evidence_hash(
            manifest.run_id,
            root=runner.root,
            require_valid_plan=False,
        )
        == original_hash
    )
    assert (
        qualify_run(
            manifest.run_id,
            task_dir=TASK_DIR,
            root=runner.root,
            persist=False,
        )
        == original
    )
    assert not {
        "public_coverage_contract",
        "coverage_decision_integrity",
        "coverage_submission_lifecycle",
        "coverage_recovery_contract",
        "coverage_terminal_contract",
    }.intersection(_checks(original))
