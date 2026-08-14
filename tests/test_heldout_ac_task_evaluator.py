from __future__ import annotations

import re
from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import ValidationError

from patchloop.contracts import TaskPackage, task_package_spec_hashes
from patchloop.errors import ContractError
from patchloop.evals.evaluator_v2_source_qualification import (
    evaluator_v2_task_private_markers,
)
from patchloop.evals.heldout_ac_task_evaluator import (
    SEALED_PLAN_CONTENT_HASH,
    HeldoutACTaskEvaluatorBindingPlan,
    HeldoutACTaskMetadataBinding,
    load_heldout_ac_task_evaluator_plan,
    materialize_heldout_ac_task_evaluator_binding,
)
from patchloop.task_loader import load_task_package
from patchloop.util import sha256_json

ROOT = Path(__file__).resolve().parents[1]
SOURCE_HASH = "sha256:" + "a" * 64


def _synthetic_package(task_id: str) -> TaskPackage:
    base = load_task_package(ROOT / "tasks/dev-validation/moto-query-scanned-count")
    public_payload = base.public.model_dump(mode="json")
    private_payload = base.private.model_dump(mode="json")
    public_payload["task_id"] = task_id
    private_payload["task_id"] = task_id
    public = type(base.public).model_validate(public_payload)
    private = type(base.private).model_validate(private_payload)
    public_hash, private_hash = task_package_spec_hashes(public, private)
    return TaskPackage(
        public=public,
        private=private,
        environment=base.environment,
        root=f"C:/synthetic/{task_id}",
        public_spec_hash=public_hash,
        private_spec_hash=private_hash,
    )


def _synthetic_plan() -> tuple[HeldoutACTaskEvaluatorBindingPlan, TaskPackage]:
    sealed = load_heldout_ac_task_evaluator_plan(repository=ROOT)
    first = sealed.tasks[0]
    package = _synthetic_package(first.task_id)
    assert package.environment is not None
    replacement = HeldoutACTaskMetadataBinding(
        task_id=first.task_id,
        task_version=1,
        role=first.role,
        task_path=first.task_path,
        public_spec_hash=package.public_spec_hash,
        private_spec_hash=package.private_spec_hash,
        evaluator_image=package.environment.evaluator_image,
        evaluator_image_digest=package.environment.image_digest,
    )
    body = sealed.model_dump(mode="json", exclude={"content_hash"})
    body["tasks"][0] = replacement.model_dump(mode="json")
    plan = HeldoutACTaskEvaluatorBindingPlan(
        **{key: value for key, value in body.items() if key != "tasks"},
        tasks=tuple(HeldoutACTaskMetadataBinding.model_validate(item) for item in body["tasks"]),
        content_hash=sha256_json(body),
    )
    return plan, package


def test_metadata_plan_binds_exact_12_without_materializing_private_contracts() -> None:
    plan = load_heldout_ac_task_evaluator_plan(repository=ROOT)

    assert len(plan.tasks) == 12
    assert sum(item.role == "core-same-repo" for item in plan.tasks) == 6
    assert sum(item.role == "core-cross-repo" for item in plan.tasks) == 6
    assert plan.task_package_files_opened is False
    assert plan.private_task_files_opened is False
    assert plan.task_evaluator_contracts_materialized == 0
    assert plan.provider_evaluator_agent_calls_authorized is False
    assert plan.content_hash == SEALED_PLAN_CONTENT_HASH


def test_metadata_loader_never_opens_a_task_path(monkeypatch: pytest.MonkeyPatch) -> None:
    opened: list[str] = []
    original_read_bytes = Path.read_bytes
    original_read_text = Path.read_text

    def read_bytes(path: Path, *args, **kwargs):
        opened.append(path.resolve().as_posix())
        return original_read_bytes(path, *args, **kwargs)

    def read_text(path: Path, *args, **kwargs):
        opened.append(path.resolve().as_posix())
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_bytes", read_bytes)
    monkeypatch.setattr(Path, "read_text", read_text)
    load_heldout_ac_task_evaluator_plan(repository=ROOT)

    assert opened
    assert all("/tasks/" not in path for path in opened)


