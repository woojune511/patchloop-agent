from __future__ import annotations

import json
from pathlib import Path

import pytest

from patchloop.agent.model import (
    SYSTEM_PROMPT_V7,
    MockModelAdapter,
    ModelTurn,
    RequestedTool,
)
from patchloop.agent.review import (
    normalize_public_issue_text,
    public_review_contract_content_hash,
    public_review_coverage_target_id,
    public_review_requirement_id,
)
from patchloop.agent.runner import AgentRunner
from patchloop.agent.tools import TOOL_SCHEMAS_V4, TOOL_SCHEMAS_V5
from patchloop.contracts import (
    Artifact,
    EventType,
    Phase,
    PublicReviewContract,
    ToolResult,
)
from patchloop.errors import ContractError, RecoveryError
from patchloop.runtime import build_manifest
from patchloop.task_loader import load_task_package
from patchloop.util import sha256_bytes, utc_now

TASK = Path("tasks/smoke/csv-quoted-newline/public.yaml")


def _smoke_v2_contract(package) -> PublicReviewContract:
    excerpt = normalize_public_issue_text(package.public.issue.description)
    requirement_id = public_review_requirement_id(excerpt)
    target_specs = [
        {
            "description": "Inspect the current CSV parser entry path.",
            "evidence_kind": "current_diff_inspection",
            "path": "mini_data_utils/csvlite.py",
            "anchor": "def parse_rows",
        },
        {
            "description": "Validate the registered CSV regression check.",
            "evidence_kind": "passing_validation",
            "check_ids": ["existing-unit-tests"],
        },
    ]
    coverage_targets = []
    for spec in target_specs:
        target = {
            "coverage_target_id": public_review_coverage_target_id(
                requirement_id,
                **spec,
            ),
            **spec,
        }
        coverage_targets.append(target)
    payload = {
        "schema_version": "public-review-contract-v2",
        "task_id": package.public.task_id,
        "task_version": package.public.task_version,
        "public_spec_hash": package.public_spec_hash,
        "requirements": [
            {
                "requirement_id": requirement_id,
                "source": "issue.description",
                "source_excerpt": excerpt,
                "coverage_targets": coverage_targets,
            }
        ],
    }
    payload["content_hash"] = public_review_contract_content_hash(payload)
    return PublicReviewContract.model_validate(payload)


def _v10_manifest(package, *, run_id: str) -> tuple[PublicReviewContract, object]:
    contract = _smoke_v2_contract(package)
    manifest = build_manifest(
        package,
        run_id=run_id,
        sandbox_backend="local",
        coverage_review_validation=True,
        public_review_contract=contract,
    )
    return contract, manifest


def _with_inspection_anchor(
    contract: PublicReviewContract,
    anchor: str,
) -> PublicReviewContract:
    payload = contract.model_dump(mode="json")
    target = payload["requirements"][0]["coverage_targets"][0]
    target["anchor"] = anchor
    target["coverage_target_id"] = public_review_coverage_target_id(
        payload["requirements"][0]["requirement_id"],
        description=target["description"],
        evidence_kind=target["evidence_kind"],
        path=target["path"],
        anchor=anchor,
    )
    payload["content_hash"] = public_review_contract_content_hash(payload)
    return PublicReviewContract.model_validate(payload)


def _smoke_multirequirement_v2_contract(package) -> PublicReviewContract:
    excerpts = [
        "A quoted CSV field containing a newline is emitted as two records.",
        "Preserve the public parse_rows(text) interface and existing behavior.",
    ]
    target_specs = [
        {
            "description": "Inspect the current CSV parser entry path.",
            "evidence_kind": "current_diff_inspection",
            "path": "mini_data_utils/csvlite.py",
            "anchor": "def parse_rows",
        },
        {
            "description": "Validate the registered CSV regression check.",
            "evidence_kind": "passing_validation",
            "check_ids": ["existing-unit-tests"],
        },
    ]
    requirements = []
    for excerpt, target_spec in zip(excerpts, target_specs, strict=True):
        requirement_id = public_review_requirement_id(excerpt)
        requirements.append(
            {
                "requirement_id": requirement_id,
                "source": "issue.description",
                "source_excerpt": excerpt,
                "coverage_targets": [
                    {
                        "coverage_target_id": (
                            public_review_coverage_target_id(
                                requirement_id,
                                **target_spec,
                            )
                        ),
                        **target_spec,
                    }
                ],
            }
        )
    payload = {
        "schema_version": "public-review-contract-v2",
        "task_id": package.public.task_id,
        "task_version": package.public.task_version,
        "public_spec_hash": package.public_spec_hash,
        "requirements": requirements,
    }
    payload["content_hash"] = public_review_contract_content_hash(payload)
    return PublicReviewContract.model_validate(payload)


