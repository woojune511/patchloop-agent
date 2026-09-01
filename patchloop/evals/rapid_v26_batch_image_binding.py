"""Exact R23 batch-image integration proof over the frozen R22 V25/V26 package.

Only the literal row-start/capability plumbing and R23 manifest admission below
may differ. Reversing those exact replacements must recover the old bytes;
agent policies, tasks, reviewed qualifications and stopped R22 stay immutable.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from patchloop.errors import RecoveryError
from patchloop.evals.rapid_public_development_v22 import _stable_json
from patchloop.evals.rapid_v26_package_binding import V26_RUNTIME_IDENTITY, _exact_file
from patchloop.util import ensure_within, sha256_bytes, sha256_json

R22_CANDIDATE_PATH = Path(
    "reports/rapid-development/artifacts/"
    "rapid-public-dev-anyio-v5-v26-reliability-ab-20260831-r22-candidate-v30.json"
)
R22_CANDIDATE_SHA256 = "sha256:f4df6803247a7afc5b0f563030b6ebe695e1023ba2826cf4005f63c7109fb2d6"
R22_RUNNER_BYTES = 358_447
R22_RUNNER_SHA256 = "sha256:687e7101ba67ac1fc6f7e791a5bfe1e563b3affe7a59decb7944be254bf9cce4"

RUNNER_REPLACEMENTS = (
    (
        """from patchloop.agent.completion_loop_successor import (
""",
        """from patchloop.agent.batch_image_authority import (
    IMAGE_ADMISSION_CONTRACT,
    BatchImageAuthorization,
    validate_row_batch_image,
)
from patchloop.agent.batch_image_authority import (
    POLICY_VERSION as BATCH_IMAGE_POLICY_VERSION,
)
from patchloop.agent.completion_loop_successor import (
""",
    ),
    (
        """class _BatchExecutionAuthorizationState:
    next_order: int = 1
""",
        """class _BatchExecutionAuthorizationState:
    next_order: int = 1
    image_admission_attempted: bool = False
    image_authorization: object | None = None
""",
    ),
    (
        """    _state: _BatchExecutionAuthorizationState
    _guard: object
""",
        """    _state: _BatchExecutionAuthorizationState
    _guard: object
    image_admission_policy: str | None = None
    image_admission_image: str | None = None
""",
    ),
    (
        """    _state: _RowExecutionAuthorizationState
    _guard: object
""",
        """    _state: _RowExecutionAuthorizationState
    _guard: object
    image_admission_policy: str | None = None
    _batch_state: _BatchExecutionAuthorizationState | None = None
""",
    ),
    (
        """    manifests: tuple[RunManifest, ...],
    live_authorization: LiveExecutionAuthorization | None = None,
) -> BatchExecutionAuthorization:""",
        """    manifests: tuple[RunManifest, ...],
    live_authorization: LiveExecutionAuthorization | None = None,
    image_admission_policy: str | None = None,
    image_admission_image: str | None = None,
) -> BatchExecutionAuthorization:""",
    ),
    (
        """    if not manifests:
        raise HarnessAdmissionError("batch execution authorization has no manifests")
""",
        r"""    if image_admission_policy not in {None, BATCH_IMAGE_POLICY_VERSION}:
        raise HarnessAdmissionError("batch image admission policy is unsupported")
    if (image_admission_policy is None and image_admission_image is not None) or (
        image_admission_policy is not None
        and (
            not isinstance(image_admission_image, str)
            or re.fullmatch(r"[^\s@]+@sha256:[0-9a-f]{64}", image_admission_image) is None
        )
    ):
        raise HarnessAdmissionError("batch image reference is invalid")
    if not manifests:
        raise HarnessAdmissionError("batch execution authorization has no manifests")
""",
    ),
    (
        """        if not unchanged:
            raise HarnessAdmissionError("live batch capability lacks its unchanged approved plan")
""",
        """        if not unchanged:
            raise HarnessAdmissionError("live batch capability lacks its unchanged approved plan")
        assert live_authorization is not None
        approved_plan = json.loads(Path(live_authorization.plan_path).read_bytes())
        expected_image_contract = (
            IMAGE_ADMISSION_CONTRACT if image_admission_policy is not None else None
        )
        if not _exact_typed_equal(
            approved_plan.get("image_admission_contract"), expected_image_contract
        ):
            raise HarnessAdmissionError("batch image policy differs from its approved plan")
        if image_admission_policy is not None:
            bindings = approved_plan.get("task_bindings")
            if not (
                isinstance(bindings, list)
                and len(bindings) == 1
                and isinstance(bindings[0], dict)
                and bindings[0].get("evaluator_image") == image_admission_image
                and bindings[0].get("evaluator_image_digest")
                == image_admission_image.rsplit("@", 1)[1]
            ):
                raise HarnessAdmissionError("batch image reference differs from its approved plan")
