from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from patchloop.agent.model import SYSTEM_PROMPT_V5
from patchloop.agent.review import load_public_review_contract
from patchloop.agent.runner import AgentRunner
from patchloop.agent.tools import TOOL_SCHEMAS_V4
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import (
    EventType,
    ExperimentPurpose,
    ExperimentRunContext,
    RunEvent,
)
from patchloop.evals.qualification import (
    _corrective_runtime_contract_evidence,
)
from patchloop.evals.runner import (
    _corrective_runtime_contract,
    _execution_hash,
    _pricing_contract,
    _pricing_contract_matches,
    _pricing_freshness_evidence,
    _pricing_freshness_passed,
    load_suite,
)
from patchloop.runtime import build_manifest
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json, sha256_text, utc_now

TASK = Path("tasks/dev-train/hf-hub-xet-endpoint-propagation")
REVIEW = Path(
    "experiments/review-contracts/hf-hub-xet-endpoint-propagation.yaml"
)


def _manifest(*, experiment: bool = False):
    package = load_task_package(TASK)
    contract = load_public_review_contract(
        REVIEW,
        task=package.public,
        public_spec_hash=package.public_spec_hash,
    )
    context = (
        ExperimentRunContext(
            experiment_id="corrective-provenance-test",
            purpose=(
                ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_CORRECTIVE_PILOT
            ),
            suite_hash="sha256:" + ("a" * 64),
            execution_hash="sha256:" + ("b" * 64),
            dataset_manifest_hash="sha256:" + ("c" * 64),
            schedule_seed=20260723,
            schedule_order=1,
            schedule_row_id="sha256:" + ("d" * 64),
            repetition=1,
        )
        if experiment
        else None
    )
    return build_manifest(
        package,
        run_id="run_corrective_provenance",
        corrective_validation=True,
        public_review_contract=contract,
        experiment_context=context,
    )


def _saturation_manifest():
    package = load_task_package(TASK)
    contract = load_public_review_contract(
        REVIEW,
        task=package.public,
        public_spec_hash=package.public_spec_hash,
    )
    return build_manifest(
        package,
        run_id="run_saturation_provenance",
        saturation_context_validation=True,
        public_review_contract=contract,
    )


def _runtime_event(tmp_path: Path, manifest, *, content=None) -> RunEvent:
    artifacts = ArtifactStore(tmp_path / "artifacts")
    artifact = artifacts.put_json(
        content
        or {
            "system_prompt": SYSTEM_PROMPT_V5,
            "tools": TOOL_SCHEMAS_V4,
            "tool_schema_version": "v4",
            "context_policy_version": "phase-evidence-v7",
        }
    )
    return RunEvent(
        event_id="evt_runtime_contract",
        run_id=manifest.run_id,
        sequence=1,
        type=EventType.RUN_STARTED,
        timestamp=utc_now(),
        actor="runner",
        payload={
            "task_id": manifest.task_id,
            "artifact_id": artifact.artifact_id,
            "artifact_path": artifact.path,
            "artifact_role": "runtime-contract",
            "runtime_contract_artifact": artifact.model_dump(mode="json"),
        },
    )


def test_corrective_runtime_semantics_accept_exact_cas_descriptor(
    tmp_path: Path,
) -> None:
    manifest = _manifest()
    event = _runtime_event(tmp_path, manifest)

    passed, details = _corrective_runtime_contract_evidence(
        root=tmp_path,
        manifest=manifest,
        events=[event],
    )

    assert passed is True
    assert details["cas_integrity_valid"] is True
    assert details["semantic_contract_valid"] is True