def _as_v1_contract(contract: PublicReviewContract) -> PublicReviewContract:
    payload = contract.model_dump(mode="json")
    payload["schema_version"] = "public-review-contract-v1"
    for requirement in payload["requirements"]:
        requirement.pop("coverage_targets")
    payload["content_hash"] = public_review_contract_content_hash(payload)
    return PublicReviewContract.model_validate(payload)


def _review_arguments(
    context: str,
    contract: PublicReviewContract,
    *,
    complete: bool,
) -> dict:
    payload = json.loads(context)
    review_evidence = payload["review_evidence"]
    target_evidence = review_evidence["coverage_target_event_sequences"]
    target_rows = []
    requirement_sequences: list[int] = []
    statuses = []
    for target in contract.requirements[0].coverage_targets:
        sequences = list(target_evidence[target.coverage_target_id])
        status = "verified" if complete or sequences else "unverified"
        if status == "verified":
            assert sequences
        else:
            sequences = []
        statuses.append(status)
        for sequence in sequences:
            if sequence not in requirement_sequences:
                requirement_sequences.append(sequence)
        target_rows.append(
            {
                "coverage_target_id": target.coverage_target_id,
                "status": status,
                "evidence_event_sequences": sequences,
                "notes": (
                    "Current-diff target evidence is present."
                    if status == "verified"
                    else "Current-diff target evidence is still missing."
                ),
            }
        )
    requirement_status = (
        "verified"
        if all(status == "verified" for status in statuses)
        else (
            "unverified"
            if all(status == "unverified" for status in statuses)
            else "partially_verified"
        )
    )
    check_sequence = review_evidence["passing_check_event_sequences"][0]
    residual_risks = (
        []
        if requirement_status == "verified"
        else [
            {
                "requirement_ids": [
                    contract.requirements[0].requirement_id
                ],
                "risk": "A declared public coverage target remains unverified.",
                "mitigation": "Inspect that target and repeat the final review.",
            }
        ]
    )
    return {
        "requirements": [
            {
                "requirement_id": contract.requirements[0].requirement_id,
                "status": requirement_status,
                "evidence_event_sequences": requirement_sequences,
                "notes": "Status is rolled up from the public target rows.",
            }
        ],
        "coverage_targets": target_rows,
        "targeted_validation": [
            {
                "kind": "registered_check",
                "event_sequence": check_sequence,
                "outcome": "passed",
                "notes": "The registered public check passed on this diff.",
            }
        ],
        "residual_risks": residual_risks,
    }


def test_v5_schema_adds_target_rows_without_mutating_v4() -> None:
    review_v4 = next(item for item in TOOL_SCHEMAS_V4 if item["name"] == "review_task")
    review_v5 = next(item for item in TOOL_SCHEMAS_V5 if item["name"] == "review_task")

    assert "coverage_targets" not in review_v4["parameters"]["properties"]
    assert review_v4["parameters"]["required"] == [
        "requirements",
        "targeted_validation",
        "residual_risks",
    ]
    assert review_v5["parameters"]["required"] == [
        "requirements",
        "coverage_targets",
        "targeted_validation",
        "residual_risks",
    ]
    target_schema = review_v5["parameters"]["properties"]["coverage_targets"]
    assert target_schema["items"]["additionalProperties"] is False
    assert target_schema["items"]["required"] == [
        "coverage_target_id",
        "status",
        "evidence_event_sequences",
        "notes",
    ]