""",
    ),
    (
        """        _guard=_BATCH_EXECUTION_AUTHORIZATION_GUARD,
    )""",
        """        _guard=_BATCH_EXECUTION_AUTHORIZATION_GUARD,
        image_admission_policy=image_admission_policy,
        image_admission_image=image_admission_image,
    )""",
    ),
    (
        """        _guard=_ROW_EXECUTION_AUTHORIZATION_GUARD,
    )""",
        """        _guard=_ROW_EXECUTION_AUTHORIZATION_GUARD,
        image_admission_policy=batch.image_admission_policy,
        _batch_state=batch._state,
    )""",
    ),
    (
        """        row_execution_authorization: RowExecutionAuthorization | None = None,
        campaign_cost_reservation: (CampaignCostReservationAuthorization | None) = None,""",
        """        row_execution_authorization: RowExecutionAuthorization | None = None,
        batch_image_authorization: BatchImageAuthorization | None = None,
        campaign_cost_reservation: (CampaignCostReservationAuthorization | None) = None,""",
    ),
    (
        """        docker_sandbox = self._docker_sandbox(package)
        backend = (
            "docker"
            if DockerSandbox.available() and docker_sandbox.image_identity() is not None
            else "local"
        )
        if package.environment is not None:
            image_identity = docker_sandbox.image_identity()
            if backend != "docker":
                raise ContractError(
                    "task requires its digest-pinned Docker evaluator image, but it is unavailable"
                )
            if image_identity != package.environment.image_digest:
                raise ContractError(
                    "task evaluator image identity does not match environment.yaml: "
                    f"{image_identity} != {package.environment.image_digest}"
                )
""",
        """        docker_sandbox = self._docker_sandbox(package)
        if batch_image_authorization is not None or (
            row_execution_authorization is not None
            and row_execution_authorization.image_admission_policy is not None
        ):
            image_identity = validate_row_batch_image(
                batch_image_authorization,
                row_execution_authorization,
                manifest,
                expected_kind="live",
                expected_image=(
                    package.environment.evaluator_image if package.environment else None
                ),
                expected_digest=(package.environment.image_digest if package.environment else None),
            )
            backend = "docker"
        else:
            backend = (
                "docker"
                if DockerSandbox.available() and docker_sandbox.image_identity() is not None
                else "local"
            )
            if package.environment is not None:
                image_identity = docker_sandbox.image_identity()
                if backend != "docker":
                    raise ContractError(
                        "task requires its digest-pinned Docker evaluator image, "
                        "but it is unavailable"
                    )
                if image_identity != package.environment.image_digest:
                    raise ContractError(
                        "task evaluator image identity does not match environment.yaml: "
                        f"{image_identity} != {package.environment.image_digest}"
                    )
""",
    ),
    (
        '''        row_execution_authorization: RowExecutionAuthorization,
    ) -> dict[str, Any]:
        """Consume the real row gate and stop before any provider adapter call."""''',
        '''        row_execution_authorization: RowExecutionAuthorization,
        *,
        batch_image_authorization: BatchImageAuthorization | None = None,
    ) -> dict[str, Any]:
        """Consume the real row gate and stop before any provider adapter call."""''',
    ),
    (
        """        boundary = _provider_dispatch_boundary(
            manifest,
            row_execution_authorization,
            stop_before_dispatch=True,
        )""",
        """        if batch_image_authorization is not None or (
            row_execution_authorization.image_admission_policy is not None
        ):
            validate_row_batch_image(
                batch_image_authorization,
                row_execution_authorization,
                manifest,
                expected_kind="rehearsal",
                expected_image=(
                    batch_image_authorization.image if batch_image_authorization else None
                ),
                expected_digest=manifest.evaluator_image_digest,
            )
        boundary = _provider_dispatch_boundary(
            manifest,
            row_execution_authorization,
            stop_before_dispatch=True,
        )""",
    ),
)

CONTRACT_REPLACEMENTS = (
    (
        """# R22 admission-only: constant