def test_saturation_runtime_semantics_accept_exact_v2_cas_descriptor(
    tmp_path: Path,
) -> None:
    manifest = _saturation_manifest()
    event = _runtime_event(
        tmp_path,
        manifest,
        content={
            "schema_version": "corrective-runtime-contract-v2",
            "system_prompt": SYSTEM_PROMPT_V5,
            "tools": TOOL_SCHEMAS_V4,
            "tool_schema_version": "v4",
            "context_policy_version": "phase-evidence-v8",
        },
    )

    passed, details = _corrective_runtime_contract_evidence(
        root=tmp_path,
        manifest=manifest,
        events=[event],
    )

    assert passed is True
    assert details["cas_integrity_valid"] is True
    assert details["semantic_contract_valid"] is True


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schema_version", "corrective-runtime-contract-v1"),
        ("context_policy_version", "phase-evidence-v7"),
    ],
)
def test_saturation_runtime_semantics_reject_v2_identity_drift(
    tmp_path: Path,
    field: str,
    value: str,
) -> None:
    manifest = _saturation_manifest()
    content = {
        "schema_version": "corrective-runtime-contract-v2",
        "system_prompt": SYSTEM_PROMPT_V5,
        "tools": TOOL_SCHEMAS_V4,
        "tool_schema_version": "v4",
        "context_policy_version": "phase-evidence-v8",
    }
    content[field] = value
    event = _runtime_event(tmp_path, manifest, content=content)

    passed, details = _corrective_runtime_contract_evidence(
        root=tmp_path,
        manifest=manifest,
        events=[event],
    )

    assert details["cas_integrity_valid"] is True
    assert details["semantic_contract_valid"] is False
    assert passed is False


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("actor", "model"),
        ("task_id", "another-task"),
        ("artifact_role", "context"),
        ("artifact_path", "wrong-path"),
    ],
)
def test_corrective_runtime_semantics_reject_event_identity_drift(
    tmp_path: Path,
    field: str,
    value: str,
) -> None:
    manifest = _manifest()
    event = _runtime_event(tmp_path, manifest)
    if field == "actor":
        event = event.model_copy(update={"actor": value})
    else:
        event = event.model_copy(
            update={"payload": {**event.payload, field: value}}
        )

    passed, _ = _corrective_runtime_contract_evidence(
        root=tmp_path,
        manifest=manifest,
        events=[event],
    )

    assert passed is False


def test_corrective_runtime_semantics_reject_missing_and_duplicate_start(
    tmp_path: Path,
) -> None:
    manifest = _manifest()
    event = _runtime_event(tmp_path, manifest)

    assert _corrective_runtime_contract_evidence(
        root=tmp_path,
        manifest=manifest,
        events=[],
    )[0] is False
    assert _corrective_runtime_contract_evidence(
        root=tmp_path,
        manifest=manifest,
        events=[event, event.model_copy(update={"event_id": "evt_duplicate"})],
    )[0] is False


@pytest.mark.parametrize(
    ("mutation", "value"),
    [
        ("system_prompt", "replacement prompt"),
        ("tools", []),
        ("tool_schema_version", "v3"),
        ("context_policy_version", "phase-evidence-v6"),
    ],
)
def test_corrective_runtime_semantics_reject_internally_valid_replacement_cas(
    tmp_path: Path,
    mutation: str,
    value: object,
) -> None:
    manifest = _manifest()
    content = {
        "system_prompt": SYSTEM_PROMPT_V5,
        "tools": TOOL_SCHEMAS_V4,
        "tool_schema_version": "v4",
        "context_policy_version": "phase-evidence-v7",
    }
    content[mutation] = value
    event = _runtime_event(tmp_path, manifest, content=content)

    passed, details = _corrective_runtime_contract_evidence(
        root=tmp_path,
        manifest=manifest,
        events=[event],
    )

    assert details["cas_integrity_valid"] is True
    assert details["semantic_contract_valid"] is False
    assert passed is False


def test_corrective_manifest_rejects_runtime_version_downgrade() -> None:
    manifest = _manifest(experiment=True)
    payload = manifest.model_dump(mode="json")
    payload.update(
        {
            "tool_schema_version": "v2",
            "context_policy_version": "phase-evidence-v5",
        }
    )

    with pytest.raises(ValidationError, match="corrective runtime"):
        type(manifest).model_validate(payload)