def test_v10_manifest_is_mock_only_and_contract_versioned() -> None:
    package = load_task_package(TASK.parent)
    contract, manifest = _v10_manifest(package, run_id="run_v10_manifest")

    assert manifest.tool_schema_version == "v5"
    assert manifest.context_policy_version == "phase-evidence-v10"
    assert manifest.public_review_contract == contract
    with pytest.raises(ContractError, match="offline-only"):
        build_manifest(
            package,
            provider="openai",
            model_id="gpt-test",
            coverage_review_validation=True,
            public_review_contract=contract,
        )
    v1_payload = contract.model_dump(mode="json")
    v1_payload["schema_version"] = "public-review-contract-v1"
    for requirement in v1_payload["requirements"]:
        requirement.pop("coverage_targets")
    v1_payload["content_hash"] = public_review_contract_content_hash(v1_payload)
    v1_contract = PublicReviewContract.model_validate(v1_payload)
    with pytest.raises(ValueError, match="version conflicts"):
        build_manifest(
            package,
            coverage_review_validation=True,
            public_review_contract=v1_contract,
        )


def test_v10_mock_run_records_complete_target_bound_review(
    tmp_path,
    monkeypatch,
) -> None:
    package = load_task_package(TASK.parent)
    contract, manifest = _v10_manifest(
        package,
        run_id="run_v10_complete_review",
    )
    monkeypatch.setattr(
        "patchloop.agent.runner.DockerSandbox.available",
        lambda: False,
    )
    runner = AgentRunner(tmp_path / "runtime")

    result = runner.start(TASK, model="mock", manifest=manifest)
    events = runner.state.list_events(manifest.run_id)

    assert result["scope_compliant_success"] is True
    review_event = next(
        event
        for event in events
        if event.type == EventType.TOOL_SUCCEEDED
        and event.payload.get("tool") == "review_task"
    )
    assert review_event.payload["review_schema_version"] == "task-review-v3"
    assert review_event.payload["coverage_complete"] is True
    assert review_event.payload["unresolved_coverage_target_ids"] == []
    descriptor = Artifact.model_validate(review_event.payload["review_artifact"])
    document = json.loads(runner.artifacts.read_bytes(descriptor))
    target_ids = [
        target.coverage_target_id
        for target in contract.requirements[0].coverage_targets
    ]
    assert document["public_review_coverage"] == {
        "schema_version": "public-review-coverage-v1",
        "authoritative_coverage_target_ids": target_ids,
        "verified_coverage_target_ids": target_ids,
        "unresolved_coverage_target_ids": [],
        "coverage_complete": True,
        "ready_for_submission": True,
        "deterministic_correctness_claimed": False,
    }
    started = next(event for event in events if event.type == EventType.RUN_STARTED)
    runtime_descriptor = Artifact.model_validate(
        started.payload["runtime_contract_artifact"]
    )
    runtime_document = json.loads(
        runner.artifacts.read_bytes(runtime_descriptor)
    )
    assert runtime_document == {
        "schema_version": "corrective-runtime-contract-v4",
        "system_prompt": SYSTEM_PROMPT_V7,
        "tools": TOOL_SCHEMAS_V5,
        "tool_schema_version": "v5",
        "context_policy_version": "phase-evidence-v10",
    }
    base_descriptor = Artifact.model_validate(
        started.payload["public_review_base_provenance_artifact"]
    )
    base_document = json.loads(runner.artifacts.read_bytes(base_descriptor))
    base_bytes = runner.workspaces.read_base_file(
        runner.root / "workspaces" / manifest.run_id / "repo",
        "mini_data_utils/csvlite.py",
    )
    assert base_document == {
        "schema_version": "public-review-base-provenance-v1",
        "task_id": package.public.task_id,
        "task_version": package.public.task_version,
        "public_spec_hash": package.public_spec_hash,
        "public_review_contract_content_hash": contract.content_hash,
        "repository_url": package.public.repository.url,
        "base_commit": package.public.repository.base_commit,
        "inspection_targets": [
            {
                "coverage_target_id": (
                    contract.requirements[0]
                    .coverage_targets[0]
                    .coverage_target_id
                ),
                "path": "mini_data_utils/csvlite.py",
                "anchor": "def parse_rows",
                "base_file_content_hash": sha256_bytes(base_bytes),
                "found": True,
            }
        ],
    }
    assert (
        runner._prepare_public_review_base_provenance(
            manifest=manifest,
            task=package.public,
            workspace=(
                runner.root / "workspaces" / manifest.run_id / "repo"
            ),
        )
        == base_descriptor
    )