RAPID_ANYIO_V5_V26_RELIABILITY_AB_EXPERIMENT_ID = (
    "rapid-public-dev-anyio-v5-v26-reliability-ab-20260831-r22"
)
# R22 admission-only: end constant
""",
        """# R22 admission-only: constant
RAPID_ANYIO_V5_V26_RELIABILITY_AB_EXPERIMENT_ID = (
    "rapid-public-dev-anyio-v5-v26-reliability-ab-20260831-r22"
)
# R22 admission-only: end constant
# R23 admission-only: constant
RAPID_ANYIO_V5_BATCH_IMAGE_AB_EXPERIMENT_ID = (
    "rapid-public-dev-anyio-v5-batch-image-ab-20260831-r23"
)
# R23 admission-only: end constant
""",
    ),
    (
        """                # R22 admission-only: runtime
                or (
                    self.experiment is not None
                    and self.experiment.experiment_id
                    == RAPID_ANYIO_V5_V26_RELIABILITY_AB_EXPERIMENT_ID
                    and self.experiment.schedule_seed == 20260831
                    and (self.tool_schema_version, self.context_policy_version)
                    in {
                        ("v26", "phase-evidence-v35"),
                        ("v27", "phase-evidence-v36"),
                    }
                    and self.task_id == "anyio-interrupt-runner-cleanup"
                    and self.task_version == 5
                )
                # R22 admission-only: end runtime
""",
        """                # R22 admission-only: runtime
                or (
                    self.experiment is not None
                    and self.experiment.experiment_id
                    == RAPID_ANYIO_V5_V26_RELIABILITY_AB_EXPERIMENT_ID
                    and self.experiment.schedule_seed == 20260831
                    and (self.tool_schema_version, self.context_policy_version)
                    in {
                        ("v26", "phase-evidence-v35"),
                        ("v27", "phase-evidence-v36"),
                    }
                    and self.task_id == "anyio-interrupt-runner-cleanup"
                    and self.task_version == 5
                )
                # R22 admission-only: end runtime
                # R23 admission-only: runtime
                or (
                    self.experiment is not None
                    and self.experiment.experiment_id == RAPID_ANYIO_V5_BATCH_IMAGE_AB_EXPERIMENT_ID
                    and self.experiment.schedule_seed == 20260831
                    and (self.tool_schema_version, self.context_policy_version)
                    in {
                        ("v26", "phase-evidence-v35"),
                        ("v27", "phase-evidence-v36"),
                    }
                    and self.task_id == "anyio-interrupt-runner-cleanup"
                    and self.task_version == 5
                )
                # R23 admission-only: end runtime
""",
    ),
    (
        """                    # R22 admission-only: dataset
                    or (
                        self.experiment.experiment_id
                        == RAPID_ANYIO_V5_V26_RELIABILITY_AB_EXPERIMENT_ID
                        and self.experiment.dataset_role == DatasetRole.DEVELOPMENT_VALIDATION
                    )
                    # R22 admission-only: end dataset
""",
        """                    # R22 admission-only: dataset
                    or (
                        self.experiment.experiment_id
                        == RAPID_ANYIO_V5_V26_RELIABILITY_AB_EXPERIMENT_ID
                        and self.experiment.dataset_role == DatasetRole.DEVELOPMENT_VALIDATION
                    )
                    # R22 admission-only: end dataset
                    # R23 admission-only: dataset
                    or (
                        self.experiment.experiment_id == RAPID_ANYIO_V5_BATCH_IMAGE_AB_EXPERIMENT_ID
                        and self.experiment.dataset_role == DatasetRole.DEVELOPMENT_VALIDATION
                    )
                    # R23 admission-only: end dataset
