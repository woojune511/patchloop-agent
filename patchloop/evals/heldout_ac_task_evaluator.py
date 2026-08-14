"""Held-out A/C task/evaluator binding source with metadata-only discovery.

The metadata plan reads the sealed suite and dataset manifest, but never opens a
task package.  Materialization is a separate pure function: a future,
separately-authorized evaluator process must supply an already-loaded
``TaskPackage`` and its private marker set.  Marker values are never serialized.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from patchloop.agent.tools import TOOL_SCHEMAS_V2
from patchloop.contracts import (
    DatasetAdmissionState,
    DatasetRole,
    EvaluatorContractBinding,
    EvaluatorSafetyContract,
    TaskPackage,
    build_evaluator_contract_binding,
)
from patchloop.dataset import load_dataset_manifest
from patchloop.errors import ContractError
from patchloop.evals.evaluator_v2_source_qualification import (
    evaluator_v2_task_private_markers,
)
from patchloop.evals.heldout_ac_contracts import HeldoutACFrozenModel
from patchloop.evals.heldout_ac_suite import load_heldout_ac_suite
from patchloop.util import sha256_bytes, sha256_json
from patchloop.verifier.evidence import evaluator_v2_marker_set_hash
from patchloop.verifier.runtime_evidence import build_evaluator_safety_contract_v2

SUITE_PATH = Path("experiments/heldout-ac-suite-20260814-v1.yaml")
DATASET_PATH = Path("data/dataset-manifest.yaml")
PLAN_SCHEMA_VERSION = "heldout-ac-task-evaluator-binding-plan-v1"
MATERIALIZATION_SCHEMA_VERSION = "heldout-ac-task-evaluator-binding-v1"
PLAN_ID = "core-ac-fixed-bundle-heldout-task-evaluator-binding-20260814-v1"
SEALED_PLAN_CONTENT_HASH = "sha256:34edbad3f5a31f5d7e16ed2358905c195372a0d1f420c0ac03bd3be6a68668a8"


class HeldoutACTaskMetadataBinding(HeldoutACFrozenModel):
    task_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]+$")
    task_version: Literal[1]
    role: Literal["core-same-repo", "core-cross-repo"]
    task_path: str
    public_spec_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    private_spec_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    evaluator_image: str
    evaluator_image_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_metadata(self) -> HeldoutACTaskMetadataBinding:
        expected_prefix = (
            "tasks/same-repo-heldout/"
            if self.role == "core-same-repo"
            else "tasks/cross-repo-heldout/"
        )
        if self.task_path != f"{expected_prefix}{self.task_id}":
            raise ValueError("held-out task path and role differ")
        if not self.evaluator_image.endswith(f"@{self.evaluator_image_digest}"):
            raise ValueError("held-out evaluator image is not digest pinned")
        return self


class HeldoutACTaskEvaluatorBindingPlan(HeldoutACFrozenModel):
    schema_version: Literal[PLAN_SCHEMA_VERSION] = PLAN_SCHEMA_VERSION
    plan_id: Literal[PLAN_ID] = PLAN_ID
    status: Literal["metadata-bound-task-package-materialization-closed"] = (
        "metadata-bound-task-package-materialization-closed"
    )
    suite_id: Literal["core-ac-fixed-bundle-heldout-20260814-v1"]
    suite_content_hash: Literal[
        "sha256:1d023e8837e99889d76acf6f3a2d970261cb7aa4b3e978c84cef2ef5cf517aaa"
    ]
    dataset_manifest_file_sha256: Literal[
        "sha256:e8cf14ca9dabebcc03c3522e400dfcb79606541e9b11e59f49510ea5c40bebed"
    ]
    evaluator_version: Literal["v2"] = "v2"
    safety_contract_schema: Literal["evaluator-safety-contract-v2"] = "evaluator-safety-contract-v2"
    receipt_schema: Literal["evaluator-v2-evaluation-receipt-v1"] = (
        "evaluator-v2-evaluation-receipt-v1"
    )
    marker_profile: Literal["task-private-plus-run-secret-exact-v1"] = (
        "task-private-plus-run-secret-exact-v1"
    )
    tasks: tuple[HeldoutACTaskMetadataBinding, ...] = Field(min_length=12, max_length=12)
    task_package_files_opened: Literal[False] = False
    private_task_files_opened: Literal[False] = False
    task_evaluator_contracts_materialized: Literal[0] = 0
    provider_evaluator_agent_calls_authorized: Literal[False] = False
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_plan(self) -> HeldoutACTaskEvaluatorBindingPlan:
        identities = [(item.task_id, item.task_version) for item in self.tasks]
        if len(identities) != len(set(identities)):
            raise ValueError("held-out task metadata identities are duplicated")
        if sum(item.role == "core-same-repo" for item in self.tasks) != 6:
            raise ValueError("held-out task metadata must contain six same-repo tasks")
        if sum(item.role == "core-cross-repo" for item in self.tasks) != 6:
            raise ValueError("held-out task metadata must contain six cross-repo tasks")
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("held-out task/evaluator plan content hash mismatch")
        return self


class HeldoutACTaskEvaluatorBinding(HeldoutACFrozenModel):
    schema_version: Literal[MATERIALIZATION_SCHEMA_VERSION] = MATERIALIZATION_SCHEMA_VERSION
    plan_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    task: HeldoutACTaskMetadataBinding
    evaluator_source_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    private_marker_count: int = Field(ge=1)
    private_marker_set_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    safety_contract: EvaluatorSafetyContract
    evaluator_contract: EvaluatorContractBinding
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_binding(self) -> HeldoutACTaskEvaluatorBinding:
        identity = (
            self.task.task_id,
            self.task.task_version,
            self.task.public_spec_hash,
            self.task.private_spec_hash,
        )
        contract_identity = (
            self.evaluator_contract.task_id,
            self.evaluator_contract.task_version,
            self.evaluator_contract.public_spec_hash,
            self.evaluator_contract.private_spec_hash,
        )
        safety_identity = (
            self.safety_contract.task_id,
            self.safety_contract.task_version,
            self.safety_contract.public_spec_hash,
            self.safety_contract.private_spec_hash,
        )
        if identity != contract_identity or identity != safety_identity:
            raise ValueError("held-out evaluator contract belongs to another task")
        if (
            self.evaluator_contract.contract_hash != self.safety_contract.content_hash
            or self.evaluator_contract.evaluator_source_hash != self.evaluator_source_hash
        ):
            raise ValueError("held-out evaluator source or safety contract binding differs")
        secret_requirements = tuple(
            item
            for item in self.safety_contract.requirements
            if item.requirement_id == "secret_marker_control"
        )
        if len(secret_requirements) != 1 or (
            secret_requirements[0].policy_input_hash != self.private_marker_set_hash
            or secret_requirements[0].policy_input_count != self.private_marker_count
        ):
            raise ValueError("held-out private marker projection differs from its contract")
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("held-out task/evaluator binding content hash mismatch")
        return self


def _root(repository: str | Path | None) -> Path:
    return Path(repository or Path.cwd()).resolve()


def load_heldout_ac_task_evaluator_plan(
    *, repository: str | Path | None = None
) -> HeldoutACTaskEvaluatorBindingPlan:
    """Build the exact 12-task metadata plan without opening any task path."""

    root = _root(repository)
    suite = load_heldout_ac_suite(SUITE_PATH, repository=root)
    manifest, _semantic_hash, manifest_path = load_dataset_manifest(root / DATASET_PATH)
    manifest_bytes = manifest_path.read_bytes()
    if (
        len(manifest_bytes) != suite.dataset.manifest_file_bytes
        or sha256_bytes(manifest_bytes) != suite.dataset.manifest_file_sha256
    ):
        raise ContractError("held-out dataset manifest bytes differ from the sealed suite")
    by_id = {entry.task_id: entry for entry in manifest.tasks}
    tasks: list[HeldoutACTaskMetadataBinding] = []
    for selected in suite.tasks:
        entry = by_id.get(selected.task_id)
        if (
            entry is None
            or entry.role.value != selected.role
            or entry.admission_state != DatasetAdmissionState.ADMITTED
            or entry.role not in {DatasetRole.CORE_SAME_REPO, DatasetRole.CORE_CROSS_REPO}
            or entry.source.environment_image is None
        ):
            raise ContractError(f"held-out task metadata differs: {selected.task_id}")
        image = entry.source.environment_image
        digest = image.rsplit("@", 1)[-1]
        tasks.append(
            HeldoutACTaskMetadataBinding(
                task_id=entry.task_id,
                task_version=entry.task_version,
                role=entry.role.value,
                task_path=entry.path,
                public_spec_hash=entry.public_spec_hash,
                private_spec_hash=entry.private_spec_hash,
                evaluator_image=image,
                evaluator_image_digest=digest,
            )
        )
    body = {
        "schema_version": PLAN_SCHEMA_VERSION,
        "plan_id": PLAN_ID,
        "status": "metadata-bound-task-package-materialization-closed",
        "suite_id": suite.suite_id,
        "suite_content_hash": suite.content_hash,
        "dataset_manifest_file_sha256": sha256_bytes(manifest_bytes),
        "evaluator_version": "v2",
        "safety_contract_schema": "evaluator-safety-contract-v2",
        "receipt_schema": "evaluator-v2-evaluation-receipt-v1",
        "marker_profile": "task-private-plus-run-secret-exact-v1",
        "tasks": [item.model_dump(mode="json") for item in tasks],
        "task_package_files_opened": False,
        "private_task_files_opened": False,
        "task_evaluator_contracts_materialized": 0,
        "provider_evaluator_agent_calls_authorized": False,
    }
    return HeldoutACTaskEvaluatorBindingPlan(
        **{key: value for key, value in body.items() if key != "tasks"},
        tasks=tuple(tasks),
        content_hash=sha256_json(body),
    )


def materialize_heldout_ac_task_evaluator_binding(
    *,
    plan: HeldoutACTaskEvaluatorBindingPlan,
    expected_task: HeldoutACTaskMetadataBinding,
    package: TaskPackage,
    evaluator_source_hash: str,
    runtime_secret_markers: Sequence[bytes],
) -> HeldoutACTaskEvaluatorBinding:
    """Materialize one evaluator-v2 binding from already-authorized private inputs."""

    if plan.content_hash != SEALED_PLAN_CONTENT_HASH:
        raise ContractError("held-out task/evaluator plan is not the sealed metadata plan")
    if expected_task not in plan.tasks:
        raise ContractError("task is outside the held-out task/evaluator plan")
    package = TaskPackage.model_validate(package.model_dump(mode="json"))
    environment = package.environment
    package_identity = (
        package.public.task_id,
        package.public.task_version,
        package.public_spec_hash,
        package.private_spec_hash,
    )
    expected_identity = (
        expected_task.task_id,
        expected_task.task_version,
        expected_task.public_spec_hash,
        expected_task.private_spec_hash,
    )
    if (
        package_identity != expected_identity
        or environment is None
        or (
            environment.evaluator_image,
            environment.image_digest,
        )
        != (expected_task.evaluator_image, expected_task.evaluator_image_digest)
    ):
        raise ContractError("task package differs from the metadata-bound held-out task")
    base_markers = evaluator_v2_task_private_markers(package)
    secrets = tuple(runtime_secret_markers)
    if (
        not secrets
        or any(type(item) is not bytes or not item or len(item) > 16_384 for item in secrets)
        or len(secrets) != len(set(secrets))
        or set(secrets).intersection(base_markers)
    ):
        raise ContractError("held-out runtime secret marker set is invalid")
    markers = tuple(sorted((*base_markers, *secrets)))
    marker_hash = evaluator_v2_marker_set_hash(markers)
    contract = build_evaluator_safety_contract_v2(
        package=package,
        tool_schemas=TOOL_SCHEMAS_V2,
        private_markers=markers,
        contract_id=f"heldout_ac_evaluator_v2_{package.public.task_id.replace('-', '_')}",
    )
    binding = build_evaluator_contract_binding(
        contract,
        package,
        evaluator_source_hash=evaluator_source_hash,
    )
    body = {
        "schema_version": MATERIALIZATION_SCHEMA_VERSION,
        "plan_content_hash": plan.content_hash,
        "task": expected_task.model_dump(mode="json"),
        "evaluator_source_hash": evaluator_source_hash,
        "private_marker_count": len(markers),
        "private_marker_set_hash": marker_hash,
        "safety_contract": contract.model_dump(mode="json"),
        "evaluator_contract": binding.model_dump(mode="json"),
    }
    return HeldoutACTaskEvaluatorBinding(**body, content_hash=sha256_json(body))


__all__ = [
    "DATASET_PATH",
    "MATERIALIZATION_SCHEMA_VERSION",
    "PLAN_ID",
    "PLAN_SCHEMA_VERSION",
    "SEALED_PLAN_CONTENT_HASH",
    "SUITE_PATH",
    "HeldoutACTaskEvaluatorBinding",
    "HeldoutACTaskEvaluatorBindingPlan",
    "HeldoutACTaskMetadataBinding",
    "load_heldout_ac_task_evaluator_plan",
    "materialize_heldout_ac_task_evaluator_binding",
]