def test_v10_solution_only_anchor_is_rejected_before_context_or_model(
    tmp_path,
    monkeypatch,
) -> None:
    package = load_task_package(TASK.parent)
    contract = _with_inspection_anchor(
        _smoke_v2_contract(package),
        'return list(csv.reader(io.StringIO(text, newline="")))',
    )
    manifest = build_manifest(
        package,
        run_id="run_v10_solution_only_anchor",
        sandbox_backend="local",
        coverage_review_validation=True,
        public_review_contract=contract,
    )
    monkeypatch.setattr(
        "patchloop.agent.runner.DockerSandbox.available",
        lambda: False,
    )
    runner = AgentRunner(tmp_path / "runtime")

    with pytest.raises(
        ContractError,
        match="absent from the public base revision",
    ):
        runner.start(TASK, model="mock", manifest=manifest)

    events = runner.state.list_events(manifest.run_id)
    assert not any(
        event.type in {EventType.CONTEXT_BUILT, EventType.MODEL_CALLED}
        for event in events
    )
    assert not any(event.type == EventType.RUN_STARTED for event in events)


def test_v10_resume_revalidates_and_reuses_base_provenance(
    tmp_path,
    monkeypatch,
) -> None:
    package = load_task_package(TASK.parent)
    _contract, manifest = _v10_manifest(
        package,
        run_id="run_v10_base_provenance_resume",
    )
    monkeypatch.setattr(
        "patchloop.agent.runner.DockerSandbox.available",
        lambda: False,
    )
    runner = AgentRunner(tmp_path / "runtime")
    original_checkpoint = runner._checkpoint
    interrupted = False

    def interrupt_first_checkpoint(*args, **kwargs):
        nonlocal interrupted
        if not interrupted:
            interrupted = True
            raise SystemExit("interrupt before first context")
        return original_checkpoint(*args, **kwargs)

    monkeypatch.setattr(runner, "_checkpoint", interrupt_first_checkpoint)
    with pytest.raises(SystemExit, match="before first context"):
        runner.start(TASK, model="mock", manifest=manifest)
    before = runner.state.list_events(manifest.run_id)
    started = next(
        event for event in before if event.type == EventType.RUN_STARTED
    )
    original_descriptor = started.payload[
        "public_review_base_provenance_artifact"
    ]
    assert not any(
        event.type in {EventType.CONTEXT_BUILT, EventType.MODEL_CALLED}
        for event in before
    )

    resumed_runner = AgentRunner(runner.root)
    result = resumed_runner.resume(manifest.run_id)
    after = resumed_runner.state.list_events(manifest.run_id)

    assert result["scope_compliant_success"] is True
    assert sum(
        event.type == EventType.RUN_STARTED for event in after
    ) == 1
    assert next(
        event for event in after if event.type == EventType.RUN_STARTED
    ).payload["public_review_base_provenance_artifact"] == original_descriptor


