"""Bind the frozen V26 review to R22's exact admission-only integration.

The reviewed agent implementation is not requalified under a new identity.
Only the three literal R22 allowlist additions in contracts.py may differ;
removing exactly those bytes must recover the reviewed source hash. This is
not a general source-normalization exception.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from patchloop.errors import RecoveryError
from patchloop.evals.rapid_public_development_v22 import _stable_json
from patchloop.util import ensure_within, sha256_bytes, sha256_json

V26_QUALIFICATION_PATH = Path(
    "experiments/lean-harness-r21-reliability-public-qualification-20260831-v1.json"
)
V26_QUALIFICATION_BYTES = 6_253
V26_QUALIFICATION_FILE_SHA256 = (
    "sha256:6b0f753f26c7e7d2d303c9b82bc192396bc1fbd312c709534927b7b39a4d38df"
)
V26_QUALIFICATION_CONTENT_HASH = (
    "sha256:4f07dd47a2d7d81580d135018b8400476880d7ce93f1c280d5b9c8f8c97f9275"
)
V26_REVIEW_PATH = Path(
    "experiments/lean-harness-r21-reliability-activation-review-20260831-v1.json"
)
V26_REVIEW_BYTES = 11_138
V26_REVIEW_FILE_SHA256 = "sha256:e7da9667fff6c16e951eb541aeb59985e91af2bcf247b8473c59549b0d16480e"
V26_REVIEW_CONTENT_HASH = "sha256:a82f018bd3fdbe638d276844f3773d33c89278cfb254f207039f679aac3b6d8c"
V26_RUNTIME_IDENTITY = {
    "anchor_policy_version": "anchored-source-read-v1",
    "context_policy_version": "phase-evidence-v36",
    "feedback_policy_version": "bounded-plan-admission-feedback-v2",
    "generation_recovery_policy_version": "dedicated-generation-incomplete-recovery-v1",
    "lifecycle_plan_policy_version": "public-lifecycle-state-transition-plan-v1",
    "request_evidence_schema": "lean-harness-request-evidence-v26",
    "runtime_policy_version": "lean-harness-v26",
    "tool_schema_version": "v27",
}
REVIEWED_CONTRACT_BYTES = 185_056
REVIEWED_CONTRACT_SHA256 = "sha256:7339df0105d51c6ebefb6635df5f554fb0fcc683d7aaee7543cf8edbdd2d157d"
CONTRACT_ADMISSION_ADDITIONS = (
    "# R22 admission-only: constant\n"
    "RAPID_ANYIO_V5_V26_RELIABILITY_AB_EXPERIMENT_ID = (\n"
    '    "rapid-public-dev-anyio-v5-v26-reliability-ab-20260831-r22"\n'
    ")\n"
    "# R22 admission-only: end constant\n",
    "                # R22 admission-only: runtime\n"
    "                or (\n"
    "                    self.experiment is not None\n"
    "                    and self.experiment.experiment_id\n"
    "                    == RAPID_ANYIO_V5_V26_RELIABILITY_AB_EXPERIMENT_ID\n"
    "                    and self.experiment.schedule_seed == 20260831\n"
    "                    and (self.tool_schema_version, self.context_policy_version)\n"
    "                    in {\n"
    '                        ("v26", "phase-evidence-v35"),\n'
    '                        ("v27", "phase-evidence-v36"),\n'
    "                    }\n"
    '                    and self.task_id == "anyio-interrupt-runner-cleanup"\n'
    "                    and self.task_version == 5\n"
    "                )\n"
    "                # R22 admission-only: end runtime\n",
    "                    # R22 admission-only: dataset\n"
    "                    or (\n"
    "                        self.experiment.experiment_id\n"
    "                        == RAPID_ANYIO_V5_V26_RELIABILITY_AB_EXPERIMENT_ID\n"
    "                        and self.experiment.dataset_role "
    "== DatasetRole.DEVELOPMENT_VALIDATION\n"
    "                    )\n"
    "                    # R22 admission-only: end dataset\n",
)


def reviewed_contract_bytes(raw: bytes) -> bytes:
    """Recover, but never write, the exact reviewed contract from R22 source."""
    restored = raw
    for addition in CONTRACT_ADMISSION_ADDITIONS:
        fragment = addition.encode("utf-8")
        if restored.count(fragment) != 1:
            raise RecoveryError("R22 contract admission-only addition differs")
        restored = restored.replace(fragment, b"", 1)
    if (
        len(restored) != REVIEWED_CONTRACT_BYTES
        or sha256_bytes(restored) != REVIEWED_CONTRACT_SHA256
    ):
        raise RecoveryError("R22 contract contains changes beyond admission-only additions")
    return restored


def _exact_file(root: Path, descriptor: dict[str, Any]) -> dict[str, Any]:
    relative = descriptor["path"]
    selected = ensure_within(root, relative)
    if selected.is_symlink() or not selected.is_file():
        raise RecoveryError(f"Reviewed V26 input is unavailable: {relative}")
    raw = selected.read_bytes()
    actual = {"path": relative, "bytes": len(raw), "file_sha256": sha256_bytes(raw)}
    if any(actual[key] != descriptor[key] for key in actual):
        raise RecoveryError(f"Reviewed V26 input changed: {relative}")
    return actual


def validate_v26_package_binding(repository: str | Path = ".") -> dict[str, Any]:
    root = Path(repository).resolve()
    qualification, qualification_raw = _stable_json(
        root, V26_QUALIFICATION_PATH, "Frozen V26 qualification"
    )
    review, review_raw = _stable_json(root, V26_REVIEW_PATH, "Frozen V26 activation review")
    if not (
        len(qualification_raw) == V26_QUALIFICATION_BYTES
        and sha256_bytes(qualification_raw) == V26_QUALIFICATION_FILE_SHA256
        and qualification["content_hash"] == V26_QUALIFICATION_CONTENT_HASH
        and qualification["status"] == "offline-qualified"
        and qualification["external_calls"] == 0
        and qualification["candidate_created"] is False
        and qualification["runtime_identity"] == V26_RUNTIME_IDENTITY
        and len(review_raw) == V26_REVIEW_BYTES
        and sha256_bytes(review_raw) == V26_REVIEW_FILE_SHA256
        and review["content_hash"] == V26_REVIEW_CONTENT_HASH
        and review["status"] == "activation-reviewed-candidate-decision-ready"
        and review["decision"]["adoption_status"] == "eligible-not-adopted"
        and review["decision"]["candidate_preparation_ready"] is True
        and review["external_calls"] == 0
        and review["candidate_created"] is False
        and review["runtime_identity"] == V26_RUNTIME_IDENTITY
        and review["runtime_source_binding"] == qualification["source_files"]
    ):
        raise RecoveryError("Frozen V26 review or qualification identity differs")
    current_sources: list[dict[str, Any]] = []
    admission_delta: dict[str, Any] | None = None
    for descriptor in qualification["source_files"]:
        if descriptor["path"] != "patchloop/contracts.py":
            current_sources.append(_exact_file(root, descriptor))
            continue
        raw = ensure_within(root, descriptor["path"]).read_bytes()
        restored = reviewed_contract_bytes(raw)
        if descriptor != {
            "path": "patchloop/contracts.py",
            "bytes": len(restored),
            "file_sha256": sha256_bytes(restored),
        }:
            raise RecoveryError("V26 reviewed contract descriptor differs")
        current = {
            "path": descriptor["path"],
            "bytes": len(raw),
            "file_sha256": sha256_bytes(raw),
        }
        current_sources.append(current)
        admission_delta = {
            "path": descriptor["path"],
            "reviewed": descriptor,
            "current": current,
            "exact_addition_count": len(CONTRACT_ADMISSION_ADDITIONS),
            "addition_hashes": [
                sha256_bytes(value.encode("utf-8")) for value in CONTRACT_ADMISSION_ADDITIONS
            ],
            "reviewed_bytes_recovered": True,
            "agent_policy_changed": False,
        }
    if admission_delta is None:
        raise RecoveryError("V26 contract admission proof is missing")
    # Includes V25 source and R21 bytes. No historical result is rerun or relabelled.
    immutable_inputs = [_exact_file(root, item) for item in qualification["immutable_inputs"]]
    proposal = qualification["separate_public_check_proposal"]
    immutable_inputs.append(_exact_file(root, proposal))
    review_module = next(
        item
        for item in review["review_source_files"]
        if item["path"] == "patchloop/agent/workflow_r21_reliability_activation_review.py"
    )
    immutable_inputs.append(_exact_file(root, review_module))
    body = {
        "schema_version": "rapid-v26-reviewed-package-admission-binding-v1",
        "runtime_identity": V26_RUNTIME_IDENTITY,
        "qualification": {
            "path": V26_QUALIFICATION_PATH.as_posix(),
            "bytes": len(qualification_raw),
            "file_sha256": sha256_bytes(qualification_raw),
            "content_hash": qualification["content_hash"],
        },
        "activation_review": {
            "path": V26_REVIEW_PATH.as_posix(),
            "bytes": len(review_raw),
            "file_sha256": sha256_bytes(review_raw),
            "content_hash": review["content_hash"],
        },
        "current_source_binding": current_sources,
        "admission_only_source_delta": admission_delta,
        "immutable_inputs": immutable_inputs,
        "runner_continuity_check_included": False,
        "historical_artifacts_rewritten": False,
    }
    return {**body, "content_hash": sha256_json(body)}