""",
    ),
)


def restore_r22_bytes(raw: bytes, replacements: tuple[tuple[str, str], ...]) -> bytes:
    restored = raw
    for before, after in reversed(replacements):
        fragment = after.encode("utf-8")
        if restored.count(fragment) != 1:
            raise RecoveryError("R23 exact batch-image source delta differs")
        restored = restored.replace(fragment, before.encode("utf-8"), 1)
    return restored


def r22_runner_bytes(raw: bytes) -> bytes:
    restored = restore_r22_bytes(raw, RUNNER_REPLACEMENTS)
    if len(restored) != R22_RUNNER_BYTES or sha256_bytes(restored) != R22_RUNNER_SHA256:
        raise RecoveryError("R23 runner contains changes beyond batch-image admission")
    return restored


def r22_contract_bytes(raw: bytes) -> bytes:
    restored = restore_r22_bytes(raw, CONTRACT_REPLACEMENTS)
    return restored


def frozen_r22_candidate(repository: str | Path = ".") -> dict[str, Any]:
    root = Path(repository).resolve()
    value, raw = _stable_json(root, R22_CANDIDATE_PATH, "Stopped R22 candidate")
    if len(raw) != 26_325 or sha256_bytes(raw) != R22_CANDIDATE_SHA256:
        raise RecoveryError("Stopped R22 candidate identity differs")
    return value


def validate_v26_batch_image_binding(repository: str | Path = ".") -> dict[str, Any]:
    root = Path(repository).resolve()
    candidate = frozen_r22_candidate(root)
    frozen = candidate["selection_evidence"]["treatment_lean_v26"]
    if frozen["content_hash"] != sha256_json(
        {key: value for key, value in frozen.items() if key != "content_hash"}
    ):
        raise RecoveryError("Frozen R22 package binding hash differs")
    current_sources = []
    source_deltas = []
    for descriptor in frozen["current_source_binding"]:
        relative = descriptor["path"]
        if relative not in {"patchloop/contracts.py", "patchloop/agent/runner.py"}:
            current_sources.append(_exact_file(root, descriptor))
            continue
        path = ensure_within(root, relative)
        if path.is_symlink() or not path.is_file():
            raise RecoveryError("R23 integrated source is unavailable")
        raw = path.read_bytes()
        restored = (
            r22_runner_bytes(raw)
            if relative == "patchloop/agent/runner.py"
            else r22_contract_bytes(raw)
        )
        if (
            len(restored) != descriptor["bytes"]
            or sha256_bytes(restored) != descriptor["file_sha256"]
        ):
            raise RecoveryError("R23 source contains changes beyond exact batch-image integration")
        current = {"path": relative, "bytes": len(raw), "file_sha256": sha256_bytes(raw)}
        current_sources.append(current)
        source_deltas.append(
            {
                "path": relative,
                "frozen_r22": descriptor,
                "current": current,
                "frozen_bytes_recovered": True,
                "agent_semantic_policy_changed": False,
            }
        )
    immutable = [
        _exact_file(root, descriptor)
        for descriptor in (
            frozen["qualification"],
            frozen["activation_review"],
            *frozen["immutable_inputs"],
        )
    ]
    prefix = R22_CANDIDATE_PATH.as_posix().removesuffix("-candidate-v30.json")
    stopped_inputs = (
        (R22_CANDIDATE_PATH.as_posix(), 26_325, R22_CANDIDATE_SHA256),
        (
            prefix + "-candidate-v30-rehearsal-v27.json",
            5_830,
            "sha256:a9718145f65e851081edc440cec15e8fb42471268d8a9d102b0f2f7e274c4388",
        ),
        (
            prefix + "-candidate-v30-prestart-stop-v1.json",
            3_795,
            "sha256:2f8e251e4d6430a923245cda771bb818579950fcf9db0995828c14669949af18",
        ),
        (
            "experiments/rapid-candidate-v30-v25-v26-package-ab-public-qualification-20260831-v1.json",
            17_902,
            "sha256:fe615a8ad3f7cdf6560c371558aeb99d4b565e7b3b95cb4898c7e80502cf209a",
        ),
    )
    for relative, size, digest in stopped_inputs:
        immutable.append(
            _exact_file(root, {"path": relative, "bytes": size, "file_sha256": digest})
        )
    body = {
        "schema_version": "rapid-v26-batch-image-integration-binding-v1",
        "runtime_identity": V26_RUNTIME_IDENTITY,
        "qualification": frozen["qualification"],
        "activation_review": frozen["activation_review"],
        "frozen_r22_package_binding_hash": frozen["content_hash"],
        "current_source_binding": current_sources,
        "batch_image_source_deltas": source_deltas,
        "immutable_inputs": immutable,
        "runner_continuity_check_included": False,
        "historical_artifacts_rewritten": False,
        "r22_retry_allowed": False,
        "agent_semantic_policy_changed": False,
    }
    return {**body, "content_hash": sha256_json(body)}
