"""Append-only evaluator-v2 receipt issuance and persisted-chain validation.

The raw v2 result deliberately remains unofficial.  This module authenticates
that the exact durable event prefix and ArtifactStore objects were consumed
under separately supplied successor source/suite authority.  It does not claim
Docker daemon enforcement beyond the typed requested-policy observations.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from patchloop.artifacts import ArtifactStore
from patchloop.contracts import (
    Artifact,
    EvaluatorSafetyContract,
    EvaluatorV2EvaluationReceipt,
    RunManifest,
    RunResult,
    SafetyEvidenceBundle,
    TaskPackage,
    safety_evidence_bundle_artifact_bytes,
)
from patchloop.errors import ContractError, RecoveryError
from patchloop.state import StateStore
from patchloop.util import sha256_bytes, sha256_json
from patchloop.verifier.evidence import (
    EvaluatorV2EvidenceValidation,
    validate_evaluator_v2_artifact_chain,
)
from patchloop.verifier.runtime_evidence import (
    EvaluatorV2RuntimeAuthority,
    EvaluatorV2StoreBoundProduction,
    evaluator_v2_manifest_runtime_tuple_hash,
    evaluator_v2_preterminal_event_projection,
)

_RECEIPT_SCHEMA = "evaluator-v2-evaluation-receipt-v1"
_PROVENANCE_SCHEMA = "evaluator-v2-provenance-v1"
_SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True)
class EvaluatorV2QualificationAuthority:
    """Separately qualified successor identities needed to issue a receipt."""

    runtime: EvaluatorV2RuntimeAuthority
    suite_hash: str
    source_qualification_hash: str
    runtime_tuple_hash: str

    def __post_init__(self) -> None:
        if not _SHA256_PATTERN.fullmatch(self.suite_hash):
            raise ValueError("evaluator-v2 qualification suite hash is invalid")
        if not _SHA256_PATTERN.fullmatch(self.source_qualification_hash):
            raise ValueError("evaluator-v2 source qualification hash is invalid")
        if not _SHA256_PATTERN.fullmatch(self.runtime_tuple_hash):
            raise ValueError("evaluator-v2 qualification runtime tuple hash is invalid")


@dataclass(frozen=True)
class EvaluatorV2ReceiptValidation:
    receipt: EvaluatorV2EvaluationReceipt
    manifest: RunManifest
    result: RunResult
    bundle: SafetyEvidenceBundle
    evidence: EvaluatorV2EvidenceValidation


def _json_bytes(value: object) -> bytes:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _run_dir(artifact_store: ArtifactStore, run_id: str) -> Path:
    return artifact_store.root / "runs" / run_id


def _write_once_or_match(
    artifact_store: ArtifactStore,
    path: Path,
    content: bytes,
) -> None:
    """Create one derived evidence file without ever replacing existing bytes."""

    try:
        root = artifact_store.root.resolve()
        resolved = path.resolve()
    except OSError as exc:
        raise RecoveryError("evaluator-v2 receipt path cannot be resolved") from exc
    if not resolved.is_relative_to(root) or path.is_symlink():
        raise RecoveryError("evaluator-v2 receipt path escapes the artifact root")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError:
        try:
            existing = path.read_bytes()
        except OSError as exc:
            raise RecoveryError("existing evaluator-v2 receipt file is unreadable") from exc
        if existing != content:
            raise RecoveryError("evaluator-v2 receipt evidence is immutable") from None


def _validated_authority(
    authority: EvaluatorV2QualificationAuthority,
) -> EvaluatorV2QualificationAuthority:
    try:
        contract = EvaluatorSafetyContract.model_validate(
            authority.runtime.safety_contract.model_dump(mode="json")
        )
    except (AttributeError, ValidationError):
        raise ContractError("evaluator-v2 qualification authority is invalid") from None
    if not _SHA256_PATTERN.fullmatch(authority.runtime.evaluator_source_hash):
        raise ContractError("evaluator-v2 qualification source hash is invalid")
    if not authority.runtime.tool_schemas or not authority.runtime.private_markers:
        raise ContractError("evaluator-v2 qualification authority is incomplete")
    return EvaluatorV2QualificationAuthority(
        runtime=EvaluatorV2RuntimeAuthority(
            safety_contract=contract,
            evaluator_source_hash=authority.runtime.evaluator_source_hash,
            tool_schemas=tuple(authority.runtime.tool_schemas),
            private_markers=tuple(authority.runtime.private_markers),
        ),
        suite_hash=authority.suite_hash,
        source_qualification_hash=authority.source_qualification_hash,
        runtime_tuple_hash=authority.runtime_tuple_hash,
    )


def _require_manifest_authority(
    manifest: RunManifest,
    authority: EvaluatorV2QualificationAuthority,
) -> None:
    binding = manifest.evaluator_contract
    experiment = manifest.experiment
    if (
        manifest.schema_version != "run-manifest-v2"
        or binding is None
        or experiment is None
        or binding.evaluator_source_hash != authority.runtime.evaluator_source_hash
        or binding.contract_hash != authority.runtime.safety_contract.content_hash
        or experiment.suite_hash != authority.suite_hash
        or evaluator_v2_manifest_runtime_tuple_hash(manifest) != authority.runtime_tuple_hash
    ):
        raise ContractError("evaluator-v2 receipt authority disagrees with the manifest")


def validate_evaluator_v2_manifest_authority(
    manifest: RunManifest,
    authority: EvaluatorV2QualificationAuthority,
) -> EvaluatorV2QualificationAuthority:
    """Fail before runner side effects when source/suite/runtime authority drifts."""

    checked = _validated_authority(authority)
    checked_manifest = RunManifest.model_validate(manifest.model_dump(mode="json"))
    _require_manifest_authority(checked_manifest, checked)
    return checked


def _descriptor_inventory(
    artifacts: tuple[Artifact, ...],
) -> tuple[tuple[Artifact, ...], str]:
    validated = tuple(
        sorted(
            (Artifact.model_validate(item.model_dump(mode="json")) for item in artifacts),
            key=lambda item: item.artifact_id,
        )
    )
    ids = [item.artifact_id for item in validated]
    if len(ids) != len(set(ids)):
        raise ContractError("evaluator-v2 receipt artifact inventory contains duplicate IDs")
    return validated, sha256_json([item.model_dump(mode="json") for item in validated])


def issue_evaluator_v2_evaluation_receipt(
    *,
    state_store: StateStore,
    artifact_store: ArtifactStore,
    package: TaskPackage,
    production: EvaluatorV2StoreBoundProduction,
    authority: EvaluatorV2QualificationAuthority,
    evaluator_duration_ms: int,
) -> EvaluatorV2ReceiptValidation:
    """Persist and re-read one append-only receipt from durable state and CAS."""

    authority = _validated_authority(authority)
    if evaluator_duration_ms < 0:
        raise ContractError("evaluator-v2 duration cannot be negative")
    manifest = state_store.get_manifest(production.production.result.run_id)
    _require_manifest_authority(manifest, authority)
    events = tuple(state_store.list_events(manifest.run_id))
    result = RunResult.model_validate(production.production.result.model_dump(mode="json"))
    bundle = SafetyEvidenceBundle.model_validate(
        production.production.bundle.model_dump(mode="json")
    )
    patch_ref = result.submitted_patch_artifact
    if patch_ref is None:
        raise ContractError("evaluator-v2 receipt result lacks its submitted patch")
    safety_prefix, preterminal_event_hash, preterminal_through_sequence = (
        evaluator_v2_preterminal_event_projection(
            events,
            run_id=manifest.run_id,
            submitted_patch_hash=patch_ref.content_hash,
        )
    )
    if (
        bundle.through_sequence != safety_prefix[-1].sequence
        or production.preterminal_event_hash != preterminal_event_hash
        or production.preterminal_through_sequence != preterminal_through_sequence
    ):
        raise ContractError("evaluator-v2 receipt requires the exact durable event boundary")

    manifest_bytes = manifest.model_dump_json(indent=2).encode("utf-8")
    result_bytes = result.model_dump_json(indent=2).encode("utf-8")
    bundle_bytes = safety_evidence_bundle_artifact_bytes(bundle)
    descriptors, inventory_hash = _descriptor_inventory(production.production.evidence_artifacts)
    descriptor_map = {item.artifact_id: item for item in descriptors}
    evidence = validate_evaluator_v2_artifact_chain(
        package=package,
        expected_contract=authority.runtime.safety_contract,
        expected_evaluator_source_hash=authority.runtime.evaluator_source_hash,
        expected_tool_schemas=authority.runtime.tool_schemas,
        private_markers=authority.runtime.private_markers,
        manifest=manifest,
        result=result,
        bundle=bundle,
        manifest_bytes=manifest_bytes,
        result_bytes=result_bytes,
        bundle_bytes=bundle_bytes,
        events=safety_prefix,
        evidence_descriptors=descriptor_map,
        read_evidence=artifact_store.read_bytes,
    )
    if evidence != production.production.validation:
        raise ContractError("evaluator-v2 receipt revalidation disagrees with production")

    bundle_ref = result.safety_evidence_bundle
    binding = result.evaluator_contract
    if patch_ref is None or bundle_ref is None or binding is None:
        raise ContractError("evaluator-v2 receipt result lacks required bindings")
    provenance = {
        "schema_version": _PROVENANCE_SCHEMA,
        "run_id": manifest.run_id,
        "evaluator_contract_hash": binding.contract_hash,
        "evaluator_source_hash": authority.runtime.evaluator_source_hash,
        "suite_hash": authority.suite_hash,
        "source_qualification_hash": authority.source_qualification_hash,
        "tool_schema_hash": sha256_json(list(authority.runtime.tool_schemas)),
        "manifest_file_hash": sha256_bytes(manifest_bytes),
        "result_file_hash": sha256_bytes(result_bytes),
        "safety_bundle_file_hash": sha256_bytes(bundle_bytes),
        "safety_bundle_semantic_hash": bundle.content_hash,
        "safety_bundle_artifact_hash": bundle_ref.content_hash,
        "submitted_patch_artifact_id": patch_ref.artifact_id,
        "submitted_patch_content_hash": patch_ref.content_hash,
        "event_prefix_hash": bundle.event_prefix_hash,
        "through_sequence": bundle.through_sequence,
        "preterminal_event_hash": preterminal_event_hash,
        "preterminal_through_sequence": preterminal_through_sequence,
        "evidence_inventory_hash": inventory_hash,
        "evidence_artifacts": [item.model_dump(mode="json") for item in descriptors],
    }
    provenance_bytes = _json_bytes(provenance)
    receipt_body = {
        "schema_version": _RECEIPT_SCHEMA,
        "run_id": manifest.run_id,
        "evaluator_contract_hash": binding.contract_hash,
        "evaluator_source_hash": authority.runtime.evaluator_source_hash,
        "suite_hash": authority.suite_hash,
        "source_qualification_hash": authority.source_qualification_hash,
        "tool_schema_hash": sha256_json(list(authority.runtime.tool_schemas)),
        "manifest_file_hash": sha256_bytes(manifest_bytes),
        "result_file_hash": sha256_bytes(result_bytes),
        "provenance_file_hash": sha256_bytes(provenance_bytes),
        "safety_bundle_file_hash": sha256_bytes(bundle_bytes),
        "safety_bundle_semantic_hash": bundle.content_hash,
        "safety_bundle_artifact_hash": bundle_ref.content_hash,
        "submitted_patch_artifact_id": patch_ref.artifact_id,
        "submitted_patch_content_hash": patch_ref.content_hash,
        "event_prefix_hash": bundle.event_prefix_hash,
        "through_sequence": bundle.through_sequence,
        "preterminal_event_hash": preterminal_event_hash,
        "preterminal_through_sequence": preterminal_through_sequence,
        "evidence_inventory_hash": inventory_hash,
        "evidence_artifact_count": len(descriptors),
        "evaluator_duration_ms": evaluator_duration_ms,
        "runtime_authenticated": True,
        "qualification_eligible": True,
    }
    receipt = EvaluatorV2EvaluationReceipt(
        **receipt_body,
        content_hash=sha256_json(receipt_body),
    )
    run_dir = _run_dir(artifact_store, manifest.run_id)
    for name, content in (
        ("manifest.json", manifest_bytes),
        ("result.json", result_bytes),
        ("safety-evidence-bundle.json", bundle_bytes),
        ("provenance.json", provenance_bytes),
        ("evaluation-receipt.json", receipt.model_dump_json(indent=2).encode("utf-8")),
    ):
        _write_once_or_match(artifact_store, run_dir / name, content)
    validated = validate_persisted_evaluator_v2_evaluation_receipt(
        state_store=state_store,
        artifact_store=artifact_store,
        run_id=manifest.run_id,
        package=package,
        authority=authority,
        expected_result=result,
    )
    if validated.receipt != receipt:
        raise ContractError("persisted evaluator-v2 receipt differs from its issuer")
    return validated


def validate_persisted_evaluator_v2_evaluation_receipt(
    *,
    state_store: StateStore,
    artifact_store: ArtifactStore,
    run_id: str,
    package: TaskPackage,
    authority: EvaluatorV2QualificationAuthority,
    expected_result: RunResult | None = None,
) -> EvaluatorV2ReceiptValidation:
    """Revalidate a persisted receipt against trusted authority, state, and CAS."""

    authority = _validated_authority(authority)
    manifest = state_store.get_manifest(run_id)
    _require_manifest_authority(manifest, authority)
    run_dir = _run_dir(artifact_store, run_id)
    try:
        receipt_bytes = (run_dir / "evaluation-receipt.json").read_bytes()
        manifest_bytes = (run_dir / "manifest.json").read_bytes()
        result_bytes = (run_dir / "result.json").read_bytes()
        bundle_bytes = (run_dir / "safety-evidence-bundle.json").read_bytes()
        provenance_bytes = (run_dir / "provenance.json").read_bytes()
        receipt = EvaluatorV2EvaluationReceipt.model_validate_json(receipt_bytes)
        persisted_manifest = RunManifest.model_validate_json(manifest_bytes)
        result = RunResult.model_validate_json(result_bytes)
        bundle = SafetyEvidenceBundle.model_validate_json(bundle_bytes)
        provenance = json.loads(provenance_bytes)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValidationError):
        raise ContractError("persisted evaluator-v2 receipt bundle is invalid") from None
    if receipt_bytes != receipt.model_dump_json(indent=2).encode("utf-8"):
        raise ContractError("evaluator-v2 receipt bytes use an unexpected serializer")
    if persisted_manifest != manifest or (
        expected_result is not None and result != expected_result
    ):
        raise ContractError("evaluator-v2 receipt files disagree with durable run state")
    file_hashes = (
        (receipt.manifest_file_hash, manifest_bytes),
        (receipt.result_file_hash, result_bytes),
        (receipt.safety_bundle_file_hash, bundle_bytes),
        (receipt.provenance_file_hash, provenance_bytes),
    )
    if any(expected != sha256_bytes(content) for expected, content in file_hashes):
        raise ContractError("evaluator-v2 receipt file hash mismatch")
    if not isinstance(provenance, dict) or set(provenance) != {
        "schema_version",
        "run_id",
        "evaluator_contract_hash",
        "evaluator_source_hash",
        "suite_hash",
        "source_qualification_hash",
        "tool_schema_hash",
        "manifest_file_hash",
        "result_file_hash",
        "safety_bundle_file_hash",
        "safety_bundle_semantic_hash",
        "safety_bundle_artifact_hash",
        "submitted_patch_artifact_id",
        "submitted_patch_content_hash",
        "event_prefix_hash",
        "through_sequence",
        "preterminal_event_hash",
        "preterminal_through_sequence",
        "evidence_inventory_hash",
        "evidence_artifacts",
    }:
        raise ContractError("evaluator-v2 provenance contract mismatch")
    try:
        raw_descriptors = provenance["evidence_artifacts"]
        if not isinstance(raw_descriptors, list):
            raise TypeError
        descriptors = tuple(Artifact.model_validate(item) for item in raw_descriptors)
    except (KeyError, TypeError, ValidationError):
        raise ContractError("evaluator-v2 provenance artifact inventory is invalid") from None
    sorted_descriptors, inventory_hash = _descriptor_inventory(descriptors)
    if descriptors != sorted_descriptors:
        raise ContractError("evaluator-v2 provenance artifact inventory is not canonical")
    descriptor_map = {item.artifact_id: item for item in descriptors}
    preterminal_events = tuple(
        event
        for event in state_store.list_events(run_id)
        if event.sequence <= receipt.preterminal_through_sequence
    )
    patch_ref = result.submitted_patch_artifact
    if patch_ref is None:
        raise ContractError("evaluator-v2 receipt result lacks its submitted patch")
    events, preterminal_event_hash, preterminal_through_sequence = (
        evaluator_v2_preterminal_event_projection(
            preterminal_events,
            run_id=run_id,
            submitted_patch_hash=patch_ref.content_hash,
        )
    )
    if (
        receipt.preterminal_event_hash != preterminal_event_hash
        or receipt.preterminal_through_sequence != preterminal_through_sequence
    ):
        raise ContractError("evaluator-v2 receipt preterminal event hash mismatch")
    evidence = validate_evaluator_v2_artifact_chain(
        package=package,
        expected_contract=authority.runtime.safety_contract,
        expected_evaluator_source_hash=authority.runtime.evaluator_source_hash,
        expected_tool_schemas=authority.runtime.tool_schemas,
        private_markers=authority.runtime.private_markers,
        manifest=manifest,
        result=result,
        bundle=bundle,
        manifest_bytes=manifest_bytes,
        result_bytes=result_bytes,
        bundle_bytes=bundle_bytes,
        events=events,
        evidence_descriptors=descriptor_map,
        read_evidence=artifact_store.read_bytes,
    )
    bundle_ref = result.safety_evidence_bundle
    binding = result.evaluator_contract
    if patch_ref is None or bundle_ref is None or binding is None:
        raise ContractError("evaluator-v2 receipt result lacks required bindings")
    expected_projection = {
        "schema_version": _PROVENANCE_SCHEMA,
        "run_id": run_id,
        "evaluator_contract_hash": binding.contract_hash,
        "evaluator_source_hash": authority.runtime.evaluator_source_hash,
        "suite_hash": authority.suite_hash,
        "source_qualification_hash": authority.source_qualification_hash,
        "tool_schema_hash": sha256_json(list(authority.runtime.tool_schemas)),
        "manifest_file_hash": receipt.manifest_file_hash,
        "result_file_hash": receipt.result_file_hash,
        "safety_bundle_file_hash": receipt.safety_bundle_file_hash,
        "safety_bundle_semantic_hash": bundle.content_hash,
        "safety_bundle_artifact_hash": bundle_ref.content_hash,
        "submitted_patch_artifact_id": patch_ref.artifact_id,
        "submitted_patch_content_hash": patch_ref.content_hash,
        "event_prefix_hash": bundle.event_prefix_hash,
        "through_sequence": bundle.through_sequence,
        "preterminal_event_hash": preterminal_event_hash,
        "preterminal_through_sequence": preterminal_through_sequence,
        "evidence_inventory_hash": inventory_hash,
        "evidence_artifacts": [item.model_dump(mode="json") for item in descriptors],
    }
    if provenance != expected_projection:
        raise ContractError("evaluator-v2 provenance disagrees with trusted evidence")
    receipt_projection = {
        "evaluator_contract_hash": binding.contract_hash,
        "evaluator_source_hash": authority.runtime.evaluator_source_hash,
        "suite_hash": authority.suite_hash,
        "source_qualification_hash": authority.source_qualification_hash,
        "tool_schema_hash": sha256_json(list(authority.runtime.tool_schemas)),
        "safety_bundle_semantic_hash": bundle.content_hash,
        "safety_bundle_artifact_hash": bundle_ref.content_hash,
        "submitted_patch_artifact_id": patch_ref.artifact_id,
        "submitted_patch_content_hash": patch_ref.content_hash,
        "event_prefix_hash": bundle.event_prefix_hash,
        "through_sequence": bundle.through_sequence,
        "preterminal_event_hash": preterminal_event_hash,
        "preterminal_through_sequence": preterminal_through_sequence,
        "evidence_inventory_hash": inventory_hash,
        "evidence_artifact_count": len(descriptors),
    }
    if any(getattr(receipt, key) != value for key, value in receipt_projection.items()):
        raise ContractError("evaluator-v2 receipt disagrees with trusted evidence")
    return EvaluatorV2ReceiptValidation(
        receipt=receipt,
        manifest=manifest,
        result=result,
        bundle=bundle,
        evidence=evidence,
    )