def test_v10_reordered_exact_once_rows_are_stored_in_contract_order(
    tmp_path,
    monkeypatch,
) -> None:
    package = load_task_package(TASK.parent)
    contract = _smoke_multirequirement_v2_contract(package)
    manifest = build_manifest(
        package,
        run_id="run_v10_reordered_review_rows",
        sandbox_backend="local",
        coverage_review_validation=True,
        public_review_contract=contract,
    )
    monkeypatch.setattr(
        "patchloop.agent.runner.DockerSandbox.available",
        lambda: False,
    )

    class ReorderedReviewAdapter(MockModelAdapter):
        def next_turn(self, context, tools):
            turn = super().next_turn(context, tools)
            calls = []
            for call in turn.tool_calls:
                if call.name != "review_task":
                    calls.append(call)
                    continue
                arguments = dict(call.arguments)
                arguments["requirements"] = list(
                    reversed(arguments["requirements"])
                )
                arguments["coverage_targets"] = list(
                    reversed(arguments["coverage_targets"])
                )
                calls.append(
                    RequestedTool(
                        call.name,
                        call.action_id,
                        arguments,
                    )
                )
            return ModelTurn(
                text=turn.text,
                tool_calls=calls,
                done=turn.done,
            )

    adapter = ReorderedReviewAdapter(
        package.public.task_id,
        structured_review=True,
    )
    runner = AgentRunner(tmp_path / "runtime")
    monkeypatch.setattr(
        runner,
        "_model_adapter",
        lambda *_args, **_kwargs: adapter,
    )

    result = runner.start(TASK, model="mock", manifest=manifest)
    events = runner.state.list_events(manifest.run_id)
    review_event = next(
        event
        for event in events
        if event.type == EventType.TOOL_SUCCEEDED
        and event.payload.get("tool") == "review_task"
    )
    descriptor = Artifact.model_validate(review_event.payload["review_artifact"])
    document = json.loads(runner.artifacts.read_bytes(descriptor))
    authoritative_requirement_ids = [
        requirement.requirement_id
        for requirement in contract.requirements
    ]
    authoritative_target_ids = [
        target.coverage_target_id
        for requirement in contract.requirements
        for target in requirement.coverage_targets
    ]
    assert authoritative_target_ids != sorted(authoritative_target_ids)

    assert result["scope_compliant_success"] is True
    assert [
        item["requirement_id"] for item in document["requirements"]
    ] == authoritative_requirement_ids
    assert [
        item["coverage_target_id"] for item in document["coverage_targets"]
    ] == authoritative_target_ids
    assert sum(
        event.type == EventType.SUBMISSION_ACCEPTED
        for event in events
    ) == 1

    tampered_document = json.loads(json.dumps(document))
    tampered_document["coverage_targets"] = list(
        reversed(tampered_document["coverage_targets"])
    )
    tampered_artifact = runner.artifacts.put_json(tampered_document)
    finish_call = next(
        event
        for event in events
        if event.type == EventType.TOOL_CALLED
        and event.payload.get("tool") == "finish_task"
    )
    durable_finish = runner.state.get_action_result(
        manifest.run_id,
        finish_call.correlation_id,
        finish_call.payload["input_hash"],
    )
    assert durable_finish is not None
    tampered_review_event = runner.state.append_event(
        manifest.run_id,
        EventType.TOOL_SUCCEEDED,
        actor="tool-gateway",
        correlation_id="tampered-review-order",
        payload={
            "tool": "review_task",
            "review_artifact": tampered_artifact.model_dump(mode="json"),
            "review_content_hash": tampered_artifact.content_hash,
            "source_get_diff_sequence": durable_finish.output[
                "source_get_diff_sequence"
            ],
            "coverage_target_count": len(authoritative_target_ids),
            "coverage_complete": True,
            "verified_coverage_target_ids": authoritative_target_ids,
            "unresolved_coverage_target_ids": [],
        },
    )
    tampered_finish = durable_finish.model_copy(
        update={
            "output": {
                **durable_finish.output,
                "source_task_review_sequence": tampered_review_event.sequence,
                "task_review_artifact": tampered_artifact.model_dump(
                    mode="json"
                ),
                "task_review_content_hash": tampered_artifact.content_hash,
            }
        }
    )
    with pytest.raises(
        RecoveryError,
        match="coverage|provenance is inconsistent",
    ):
        runner._reconcile_finish_task_lifecycle(
            manifest.run_id,
            finish_call.correlation_id,
            finish_call.payload["input_hash"],
            tampered_finish,
        )


@pytest.mark.parametrize("tool_schema_version", ["v3", "v4", "v5"])
def test_structured_durable_accepted_finish_without_review_provenance_fails_closed(
    tmp_path,
    tool_schema_version,
) -> None:
    package = load_task_package(TASK.parent)
    v2_contract = _smoke_multirequirement_v2_contract(package)
    if tool_schema_version == "v3":
        manifest = build_manifest(
            package,
            run_id="run_v3_missing_durable_review",
            self_validation=True,
        )
    elif tool_schema_version == "v4":
        manifest = build_manifest(
            package,
            run_id="run_v4_missing_durable_review",
            review_evidence_validation=True,
            public_review_contract=_as_v1_contract(v2_contract),
        )
    else:
        manifest = build_manifest(
            package,
            run_id="run_v5_missing_durable_review",
            coverage_review_validation=True,
            public_review_contract=v2_contract,
        )
    runner = AgentRunner(tmp_path / tool_schema_version)
    runner.state.create_run(manifest)
    now = utc_now()
    durable_result = ToolResult(
        action_id="finish-without-review",
        status="succeeded",
        started_at=now,
        finished_at=now,
        output={
            "submission_attempt_number": 1,
            "worktree_diff_hash": "sha256:" + ("a" * 64),
            "accepted_for_evaluation": True,
            "source_get_diff_sequence": 1,
            "request_artifact_id": "artifact-request",
        },
    )

    with pytest.raises(
        RecoveryError,
        match="incomplete review provenance",
    ):
        runner._reconcile_finish_task_lifecycle(
            manifest.run_id,
            durable_result.action_id,
            "sha256:" + ("b" * 64),
            durable_result,
        )