def test_materialization_builds_a_real_v2_contract_without_serializing_markers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan, package = _synthetic_plan()
    monkeypatch.setattr(
        "patchloop.evals.heldout_ac_task_evaluator.SEALED_PLAN_CONTENT_HASH",
        plan.content_hash,
    )
    binding = materialize_heldout_ac_task_evaluator_binding(
        plan=plan,
        expected_task=plan.tasks[0],
        package=package,
        evaluator_source_hash=SOURCE_HASH,
        runtime_secret_markers=(b"synthetic-run-secret",),
    )

    assert binding.evaluator_contract.evaluator_source_hash == SOURCE_HASH
    assert binding.evaluator_contract.contract_hash == binding.safety_contract.content_hash
    assert binding.private_marker_count > 1
    serialized = binding.model_dump_json().encode("utf-8")
    expected_markers = (
        *evaluator_v2_task_private_markers(package),
        b"synthetic-run-secret",
    )
    assert all(marker not in serialized for marker in expected_markers)
    secret_requirement = next(
        item
        for item in binding.safety_contract.requirements
        if item.requirement_id == "secret_marker_control"
    )
    assert secret_requirement.policy_input_count == binding.private_marker_count
    assert secret_requirement.policy_input_hash == binding.private_marker_set_hash


def test_exact_12_task_contracts_use_opaque_check_identities_without_marker_collisions() -> None:
    plan = load_heldout_ac_task_evaluator_plan(repository=ROOT)
    covered: set[str] = set()

    for expected_task in plan.tasks:
        package = load_task_package(ROOT / expected_task.task_path)
        runtime_secret = f"runtime-secret-{expected_task.task_id}".encode()
        binding = materialize_heldout_ac_task_evaluator_binding(
            plan=plan,
            expected_task=expected_task,
            package=package,
            evaluator_source_hash=SOURCE_HASH,
            runtime_secret_markers=(runtime_secret,),
        )
        serialized_contract = binding.safety_contract.model_dump_json().encode("utf-8")
        private_markers = (
            *evaluator_v2_task_private_markers(package),
            runtime_secret,
        )

        assert all(marker not in serialized_contract for marker in private_markers)
        assert all(
            f"hidden:{check.id}".encode() not in serialized_contract
            for check in package.private.hidden_checks
        )
        sandbox_requirements = (
            requirement
            for requirement in binding.safety_contract.requirements
            if requirement.control in {"network", "sandbox"}
        )
        assert all(
            re.fullmatch(r"(?:hidden|regression):h_[0-9a-f]{64}", check_id)
            for requirement in sandbox_requirements
            for check_id in requirement.check_ids
        )
        covered.add(expected_task.task_id)

    assert len(covered) == 12
    assert {
        "dagster-subset-partition-definition-selection",
        "tox-dotted-version-factor-base-python",
    } <= covered


def test_materialization_fails_closed_on_package_or_marker_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan, package = _synthetic_plan()
    monkeypatch.setattr(
        "patchloop.evals.heldout_ac_task_evaluator.SEALED_PLAN_CONTENT_HASH",
        plan.content_hash,
    )
    wrong = deepcopy(package.model_dump(mode="json"))
    wrong["environment"]["image_digest"] = "sha256:" + "b" * 64
    wrong["environment"]["evaluator_image"] = (
        "docker.io/example/test@" + wrong["environment"]["image_digest"]
    )
    wrong_package = TaskPackage.model_validate(wrong)

    with pytest.raises(ContractError, match="metadata-bound"):
        materialize_heldout_ac_task_evaluator_binding(
            plan=plan,
            expected_task=plan.tasks[0],
            package=wrong_package,
            evaluator_source_hash=SOURCE_HASH,
            runtime_secret_markers=(b"synthetic-run-secret",),
        )
    with pytest.raises(ContractError, match="marker set"):
        materialize_heldout_ac_task_evaluator_binding(
            plan=plan,
            expected_task=plan.tasks[0],
            package=package,
            evaluator_source_hash=SOURCE_HASH,
            runtime_secret_markers=(),
        )


def test_materialization_rejects_a_rehashed_unsealed_plan() -> None:
    plan, package = _synthetic_plan()

    with pytest.raises(ContractError, match="sealed metadata plan"):
        materialize_heldout_ac_task_evaluator_binding(
            plan=plan,
            expected_task=plan.tasks[0],
            package=package,
            evaluator_source_hash=SOURCE_HASH,
            runtime_secret_markers=(b"synthetic-run-secret",),
        )


def test_binding_rejects_rehashed_marker_projection_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan, package = _synthetic_plan()
    monkeypatch.setattr(
        "patchloop.evals.heldout_ac_task_evaluator.SEALED_PLAN_CONTENT_HASH",
        plan.content_hash,
    )
    binding = materialize_heldout_ac_task_evaluator_binding(
        plan=plan,
        expected_task=plan.tasks[0],
        package=package,
        evaluator_source_hash=SOURCE_HASH,
        runtime_secret_markers=(b"synthetic-run-secret",),
    )
    payload = binding.model_dump(mode="json")
    payload["private_marker_count"] += 1
    payload["content_hash"] = sha256_json(
        {key: value for key, value in payload.items() if key != "content_hash"}
    )

    with pytest.raises(ValidationError, match="marker projection"):
        type(binding).model_validate(payload)
