"""One inspected digest-pinned image per trusted batch, never a global cache.

The live issuer performs at most one inspect after a durable attempt marker.
Rehearsal binds the same admission surface but never observes Docker or issues
live authority. Capabilities cannot be deserialized or transferred to a new
batch instance, including a restart of an identical candidate.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from patchloop.errors import HarnessAdmissionError
from patchloop.sandbox import DockerSandbox
from patchloop.sandbox.runner import DockerImageIdentityProjection
from patchloop.util import canonical_json, sha256_bytes, sha256_json

if TYPE_CHECKING:
    from patchloop.agent.runner import BatchExecutionAuthorization, RowExecutionAuthorization
    from patchloop.contracts import RunManifest

POLICY_VERSION = "batch-pinned-image-admission-v1"
IMAGE_ADMISSION_CONTRACT = {
    "policy_version": POLICY_VERSION,
    "unique_digest_pinned_images": 1,
    "image_inspect_attempts_max": 1,
    "daemon_version_calls": 0,
    "per_row_image_inspect_calls": 0,
    "pull_policy": "never",
    "network_policy": "none",
    "durable_attempt_before_inspect": True,
    "reuse_scope": "same-in-process-batch-and-admitted-manifests",
    "missing_or_invalid_receipt": "fail-closed-without-reinspection",
    "restart_or_retry_allowed": False,
}
_IMAGE_AUTHORITY_GUARD = object()


@dataclass(frozen=True)
class BatchImageAuthorization:
    authority_kind: str
    image: str
    digest: str
    binding_hash: str
    receipt_hash: str
    receipt_path: Path | None
    receipt_file_hash: str | None
    _batch: BatchExecutionAuthorization
    _guard: object


def _binding(
    batch: BatchExecutionAuthorization,
    manifests: tuple[RunManifest, ...],
    image: str,
) -> dict[str, Any]:
    from patchloop.agent.runner import batch_execution_authorization_receipt

    receipt = batch_execution_authorization_receipt(batch)
    match = re.fullmatch(r"[^\s@]+@(sha256:[0-9a-f]{64})", image)
    if (
        batch.image_admission_policy != POLICY_VERSION
        or batch.image_admission_image != image
        or match is None
        or not manifests
        or tuple(sha256_json(item.model_dump(mode="json")) for item in manifests)
        != batch.manifest_hashes
        or receipt["next_order"] != 1
    ):
        raise HarnessAdmissionError("batch image admission binding is invalid")
    digest = match.group(1)
    for manifest in manifests:
        if (
            manifest.sandbox_backend != "docker"
            or manifest.agent_image_digest != digest
            or manifest.evaluator_image_digest != digest
            or manifest.probe_image_digest is not None
        ):
            raise HarnessAdmissionError("batch image admission requires one exact pinned image")
    return {
        "policy_version": POLICY_VERSION,
        "authority_kind": batch.authority_kind,
        "execution_hash": batch.execution_hash,
        "plan_hash": batch.plan_hash,
        "runtime_build_hash": batch.runtime_build_hash,
        "schedule_hash": batch.schedule_hash,
        "cost_control_hash": batch.cost_control_hash,
        "manifest_hashes": list(batch.manifest_hashes),
        "image": image,
        "digest": digest,
    }


def _claim_attempt(batch: BatchExecutionAuthorization, expected_kind: str) -> None:
    with batch._state.lock:
        if (
            batch.authority_kind != expected_kind
            or batch._state.next_order != 1
            or batch._state.image_admission_attempted
        ):
            raise HarnessAdmissionError("batch image admission attempt is unavailable")
        batch._state.image_admission_attempted = True


def _record(body: dict[str, Any]) -> dict[str, Any]:
    return {**body, "content_hash": sha256_json(body)}


def _record_bytes(record: dict[str, Any]) -> bytes:
    return (canonical_json(record) + "\n").encode("utf-8")


def _install_authority(
    batch: BatchExecutionAuthorization,
    binding: dict[str, Any],
    receipt: dict[str, Any],
    *,
    receipt_path: Path | None,
    receipt_file_hash: str | None,
) -> BatchImageAuthorization:
    authorization = BatchImageAuthorization(
        authority_kind=batch.authority_kind,
        image=binding["image"],
        digest=binding["digest"],
        binding_hash=sha256_json(binding),
        receipt_hash=receipt["content_hash"],
        receipt_path=receipt_path,
        receipt_file_hash=receipt_file_hash,
        _batch=batch,
        _guard=_IMAGE_AUTHORITY_GUARD,
    )
    with batch._state.lock:
        if batch._state.image_authorization is not None:
            raise HarnessAdmissionError("batch image authority was already installed")
        batch._state.image_authorization = authorization
    return authorization


def issue_live_batch_image_authorization(
    batch: BatchExecutionAuthorization,
    manifests: tuple[RunManifest, ...],
    *,
    image: str,
    receipt_path: Path,
) -> BatchImageAuthorization:
    """Inspect once, after consuming the exact invocation durably.

    A failed/partial receipt is deliberately not recoverable into live authority.
    A new exact candidate and approval are needed after any interrupted attempt.
    No daemon version, tag lookup, fallback, pull or retry is performed here.
    """
    binding = _binding(batch, manifests, image)
    _claim_attempt(batch, "live")
    path = Path(receipt_path)
    if path.is_symlink():
        raise HarnessAdmissionError("batch image receipt cannot be a symlink")
    path.parent.mkdir(parents=True, exist_ok=True)
    started = _record(
        {
            "schema_version": "batch-image-admission-event-v1",
            "sequence": 1,
            "type": "image-inspection-attempt-started",
            "binding": binding,
            "image_admission_contract": IMAGE_ADMISSION_CONTRACT,
            "previous_hash": None,
        }
    )
    try:
        stream = path.open("xb")
    except FileExistsError as exc:
        raise HarnessAdmissionError("batch image receipt exists; retry is forbidden") from exc
    with stream:
        start_bytes = _record_bytes(started)
        stream.write(start_bytes)
        stream.flush()
        os.fsync(stream.fileno())
        projection = None
        reason = "IMAGE_IDENTITY_UNAVAILABLE_OR_MISMATCHED"
        try:
            projection = DockerSandbox(image).image_identity_projection()
            valid = (
                isinstance(projection, DockerImageIdentityProjection)
                and projection.requested_repo_digest == image
                and projection.requested_digest == binding["digest"]
                and projection.verified_identity == binding["digest"]
                and projection.matched_repo_digest in {image, image.removeprefix("docker.io/")}
                and projection.matched_repo_digest in projection.repo_digests
                and re.fullmatch(r"sha256:[0-9a-f]{64}", projection.config_id) is not None
            )
        except Exception:
            valid = False
            reason = "IMAGE_INSPECTION_ADAPTER_FAILED"
        completed = _record(
            {
                "schema_version": "batch-image-admission-event-v1",
                "sequence": 2,
                "type": "image-admitted" if valid else "image-admission-rejected",
                "binding_hash": sha256_json(binding),
                "previous_hash": started["content_hash"],
                "inspection_adapter_calls": 1,
                "observation_source": "docker-image-inspect-projection",
                "identity_projection": (
                    {
                        "config_id": projection.config_id,
                        "repo_digests": list(projection.repo_digests),
                        "matched_repo_digest": projection.matched_repo_digest,
                    }
                    if valid and projection is not None
                    else None
                ),
                "rejection_code": None if valid else reason,
            }
        )
        completed_bytes = _record_bytes(completed)
        stream.write(completed_bytes)
        stream.flush()
        os.fsync(stream.fileno())
    if not valid:
        raise HarnessAdmissionError(reason)
    return _install_authority(
        batch,
        binding,
        completed,
        receipt_path=path,
        receipt_file_hash=sha256_bytes(start_bytes + completed_bytes),
    )


def rehearse_batch_image_authorization(
    batch: BatchExecutionAuthorization,
    manifests: tuple[RunManifest, ...],
    *,
    image: str,
) -> tuple[BatchImageAuthorization, dict[str, Any]]:
    """Project the contract only; this is not an observed Docker identity."""
    binding = _binding(batch, manifests, image)
    _claim_attempt(batch, "rehearsal")
    receipt = _record(
        {
            "schema_version": "batch-image-admission-rehearsal-v1",
            "binding": binding,
            "image_admission_contract": IMAGE_ADMISSION_CONTRACT,
            "observation_source": "no-call-binding-projection",
            "image_identity_observed": False,
            "docker_calls_made": 0,
            "live_authority_created": False,
        }
    )
    return (
        _install_authority(batch, binding, receipt, receipt_path=None, receipt_file_hash=None),
        receipt,
    )


def validate_row_batch_image(
    authorization: BatchImageAuthorization | None,
    row: RowExecutionAuthorization | None,
    manifest: RunManifest | None,
    *,
    expected_kind: str,
    expected_image: str | None,
    expected_digest: str | None,
) -> str:
    """The shared live/rehearsal row-start gate, with zero Docker queries."""
    from patchloop.agent.runner import row_execution_authorization_receipt

    if not isinstance(authorization, BatchImageAuthorization) or row is None or manifest is None:
        raise HarnessAdmissionError("row requires its batch image authority")
    receipt = row_execution_authorization_receipt(row)
    batch = authorization._batch
    if (
        authorization._guard is not _IMAGE_AUTHORITY_GUARD
        or batch._state.image_authorization is not authorization
        or row._batch_state is not batch._state
        or authorization.authority_kind != expected_kind
        or row.authority_kind != expected_kind
        or row.image_admission_policy != POLICY_VERSION
        or batch.image_admission_policy != POLICY_VERSION
        or not receipt["consumed"]
        or row.execution_hash != batch.execution_hash
        or row.plan_hash != batch.plan_hash
        or row.manifest_hash != sha256_json(manifest.model_dump(mode="json"))
        or row.manifest_hash not in batch.manifest_hashes
        or expected_image != authorization.image
        or expected_digest != authorization.digest
        or manifest.sandbox_backend != "docker"
        or manifest.agent_image_digest != authorization.digest
        or manifest.evaluator_image_digest != authorization.digest
        or manifest.probe_image_digest is not None
    ):
        raise HarnessAdmissionError("row batch image authority differs")
    if expected_kind == "live":
        try:
            unchanged = (
                authorization.receipt_path is not None
                and not authorization.receipt_path.is_symlink()
                and sha256_bytes(authorization.receipt_path.read_bytes())
                == authorization.receipt_file_hash
            )
        except OSError:
            unchanged = False
        if not unchanged:
            raise HarnessAdmissionError("batch image receipt changed or disappeared")
    elif authorization.receipt_path is not None or authorization.receipt_file_hash is not None:
        raise HarnessAdmissionError("rehearsal image authority carries live observation")
    return authorization.digest


def image_authorization_receipt(authorization: BatchImageAuthorization) -> dict[str, Any]:
    if (
        authorization._guard is not _IMAGE_AUTHORITY_GUARD
        or authorization._batch._state.image_authorization is not authorization
    ):
        raise HarnessAdmissionError("batch image authority receipt is invalid")
    return _record(
        {
            "schema_version": "batch-image-capability-receipt-v1",
            "authority_kind": authorization.authority_kind,
            "execution_hash": authorization._batch.execution_hash,
            "binding_hash": authorization.binding_hash,
            "image": authorization.image,
            "digest": authorization.digest,
            "receipt_hash": authorization.receipt_hash,
            "receipt_file_hash": authorization.receipt_file_hash,
        }
    )