def test_partial_v10_review_is_preserved_remediated_and_not_submitted(
    tmp_path,
    monkeypatch,
) -> None:
    package = load_task_package(TASK.parent)
    contract, manifest = _v10_manifest(
        package,
        run_id="run_v10_partial_review",
    )
    monkeypatch.setattr(
        "patchloop.agent.runner.DockerSandbox.available",
        lambda: False,
    )

    class PartialThenCorrectAdapter(MockModelAdapter):
        def __init__(self) -> None:
            super().__init__(package.public.task_id)
            self.stage = 0

        def next_turn(self, context, tools):
            counts = {
                name: self.completed_tools.count(name)
                for name in set(self.completed_tools)
            }
            if counts.get("get_diff", 0) == 0:
                return super().next_turn(context, tools)
            if self.stage == 0:
                self.stage = 1
                return ModelTurn(
                    tool_calls=[
                        RequestedTool(
                            "review_task",
                            "v10-partial-review",
                            _review_arguments(
                                context,
                                contract,
                                complete=False,
                            ),
                        )
                    ]
                )
            if self.stage == 1:
                self.stage = 2
                return ModelTurn(
                    tool_calls=[
                        RequestedTool("finish_task", "v10-early-finish", {})
                    ]
                )
            if self.stage == 2:
                self.stage = 3
                return ModelTurn(
                    tool_calls=[
                        RequestedTool(
                            "read_file",
                            "v10-remediation-read",
                            {
                                "path": "mini_data_utils/csvlite.py",
                                "start_line": 1,
                                "end_line": 200,
                            },
                        )
                    ]
                )
            if self.stage == 3:
                self.stage = 4
                return ModelTurn(
                    tool_calls=[
                        RequestedTool("get_diff", "v10-remediation-diff", {})
                    ]
                )
            if self.stage == 4:
                self.stage = 5
                return ModelTurn(
                    tool_calls=[
                        RequestedTool(
                            "review_task",
                            "v10-complete-review",
                            _review_arguments(
                                context,
                                contract,
                                complete=True,
                            ),
                        )
                    ]
                )
            return ModelTurn(
                tool_calls=[
                    RequestedTool("finish_task", "v10-final-finish", {})
                ]
            )

    adapter = PartialThenCorrectAdapter()
    runner = AgentRunner(tmp_path / "runtime")
    monkeypatch.setattr(
        runner,
        "_model_adapter",
        lambda *_args, **_kwargs: adapter,
    )

    result = runner.start(TASK, model="mock", manifest=manifest)
    events = runner.state.list_events(manifest.run_id)

    assert result["scope_compliant_success"] is True
    review_events = [
        event
        for event in events
        if event.type == EventType.TOOL_SUCCEEDED
        and event.payload.get("tool") == "review_task"
    ]
    assert [event.payload["coverage_complete"] for event in review_events] == [
        False,
        True,
    ]
    partial = review_events[0]
    assert partial.payload["unresolved_coverage_target_ids"]
    corrective_transition = next(
        event
        for event in events
        if event.sequence > partial.sequence
        and event.type == EventType.PHASE_CHANGED
    )
    assert corrective_transition.payload == {
        "from": Phase.REVIEW.value,
        "to": Phase.IMPLEMENT.value,
    }
    rejected = next(
        event
        for event in events
        if event.type == EventType.SUBMISSION_REJECTED
    )
    assert "public_review_coverage_incomplete" in rejected.payload[
        "missing_evidence"
    ]
    assert len(
        [
            event
            for event in events
            if event.type == EventType.SUBMISSION_ACCEPTED
        ]
    ) == 1
    assert runner.state.latest_checkpoint(manifest.run_id).phase == Phase.DONE