def test_pricing_freshness_uses_immutable_boundary_inclusively() -> None:
    suite = load_suite(
        "experiments/dev-no-memory-corrective-pilot-20260731-r1.yaml"
    )
    assert suite.pricing_verified_at is not None
    verified_at = suite.pricing_verified_at

    exact = _pricing_freshness_evidence(
        suite,
        boundary_at=verified_at + timedelta(hours=72),
    )
    stale = _pricing_freshness_evidence(
        suite,
        boundary_at=verified_at + timedelta(hours=72, microseconds=1),
    )
    future = _pricing_freshness_evidence(
        suite,
        boundary_at=verified_at - timedelta(microseconds=1),
    )

    assert _pricing_freshness_passed(exact) is True
    assert exact["age_seconds"] == 72 * 60 * 60
    assert _pricing_freshness_passed(stale) is False
    assert stale["within_maximum_age"] is False
    assert _pricing_freshness_passed(future) is False
    assert future["date_not_future"] is False


def test_corrective_pricing_metadata_and_reserves_are_recomputed() -> None:
    suite = load_suite(
        "experiments/dev-no-memory-corrective-pilot-20260731-r1.yaml"
    )
    assert suite.pricing_verified_at is not None
    pricing = _pricing_contract(
        suite,
        schedule_size=3,
        checked_at=suite.pricing_verified_at + timedelta(hours=1),
    )
    assert _pricing_contract_matches(
        suite,
        pricing,
        schedule_size=3,
    ) is True
    assert pricing["per_run_cost_reserve_usd"] == 4.1625
    assert pricing["budget_upper_bound_usd"] == 12.4875

    for field, value in (
        ("source_url", "https://example.invalid/pricing"),
        ("output_price_per_million_usd", 0.01),
        ("per_run_cost_reserve_usd", 0.01),
        ("budget_upper_bound_usd", 0.03),
    ):
        tampered = {**pricing, field: value}
        assert _pricing_contract_matches(
            suite,
            tampered,
            schedule_size=3,
        ) is False


def test_corrective_runtime_block_changes_execution_hash() -> None:
    suite = load_suite(
        "experiments/dev-no-memory-corrective-pilot-20260731-r1.yaml"
    )
    runtime_contract = _corrective_runtime_contract(
        suite,
        harness_git_commit="a" * 40,
    )
    assert runtime_contract is not None
    arguments = {
        "dataset": {"manifest_hash": suite.dataset_manifest_hash},
        "task_rows": [{"task": task} for task in suite.tasks],
        "schedule_hash": "sha256:" + ("e" * 64),
        "git_state": {"commit": "a" * 40},
        "docker_state": {"images": []},
        "openai_sdk": {"installed": True, "version": "test"},
        "pilot_qualification": {"qualification_hash": None},
    }
    approved_hash = _execution_hash(
        suite,
        runtime_contract=runtime_contract,
        **arguments,
    )
    changed = {
        **runtime_contract,
        "context_policy_version": "phase-evidence-v6",
    }

    assert _execution_hash(
        suite,
        runtime_contract=changed,
        **arguments,
    ) != approved_hash


def test_agent_boundary_matches_exact_corrective_runtime_plan(
    tmp_path: Path,
) -> None:
    manifest = _manifest(experiment=True)
    runtime_contract = {
        "schema_version": "corrective-runtime-contract-v1",
        "tool_schema_version": "v4",
        "context_policy_version": "phase-evidence-v7",
        "system_prompt_hash": sha256_text(SYSTEM_PROMPT_V5),
        "tool_schema_hash": sha256_text(canonical_json(TOOL_SCHEMAS_V4)),
        "harness_git_commit": manifest.harness_git_commit,
    }
    plan_path = tmp_path / "plan.json"
    plan_path.write_text("{}", encoding="utf-8")
    authorization = type("Authorization", (), {"plan_path": str(plan_path)})()

    plan_path.write_text(
        canonical_json({"runtime_contract": runtime_contract}),
        encoding="utf-8",
    )
    assert AgentRunner._live_plan_matches_manifest(
        manifest,
        authorization,
    ) is True

    runtime_contract["tool_schema_version"] = "v3"
    plan_path.write_text(
        canonical_json({"runtime_contract": runtime_contract}),
        encoding="utf-8",
    )
    assert AgentRunner._live_plan_matches_manifest(
        manifest,
        authorization,
    ) is False
