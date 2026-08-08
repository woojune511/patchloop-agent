"""Seal the D-117 grammar-blind control-acquisition protocol candidate.

D-117 consumes the exact D-116 approval only to materialize a protocol and a
future execution-authorization candidate.  It does not identify or read a new
pool, assemble members, create a blind packet, recruit reviewers, label a
control, or execute the D-116 matcher, a classifier, calibration, retrieval,
an agent, a provider, or an evaluator.
"""

from __future__ import annotations

import json
import os
import stat
from collections.abc import Mapping, Sequence
from datetime import datetime
from itertools import pairwise
from pathlib import Path
from typing import Any

from patchloop.errors import ContractError
from patchloop.util import canonical_json, sha256_bytes, sha256_text

MILESTONE = "D-117"
RECEIPT_SCHEMA_VERSION = (
    "grammar-blind-public-control-acquisition-protocol-approval-receipt-d117-v1"
)
PREFLIGHT_SCHEMA_VERSION = "grammar-blind-public-control-acquisition-protocol-preflight-d117-v1"
CANDIDATE_SCHEMA_VERSION = (
    "grammar-blind-public-control-acquisition-protocol-authorization-candidate-d117-v1"
)
SOURCE_GATE_SCHEMA_VERSION = "grammar-blind-public-control-acquisition-protocol-source-gate-d117-v1"

APPROVAL_RECORDED_AT = "2026-08-07T09:27:15.522350Z"
PREFLIGHT_RECORDED_AT = "2026-08-07T09:27:16Z"
CANDIDATE_RECORDED_AT = "2026-08-07T09:27:17Z"
GATE_RECORDED_AT = "2026-08-07T09:27:18Z"

DEFAULT_RECEIPT_PATH = Path(
    "reports/memory-development/d117-blind-control-acquisition-protocol-approval-receipt.json"
)
DEFAULT_PREFLIGHT_PATH = Path(
    "reports/memory-development/d117-blind-control-acquisition-protocol-preflight.json"
)
DEFAULT_CANDIDATE_PATH = Path(
    "reports/memory-development/"
    "d117-blind-control-acquisition-protocol-authorization-candidate.json"
)
DEFAULT_SOURCE_GATE_PATH = Path(
    "reports/memory-development/d117-blind-control-acquisition-protocol-source-gate.json"
)

D117_IMPLEMENTATION_PATHS = (
    Path("patchloop/memory/d117_blind_control_acquisition_protocol.py"),
    Path("scripts/build_d117_blind_control_acquisition_protocol_candidate.py"),
    Path("tests/test_d117_blind_control_acquisition_protocol.py"),
)

D116_RECEIPT_PATH = Path(
    "reports/memory-development/d116-public-failure-class-signal-approval-receipt.json"
)
D116_PREFLIGHT_PATH = Path(
    "reports/memory-development/d116-public-failure-class-signal-preflight.json"
)
D116_CANDIDATE_PATH = Path(
    "reports/memory-development/d116-public-failure-class-signal-calibration-candidate.json"
)
D116_SOURCE_GATE_PATH = Path(
    "reports/memory-development/d116-public-failure-class-signal-source-gate.json"
)

EXPECTED_D116_RECEIPT_ID = (
    "d116approval_016c99bd81a756f640cf10132eda196057cb3a50a59cf593d64e215dc4d47bcb"
)
EXPECTED_D116_RECEIPT_BODY_SHA = (
    "sha256:016c99bd81a756f640cf10132eda196057cb3a50a59cf593d64e215dc4d47bcb"
)
EXPECTED_D116_RECEIPT_BYTES = 12_014
EXPECTED_D116_RECEIPT_FILE_SHA = (
    "sha256:86c4e279df6c3d4b6ea02719375f76370d76fb795d642f2d10211e878662ba77"
)
EXPECTED_D116_PREFLIGHT_ID = (
    "d116preflight_e9005e90895ea4554ea04b21b025ff1afc42076d4e08a7adef2b6476cbf06a3f"
)
EXPECTED_D116_PREFLIGHT_BODY_SHA = (
    "sha256:e9005e90895ea4554ea04b21b025ff1afc42076d4e08a7adef2b6476cbf06a3f"
)
EXPECTED_D116_PREFLIGHT_BYTES = 76_157
EXPECTED_D116_PREFLIGHT_FILE_SHA = (
    "sha256:fc2602a385242204ab9ae274ea6c73a83bd00a00eace88c7f310a57b5d4655f5"
)
EXPECTED_D116_CANDIDATE_ID = (
    "d116classsignalcandidate_0b1b700af4ce2274cb9cb032ecf23c741ec9c41b0e86abbc06e96e18f91c74d4"
)
EXPECTED_D116_CANDIDATE_BODY_SHA = (
    "sha256:0b1b700af4ce2274cb9cb032ecf23c741ec9c41b0e86abbc06e96e18f91c74d4"
)
EXPECTED_D116_CANDIDATE_BYTES = 8_017
EXPECTED_D116_CANDIDATE_FILE_SHA = (
    "sha256:8299f3d400bd9412a8b7100305a0eb57f1d5b4ea78a39d8e5edad6cd5a2b15ca"
)
EXPECTED_D116_GATE_ID = "d116_e93b1d39428c3778dd1f55dd0ae1a6c7f4b2091f9b4a92c347f6b7b3c6a66c37"
EXPECTED_D116_GATE_BODY_SHA = (
    "sha256:e93b1d39428c3778dd1f55dd0ae1a6c7f4b2091f9b4a92c347f6b7b3c6a66c37"
)
EXPECTED_D116_GATE_BYTES = 19_859
EXPECTED_D116_GATE_FILE_SHA = (
    "sha256:f03bc7806d8401b9ac9f3d9e47df7b0ef19b16a04380bed1c9cb1d105e52320d"
)
EXPECTED_D116_ACTION_HASH = (
    "sha256:e368dcb794875064f605a341902b4c27be20fcb3ff9b86d65ca5fb66dbf35e55"
)
EXPECTED_D116_CUTOFF = "2026-08-07T06:22:51.021003Z"
EXPECTED_D116_TAXONOMY_HASH = (
    "sha256:910b02269b16d8277a48dfd0353724e06c5aea988874b9dcb89e062cd1508b45"
)
EXPECTED_D116_GRAMMAR_HASH = (
    "sha256:c9e88df2d48ea1d089da11ec394fd41daa2d3e377b3058899e9f530b51548bf1"
)

D105_GATE_PATH = Path(
    "reports/memory-development/d105-renderer-embedding-index-authorization-gate.json"
)
EXPECTED_D105_GATE_ID = "d105_0f99c7d1cd1c371191073ead8d60636be9ea6040947d9c7f3522aba25bc3df70"
EXPECTED_D105_GATE_BODY_SHA = (
    "sha256:0f99c7d1cd1c371191073ead8d60636be9ea6040947d9c7f3522aba25bc3df70"
)
EXPECTED_D105_GATE_BYTES = 12_368
EXPECTED_D105_GATE_FILE_SHA = (
    "sha256:db6303f3de834b3c36493f2863dcc5be3ca697490d18df15c86a18e7ee7b17eb"
)
EXPECTED_D105_RENDER_SET_HASH = (
    "sha256:7b72fc94642d996fad5a0b199719c56bfecc8a8fc1bbe42b2060aa18e21d2667"
)

D105_RUBRIC_SPECS = (
    {
        "order": 1,
        "path": (
            "reports/memory-development/rendered/d105/memgrp_649483b80292fea26e4009ebdb72df31.txt"
        ),
        "semantic_group_id": "platform-emulation-matrix-gap",
        "file_bytes": 1_191,
        "file_sha256": ("sha256:f1cd44ed10d527ff7f5c44dd0be4e6957810530cd055d3329da0d7962d3cec7c"),
    },
    {
        "order": 2,
        "path": (
            "reports/memory-development/rendered/d105/memgrp_b421547d481faabf9be3511217258de5.txt"
        ),
        "semantic_group_id": "request-context-propagation-gap",
        "file_bytes": 1_164,
        "file_sha256": ("sha256:ab0273b575f76efd4ca9facda9540d87f2ea85e69a333cf87e4d7ac781287c2a"),
    },
    {
        "order": 3,
        "path": (
            "reports/memory-development/rendered/d105/memgrp_5a23f463cba43bf3ba395f67cf976047.txt"
        ),
        "semantic_group_id": "exception-origin-state-conflation",
        "file_bytes": 1_161,
        "file_sha256": ("sha256:00ceca8ed912a48f36ab26fb50b1d7eb428fe261a83b2bd84e231f0c6e786bf7"),
    },
)

PROTECTED_FILE_SPECS = (
    {
        "path": D116_RECEIPT_PATH.as_posix(),
        "file_bytes": EXPECTED_D116_RECEIPT_BYTES,
        "file_sha256": EXPECTED_D116_RECEIPT_FILE_SHA,
    },
    {
        "path": D116_PREFLIGHT_PATH.as_posix(),
        "file_bytes": EXPECTED_D116_PREFLIGHT_BYTES,
        "file_sha256": EXPECTED_D116_PREFLIGHT_FILE_SHA,
    },
    {
        "path": D116_CANDIDATE_PATH.as_posix(),
        "file_bytes": EXPECTED_D116_CANDIDATE_BYTES,
        "file_sha256": EXPECTED_D116_CANDIDATE_FILE_SHA,
    },
    {
        "path": D116_SOURCE_GATE_PATH.as_posix(),
        "file_bytes": EXPECTED_D116_GATE_BYTES,
        "file_sha256": EXPECTED_D116_GATE_FILE_SHA,
    },
    {
        "path": "patchloop/memory/d116_public_failure_class_signal_contract.py",
        "file_bytes": 106_302,
        "file_sha256": ("sha256:8244e1b5c23ea73e6be4e58ad8c4980251d6bb2be51f92e2c1ca8393172ca530"),
    },
    {
        "path": "scripts/build_d116_public_failure_class_signal_candidate.py",
        "file_bytes": 1_883,
        "file_sha256": ("sha256:1f462e51e706da543f99ed3ac0aa79cf07001711b9b13162ff63a7f45e3c33b9"),
    },
    {
        "path": "tests/test_d116_public_failure_class_signal_contract.py",
        "file_bytes": 37_436,
        "file_sha256": ("sha256:8afaf76ef5cadebec52e9d35ceb465080351d85667d210ae3069728fa5e8b3d2"),
    },
    {
        "path": D105_GATE_PATH.as_posix(),
        "file_bytes": EXPECTED_D105_GATE_BYTES,
        "file_sha256": EXPECTED_D105_GATE_FILE_SHA,
    },
    *(
        {
            "path": str(spec["path"]),
            "file_bytes": int(spec["file_bytes"]),
            "file_sha256": str(spec["file_sha256"]),
        }
        for spec in D105_RUBRIC_SPECS
    ),
)

RECEIPT_ROOT_KEYS = ("schema_version", "receipt_id", "semantic_body_hash", "semantic_body")
PREFLIGHT_ROOT_KEYS = (
    "schema_version",
    "preflight_id",
    "semantic_body_hash",
    "semantic_body",
)
CANDIDATE_ROOT_KEYS = (
    "schema_version",
    "candidate_id",
    "semantic_body_hash",
    "semantic_body",
)
GATE_ROOT_KEYS = ("schema_version", "gate_id", "semantic_body_hash", "semantic_body")

RECEIPT_BODY_KEYS = (
    "milestone",
    "evidence_kind",
    "approval_recorded_at",
    "approval_action_id",
    "approval_reference",
    "approval_reference_mode",
    "approval_statement_code",
    "d116_source_gate",
    "d116_candidate",
    "authorized_action_hash",
    "authorized_scope",
    "materialization_scope",
    "protected_pre_state",
    "implementation_pre_state",
    "claim_semantics",
    "self_attested",
    "approver_kind",
    "approver_label",
    "reviewer_identity_authenticated",
    "cryptographic_signature_verified",
    "execution_result_present",
)
PREFLIGHT_BODY_KEYS = (
    "milestone",
    "evidence_kind",
    "recorded_at",
    "approval_receipt",
    "d116_source_gate",
    "d116_candidate",
    "input_scope",
    "predecessor_contract_binding",
    "cutoff_and_preexistence_contract",
    "d105_rubric_contract",
    "role_separation_contract",
    "chain_of_custody_contract",
    "independence_and_fallback_contract",
    "future_artifact_contracts",
    "prospective_execution_plan",
    "protected_pre_state",
    "evidence_boundary",
    "authority",
)
CANDIDATE_BODY_KEYS = (
    "milestone",
    "evidence_kind",
    "recorded_at",
    "approval_receipt",
    "preflight",
    "protocol_component_hashes",
    "candidate_status",
    "unresolved_prerequisites",
    "proposed_next_action",
    "proposed_next_action_hash",
    "approval_contract",
    "authority",
)
GATE_BODY_KEYS = (
    "milestone",
    "evidence_kind",
    "recorded_at",
    "approval_receipt",
    "d116_source_gate",
    "d116_candidate",
    "preflight",
    "protocol_candidate",
    "implementation_files",
    "protected_input_integrity",
    "qualification",
    "evidence_boundary",
    "authority",
    "next_gate",
)


class D117BlindProtocolError(ContractError):
    """Raised when D-117 scope, predecessor bytes, or protocol artifacts drift."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise D117BlindProtocolError(message)


def _repo_root(repository: str | Path | None) -> Path:
    selected = Path(repository) if repository is not None else Path(__file__).resolve().parents[2]
    try:
        return selected.resolve(strict=True)
    except OSError as exc:
        raise D117BlindProtocolError("D-117 repository root cannot be resolved") from exc


def _is_linklike(path: Path) -> bool:
    try:
        info = path.lstat()
    except OSError:
        return False
    attributes = getattr(info, "st_file_attributes", 0)
    junction = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return stat.S_ISLNK(info.st_mode) or bool(attributes & junction)


def _resolved(
    relative: str | Path,
    *,
    repository: Path,
    label: str,
    must_exist: bool = True,
) -> Path:
    raw = Path(relative)
    _require(not raw.is_absolute(), f"D-117 {label} must be repository-relative")
    candidate = repository / raw
    try:
        selected = candidate.resolve(strict=must_exist)
        selected.relative_to(repository)
    except (OSError, ValueError) as exc:
        raise D117BlindProtocolError(f"D-117 {label} escapes or is missing") from exc
    current = candidate
    while current != repository:
        _require(not _is_linklike(current), f"D-117 {label} cannot use a link or junction")
        current = current.parent
    return selected


def _read_stable(path: Path, *, label: str) -> bytes:
    try:
        path_before = path.stat()
        with path.open("rb") as handle:
            descriptor_before = os.fstat(handle.fileno())
            content = handle.read()
            descriptor_after = os.fstat(handle.fileno())
        path_after = path.stat()
    except OSError as exc:
        raise D117BlindProtocolError(f"D-117 {label} cannot be read") from exc
    identity_before = (
        getattr(path_before, "st_dev", None),
        getattr(path_before, "st_ino", None),
        path_before.st_size,
        path_before.st_mtime_ns,
    )
    descriptor_identity_before = (
        getattr(descriptor_before, "st_dev", None),
        getattr(descriptor_before, "st_ino", None),
        descriptor_before.st_size,
        descriptor_before.st_mtime_ns,
    )
    descriptor_identity_after = (
        getattr(descriptor_after, "st_dev", None),
        getattr(descriptor_after, "st_ino", None),
        descriptor_after.st_size,
        descriptor_after.st_mtime_ns,
    )
    identity_after = (
        getattr(path_after, "st_dev", None),
        getattr(path_after, "st_ino", None),
        path_after.st_size,
        path_after.st_mtime_ns,
    )
    _require(
        identity_before
        == descriptor_identity_before
        == descriptor_identity_after
        == identity_after,
        f"D-117 {label} changed identity or metadata while being read",
    )
    _require(len(content) == path_after.st_size, f"D-117 {label} read length mismatch")
    return content


def _parse_json(content: bytes, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise D117BlindProtocolError(f"D-117 {label} is not valid UTF-8 JSON") from exc
    _require(isinstance(value, dict), f"D-117 {label} root must be an object")
    return value


def _pretty_json(payload: Mapping[str, Any]) -> bytes:
    return (json.dumps(payload, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def _require_exact_keys(value: Any, expected: Sequence[str], *, label: str) -> None:
    _require(isinstance(value, dict), f"D-117 {label} must be an object")
    actual = set(value)
    wanted = set(expected)
    _require(
        actual == wanted,
        f"D-117 {label} key set mismatch: missing={sorted(wanted - actual)}, "
        f"unknown={sorted(actual - wanted)}",
    )


def _validate_envelope(
    payload: Mapping[str, Any],
    *,
    root_keys: Sequence[str],
    body_keys: Sequence[str],
    id_field: str,
    id_prefix: str,
    label: str,
) -> Mapping[str, Any]:
    _require_exact_keys(payload, root_keys, label=f"{label} root")
    body = payload.get("semantic_body")
    _require_exact_keys(body, body_keys, label=f"{label} semantic body")
    body_hash = sha256_text(canonical_json(body))
    _require(payload.get("semantic_body_hash") == body_hash, f"D-117 {label} body hash mismatch")
    _require(
        payload.get(id_field) == id_prefix + body_hash.removeprefix("sha256:"),
        f"D-117 {label} identifier mismatch",
    )
    return body


def _load_exact_json(
    relative: str | Path,
    *,
    repository: Path,
    expected_bytes: int,
    expected_sha: str,
    label: str,
) -> tuple[dict[str, Any], bytes]:
    selected = _resolved(relative, repository=repository, label=label)
    content = _read_stable(selected, label=label)
    _require(
        len(content) == expected_bytes and sha256_bytes(content) == expected_sha,
        f"D-117 {label} exact file binding mismatch",
    )
    return _parse_json(content, label=label), content


def _file_binding(relative: str | Path, *, repository: Path, label: str) -> dict[str, Any]:
    selected = _resolved(relative, repository=repository, label=label)
    content = _read_stable(selected, label=label)
    return {
        "path": selected.relative_to(repository).as_posix(),
        "file_bytes": len(content),
        "file_sha256": sha256_bytes(content),
    }


def _artifact_binding(
    relative: str | Path,
    *,
    repository: Path,
    payload: Mapping[str, Any],
    content: bytes,
    id_field: str,
) -> dict[str, Any]:
    selected = _resolved(relative, repository=repository, label="bound artifact")
    return {
        "path": selected.relative_to(repository).as_posix(),
        "file_bytes": len(content),
        "file_sha256": sha256_bytes(content),
        "schema_version": payload["schema_version"],
        id_field: payload[id_field],
        "semantic_body_hash": payload["semantic_body_hash"],
    }


def _output_binding(
    relative: str | Path,
    *,
    repository: Path,
    payload: Mapping[str, Any],
    id_field: str,
) -> dict[str, Any]:
    selected = _resolved(relative, repository=repository, label="D-117 output", must_exist=False)
    content = _pretty_json(payload)
    return {
        "path": selected.relative_to(repository).as_posix(),
        "file_bytes": len(content),
        "file_sha256": sha256_bytes(content),
        "schema_version": payload["schema_version"],
        id_field: payload[id_field],
        "semantic_body_hash": payload["semantic_body_hash"],
    }


def _protected_input_state(repository: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    seen_paths: set[str] = set()
    seen_identities: set[tuple[Any, Any]] = set()
    for spec in PROTECTED_FILE_SPECS:
        binding = _file_binding(spec["path"], repository=repository, label="protected input")
        normalized = binding["path"].casefold()
        selected = _resolved(spec["path"], repository=repository, label="protected input")
        info = selected.stat()
        identity = (
            getattr(info, "st_dev", None),
            getattr(info, "st_ino", None),
        )
        _require(normalized not in seen_paths, "D-117 protected path alias collision")
        _require(identity not in seen_identities, "D-117 protected inode alias collision")
        seen_paths.add(normalized)
        seen_identities.add(identity)
        _require(
            binding["file_bytes"] == spec["file_bytes"]
            and binding["file_sha256"] == spec["file_sha256"],
            f"D-117 protected input drifted: {spec['path']}",
        )
        rows.append(binding)
    return {"files": rows, "fingerprint": sha256_text(canonical_json(rows))}


def _implementation_state(repository: Path) -> dict[str, Any]:
    rows = [
        _file_binding(path, repository=repository, label="D-117 implementation")
        for path in D117_IMPLEMENTATION_PATHS
    ]
    return {"files": rows, "fingerprint": sha256_text(canonical_json(rows))}


def _load_exact_context(repository: Path) -> dict[str, Any]:
    receipt, receipt_content = _load_exact_json(
        D116_RECEIPT_PATH,
        repository=repository,
        expected_bytes=EXPECTED_D116_RECEIPT_BYTES,
        expected_sha=EXPECTED_D116_RECEIPT_FILE_SHA,
        label="D-116 approval receipt",
    )
    preflight, preflight_content = _load_exact_json(
        D116_PREFLIGHT_PATH,
        repository=repository,
        expected_bytes=EXPECTED_D116_PREFLIGHT_BYTES,
        expected_sha=EXPECTED_D116_PREFLIGHT_FILE_SHA,
        label="D-116 preflight",
    )
    candidate, candidate_content = _load_exact_json(
        D116_CANDIDATE_PATH,
        repository=repository,
        expected_bytes=EXPECTED_D116_CANDIDATE_BYTES,
        expected_sha=EXPECTED_D116_CANDIDATE_FILE_SHA,
        label="D-116 candidate",
    )
    gate, gate_content = _load_exact_json(
        D116_SOURCE_GATE_PATH,
        repository=repository,
        expected_bytes=EXPECTED_D116_GATE_BYTES,
        expected_sha=EXPECTED_D116_GATE_FILE_SHA,
        label="D-116 source gate",
    )
    _require(
        receipt.get("receipt_id") == EXPECTED_D116_RECEIPT_ID
        and receipt.get("semantic_body_hash") == EXPECTED_D116_RECEIPT_BODY_SHA,
        "D-117 exact D-116 receipt identity mismatch",
    )
    _require(
        preflight.get("preflight_id") == EXPECTED_D116_PREFLIGHT_ID
        and preflight.get("semantic_body_hash") == EXPECTED_D116_PREFLIGHT_BODY_SHA,
        "D-117 exact D-116 preflight identity mismatch",
    )
    _require(
        candidate.get("candidate_id") == EXPECTED_D116_CANDIDATE_ID
        and candidate.get("semantic_body_hash") == EXPECTED_D116_CANDIDATE_BODY_SHA,
        "D-117 exact D-116 candidate identity mismatch",
    )
    _require(
        gate.get("gate_id") == EXPECTED_D116_GATE_ID
        and gate.get("semantic_body_hash") == EXPECTED_D116_GATE_BODY_SHA,
        "D-117 exact D-116 source-gate identity mismatch",
    )

    candidate_body = candidate.get("semantic_body")
    _require(isinstance(candidate_body, dict), "D-117 D-116 candidate body missing")
    authorized_scope = candidate_body.get("proposed_next_action")
    _require(isinstance(authorized_scope, dict), "D-117 D-116 authorized scope missing")
    _require(
        sha256_text(canonical_json(authorized_scope)) == EXPECTED_D116_ACTION_HASH
        and candidate_body.get("proposed_next_action_hash") == EXPECTED_D116_ACTION_HASH,
        "D-117 D-116 authorized action hash mismatch",
    )
    required_scope = {
        "action_kind": (
            "prepare-grammar-blind-preexisting-public-applicability-control-acquisition-"
            "protocol-candidate"
        ),
        "future_milestone": MILESTONE,
        "public_development_inputs_only": True,
        "source_pool_must_preexist_d116": True,
        "source_pool_cutoff_must_precede": EXPECTED_D116_CUTOFF,
        "pool_assembler_may_view_matcher_grammar_hash_or_output": False,
        "selector_or_adjudicator_may_view_matcher_grammar_or_hash": False,
        "current_process_or_agent_eligible_as_blind_selector": False,
        "classifier_implementation_allowed": False,
        "classifier_execution_allowed": False,
        "calibration_execution_allowed": False,
        "score_policy_mutation_allowed": False,
        "retrieval_or_runtime_injection_allowed": False,
        "agent_provider_evaluator_or_network_allowed": False,
        "core_or_analysis_campaign_allowed": False,
    }
    _require(
        all(authorized_scope.get(key) == value for key, value in required_scope.items()),
        "D-117 D-116 authorized scope expanded or drifted",
    )
    contract_binding = candidate_body.get("contract_binding")
    _require(isinstance(contract_binding, dict), "D-117 D-116 contract binding missing")
    _require(
        contract_binding.get("taxonomy_contract_hash") == EXPECTED_D116_TAXONOMY_HASH
        and contract_binding.get("predicate_contract_hash") == EXPECTED_D116_GRAMMAR_HASH,
        "D-117 D-116 taxonomy or grammar binding drifted",
    )
    _require(
        preflight.get("semantic_body", {})
        .get("prospective_predicate_contract", {})
        .get("formal_matcher_grammar_complete")
        is True,
        "D-117 D-116 grammar seal is not complete",
    )
    gate_body = gate.get("semantic_body")
    _require(isinstance(gate_body, dict), "D-117 D-116 source-gate body missing")
    gate_candidate = gate_body.get("calibration_candidate")
    _require(
        isinstance(gate_candidate, dict)
        and gate_candidate.get("candidate_id") == EXPECTED_D116_CANDIDATE_ID
        and gate_candidate.get("semantic_body_hash") == EXPECTED_D116_CANDIDATE_BODY_SHA
        and gate_candidate.get("file_sha256") == EXPECTED_D116_CANDIDATE_FILE_SHA,
        "D-117 D-116 gate-to-candidate binding drifted",
    )
    gate_authority = gate_body.get("authority")
    _require(
        isinstance(gate_authority, dict)
        and gate_authority.get("classifier_execution_count") == 0
        and gate_authority.get("calibration_execution_count") == 0
        and gate_authority.get("retrieval_ready") is False
        and gate_authority.get("core_campaign_unlocked") is False,
        "D-117 predecessor authority is not closed",
    )

    d105_gate, d105_gate_content = _load_exact_json(
        D105_GATE_PATH,
        repository=repository,
        expected_bytes=EXPECTED_D105_GATE_BYTES,
        expected_sha=EXPECTED_D105_GATE_FILE_SHA,
        label="D-105 render gate",
    )
    _require(
        d105_gate.get("gate_id") == EXPECTED_D105_GATE_ID
        and d105_gate.get("semantic_body_hash") == EXPECTED_D105_GATE_BODY_SHA,
        "D-117 exact D-105 gate identity mismatch",
    )
    d105_body = d105_gate.get("semantic_body")
    _require(isinstance(d105_body, dict), "D-117 D-105 body missing")
    _require(
        d105_body.get("render_set_hash") == EXPECTED_D105_RENDER_SET_HASH,
        "D-117 D-105 rubric set hash mismatch",
    )
    recorded_entries = d105_body.get("entries")
    _require(isinstance(recorded_entries, list), "D-117 D-105 entries missing")
    rubrics: list[dict[str, Any]] = []
    for spec in D105_RUBRIC_SPECS:
        matching = [
            row
            for row in recorded_entries
            if isinstance(row, dict) and row.get("semantic_group_id") == spec["semantic_group_id"]
        ]
        _require(len(matching) == 1, "D-117 D-105 rubric membership drifted")
        row = matching[0]
        _require(
            row.get("order") == spec["order"]
            and row.get("path") == spec["path"]
            and row.get("file_bytes") == spec["file_bytes"]
            and row.get("file_sha256") == spec["file_sha256"],
            f"D-117 D-105 rubric binding drifted: {spec['semantic_group_id']}",
        )
        selected = _resolved(spec["path"], repository=repository, label="D-105 rubric")
        content = _read_stable(selected, label="D-105 rubric")
        _require(
            len(content) == spec["file_bytes"] and sha256_bytes(content) == spec["file_sha256"],
            f"D-117 D-105 rubric bytes drifted: {spec['semantic_group_id']}",
        )
        rubrics.append(
            {
                "order": spec["order"],
                "semantic_group_id": spec["semantic_group_id"],
                "path": spec["path"],
                "file_bytes": len(content),
                "file_sha256": sha256_bytes(content),
            }
        )
    _require(
        [row["order"] for row in rubrics] == [1, 2, 3],
        "D-117 D-105 rubric order drifted",
    )
    return {
        "repository": repository,
        "d116_receipt": receipt,
        "d116_receipt_content": receipt_content,
        "d116_preflight": preflight,
        "d116_preflight_content": preflight_content,
        "d116_candidate": candidate,
        "d116_candidate_content": candidate_content,
        "d116_gate": gate,
        "d116_gate_content": gate_content,
        "authorized_scope": authorized_scope,
        "d105_gate": d105_gate,
        "d105_gate_content": d105_gate_content,
        "rubrics": rubrics,
    }


def _cutoff_and_preexistence_contract() -> dict[str, Any]:
    return {
        "contract_version": "pre-d116-byte-and-membership-proof-d117-v1",
        "source_pool_scope": "public-development-controls-only",
        "held_out_task_issue_or_result_membership_allowed": False,
        "private_hidden_reference_patch_trace_or_evaluator_membership_allowed": False,
        "d116_cutoff_exclusive": EXPECTED_D116_CUTOFF,
        "strict_relation_required": "proof_anchor_timestamp < d116_cutoff_exclusive",
        "source_issue_created_before_cutoff_alone_is_sufficient": False,
        "exact_source_bytes_must_credibly_predate_cutoff": True,
        "membership_basis_must_credibly_predate_cutoff": True,
        "membership_basis_domain": [
            "exact-byte-frozen-membership-manifest",
            "byte-frozen-grammar-independent-exhaustive-inclusion-rule",
        ],
        "membership_or_rule_authored_after_d116_allowed": False,
        "post_cutoff_issue_prose_rewrite_allowed": False,
        "current_fetch_or_newly_computed_hash_is_retroactive_preexistence_proof": False,
        "filesystem_mtime_is_preexistence_proof": False,
        "git_author_or_committer_timestamp_alone_is_preexistence_proof": False,
        "self_attested_created_at_alone_is_preexistence_proof": False,
        "acceptable_external_anchor_kinds": [
            "pre-cutoff-transparency-log-or-trusted-timestamp",
            "pre-cutoff-signed-release-or-signed-tag-with-exact-content-binding",
            "pre-cutoff-independent-immutable-archive-with-exact-content-binding",
            "pre-cutoff-externally-sealed-content-and-membership-hash",
        ],
        "pool_membership_or_exhaustive_rule_must_be_frozen_before_grammar_seal": True,
        "pool_assembler_must_not_choose_among_multiple_post-hoc-subsets": True,
        "neutral_exhaustive_rule_or_precommitted_seed_required": True,
        "actual_source_pool_identified": False,
        "actual_source_pool_read_count": 0,
        "actual_source_pool_frozen": False,
        "trusted_cutoff_anchor_verified": False,
        "pre_d116_membership_verified": False,
    }


def _d105_rubric_contract(context: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "contract_version": "exact-d105-applicability-rubric-packet-d117-v1",
        "rubric_source_kind": "leak-scanned-model-facing-render",
        "d105_gate": _artifact_binding(
            D105_GATE_PATH,
            repository=context["repository"],
            payload=context["d105_gate"],
            content=context["d105_gate_content"],
            id_field="gate_id",
        ),
        "ordered_render_set_hash": EXPECTED_D105_RENDER_SET_HASH,
        "group_count": 3,
        "groups": list(context["rubrics"]),
        "reviewer_instruction_basis": ["Apply when", "Do not apply when"],
        "d116_regex_predicate_or_synthetic_case_in_packet": False,
        "d116_source_anchor_expectation_in_packet": False,
        "d112_moto_hypothesis_in_packet": False,
        "tox_source_association_in_packet": False,
        "task_or_repository_identity_in_packet": False,
        "rubric_is_public_applicability_guidance_not_failure_cause_ground_truth": True,
    }


def _role_separation_contract() -> dict[str, Any]:
    return {
        "contract_version": "capability-separated-blind-review-roles-d117-v1",
        "current_protocol_author_or_current_conversation_actor_is_blind_role_eligible": False,
        "same_checkout_subagent_is_technical_isolation": False,
        "prompt_only_blinding_or_self_attestation_is_technical_isolation": False,
        "one_principal_may_hold_multiple_blind_roles": False,
        "roles": [
            {
                "role": "provenance-verifier",
                "allowed_inputs": [
                    "neutral-cutoff-token",
                    "historical-source-snapshot-and-anchor",
                    "preexisting-membership-manifest-or-exhaustive-rule",
                ],
                "forbidden_inputs": [
                    "d105-rubric",
                    "d116-grammar-hash-or-output",
                    "task-expectations-or-labels",
                ],
                "may_label_applicability": False,
            },
            {
                "role": "pool-assembler",
                "allowed_inputs": [
                    "neutral-cutoff-token",
                    "verified-historical-public-development-archive",
                    "verified-pre-d116-membership-manifest-or-exhaustive-rule",
                    "public-projection-schema-without-rubric",
                ],
                "forbidden_inputs": [
                    "d105-rubric",
                    "d116-grammar-regex-hash-output-or-expectations",
                    "d112-hypotheses",
                    "current-repository-docs-traces-memory-index-or-task-labels",
                ],
                "may_label_applicability": False,
            },
            {
                "role": "blinding-broker",
                "allowed_inputs": [
                    "frozen-pool-manifest",
                    "canonical-public-projection",
                ],
                "forbidden_inputs": [
                    "d105-rubric",
                    "d116-grammar-or-output",
                    "labels",
                ],
                "may_label_applicability": False,
            },
            {
                "role": "selector-a",
                "allowed_inputs": [
                    "opaque-control-id",
                    "canonical-issue-title-description-language",
                    "exact-d105-applicability-rubric",
                ],
                "forbidden_inputs": [
                    "upstream-repository-task-path-or-lineage-identity",
                    "d116-grammar-regex-hash-output-or-expectations",
                    "source-anchor-marker-d112-hypothesis-or-tox-association",
                    "selector-b-or-adjudicator-result-before-own-result-seal",
                ],
                "may_label_applicability": True,
            },
            {
                "role": "selector-b",
                "allowed_inputs": [
                    "opaque-control-id",
                    "canonical-issue-title-description-language",
                    "exact-d105-applicability-rubric",
                ],
                "forbidden_inputs": [
                    "upstream-repository-task-path-or-lineage-identity",
                    "d116-grammar-regex-hash-output-or-expectations",
                    "source-anchor-marker-d112-hypothesis-or-tox-association",
                    "selector-a-or-adjudicator-result-before-own-result-seal",
                ],
                "may_label_applicability": True,
            },
            {
                "role": "adjudicator",
                "allowed_inputs": [
                    "opaque-control-id",
                    "canonical-issue-title-description-language",
                    "exact-d105-applicability-rubric",
                ],
                "forbidden_inputs": [
                    "d116-grammar-regex-hash-output-or-expectations",
                    "selector-results-before-independent-first-pass-seal",
                    "source-or-task-identity-and-private-evidence",
                ],
                "may_label_applicability": True,
            },
            {
                "role": "independence-auditor",
                "allowed_inputs": [
                    "provenance-and-membership-manifests",
                    "role-input-allowlists-and-access-logs",
                    "sealed-role-output-bindings",
                ],
                "forbidden_inputs": ["label-authoring-or-matcher-tuning-authority"],
                "may_label_applicability": False,
            },
            {
                "role": "future-matcher-evaluator",
                "allowed_inputs": ["only-after-label-freeze-d116-grammar-and-sealed-gold-packet"],
                "forbidden_inputs": ["participation-in-label-generation"],
                "may_label_applicability": False,
            },
        ],
        "isolation_profile": {
            "separate_clean_container_vm_or_os_identity_required": True,
            "repository_git_agents_docs_d112_through_d116_trace_patch_index_mount_allowed": False,
            "exact_input_allowlist_read_only_mount_required": True,
            "single_role_output_directory_only_writable": True,
            "network_mode": "none",
            "read_only_root_filesystem_required": True,
            "non_root_identity_required": True,
            "all_capabilities_dropped": True,
            "no_new_privileges_required": True,
            "environment_allowlist_required": True,
            "image_digest_argv_mount_env_input_output_hash_receipt_required": True,
            "unexpected_path_symlink_junction_or_hash_drift_fails_closed": True,
            "human_prior_knowledge_cryptographically_excluded": False,
            "maximum_honest_claim": "process-isolated-not-human-knowledge-proof",
        },
        "actual_role_assignments": 0,
        "actual_role_invocations": 0,
        "actual_isolation_sessions": 0,
    }


def _chain_of_custody_contract() -> dict[str, Any]:
    return {
        "contract_version": "append-only-public-control-chain-d117-v1",
        "future_pool_manifest_required_fields": [
            "source_collection_and_version",
            "public-development-eligibility-and-split-role",
            "held-out-and-private-lineage-exclusion",
            "source_snapshot_path_bytes_sha256_and_cutoff_anchor",
            "preexisting_membership_manifest_or_exhaustive_rule_bytes_sha256",
            "deterministic_included_and_excluded_record_ledger",
            "original_public_record_bytes_sha256",
            "canonical_title_description_language_projection_sha256",
            "upstream_stable_id",
            "issue_pr_fix_lineage_family_id",
            "deterministic_member_order",
            "collection_root_hash",
            "d104_d105_source_lineage_overlap",
            "d116_ten-task-panel_or_duplicate-lineage_overlap",
        ],
        "future_role_session_receipt_required_fields": [
            "role",
            "isolated_principal_id",
            "container_or_vm_image_digest",
            "argv",
            "read_only_mount_allowlist",
            "writable_output_path",
            "environment_allowlist",
            "network_none",
            "input_file_bindings",
            "output_file_bindings",
            "access_log_binding",
            "started_at",
            "completed_at",
        ],
        "future_blind_packet_required_fields": [
            "opaque_control_id",
            "canonical_public_projection",
            "canonical_projection_sha256",
            "exact_d105_rubric_set_hash",
        ],
        "future_blind_packet_forbidden_fields": [
            "task_id",
            "repository_url_or_name",
            "base_commit_or_path",
            "source_anchor_or_expected_group",
            "d112_hypothesis",
            "d116_matcher_grammar_regex_hash_output_or_expectation",
            "private_hidden_reference_patch_trace_or_evaluator_result",
        ],
        "selector_result_domain": [
            "SELECT:platform-emulation-matrix-gap",
            "SELECT:request-context-propagation-gap",
            "SELECT:exception-origin-state-conflation",
            "ABSTAIN:INSUFFICIENT_PUBLIC_EVIDENCE",
            "ABSTAIN:AMBIGUOUS_MULTIPLE_GROUPS",
            "ABSTAIN:CONTRADICTED_BY_DO_NOT_APPLY",
            "INVALID_PUBLIC_INPUT",
        ],
        "result_must_bind_projection_and_rubric_hashes": True,
        "evidence_spans_must_validate_against_exact_canonical_public_bytes": True,
        "free_text_external_knowledge_field_allowed": False,
        "selector_a_b_and_adjudicator_first_pass_must_be_independently_sealed": True,
        "cross_reveal_before_all_first_pass_seals_allowed": False,
        "append_only_correction_chain_required": True,
        "existing_pool_or_role_output_in_place_mutation_allowed": False,
        "missing_access_log_or_binding_drift_fails_closed": True,
        "actual_future_artifact_count": 0,
    }


def _independence_and_fallback_contract() -> dict[str, Any]:
    return {
        "contract_version": "blind-public-applicability-independence-d117-v1",
        "independent_positive_logic": [
            "pre-d116-source-bytes-and-membership-proof-valid",
            "member-not-in-d104-or-d105-source-lineage",
            "member-not-in-d116-ten-task-panel-or-duplicate-lineage",
            "pool-assembler-and-session-blinding-valid",
            "selector-a-and-selector-b-first-pass-results-independently-sealed",
            "adjudicator-first-pass-result-sealed-before-cross-reveal",
            "selector-a-selector-b-and-adjudicator-select-same-single-group",
            "all-public-evidence-spans-validate",
            "no-d105-do-not-apply-contradiction",
        ],
        "all_logic_terms_required": True,
        "source_anchor_sanity_case_counts_as_independent": False,
        "matcher_author_synthetic_case_counts_as_independent": False,
        "abstention_counts_as_negative_failure_class_ground_truth": False,
        "failure_fallback": {
            "post_hoc": True,
            "independent": False,
            "eligible_for_independent_calibration": False,
            "reason_code_required": True,
            "records_preserved_append_only": True,
        },
        "failure_reason_code_domain": [
            "PRE_D116_SOURCE_BYTES_PROOF_MISSING",
            "PRE_D116_MEMBERSHIP_PROOF_MISSING",
            "TRUSTED_CUTOFF_ANCHOR_MISSING",
            "LIVE_CURRENT_FETCH_ONLY",
            "POST_CUTOFF_CONTENT_OR_MEMBERSHIP_CHANGE",
            "POOL_ASSEMBLER_FORBIDDEN_VISIBILITY",
            "SELECTOR_FORBIDDEN_VISIBILITY",
            "ADJUDICATOR_FORBIDDEN_VISIBILITY",
            "ROLE_PRINCIPAL_OVERLAP",
            "CURRENT_GRAMMAR_OBSERVER_USED_IN_BLIND_ROLE",
            "TECHNICAL_ISOLATION_UNVERIFIED",
            "SOURCE_ANCHOR_OR_D116_PANEL_REUSE",
            "DUPLICATE_LINEAGE",
            "CHAIN_OF_CUSTODY_DRIFT",
            "FIRST_PASS_NOT_SEALED_BEFORE_REVEAL",
            "SELECTOR_OR_ADJUDICATOR_DISAGREEMENT",
            "EVIDENCE_SPAN_INVALID",
            "DO_NOT_APPLY_CONTRADICTION",
            "UNKNOWN_OR_INCOMPLETE_INDEPENDENCE_EVIDENCE",
        ],
        "pool_scope_failure_downgrades_entire_pool": True,
        "role_session_failure_downgrades_all_members_seen_by_session": True,
        "member_scope_failure_downgrades_only_member": True,
        "unknown_evidence_is_independent": False,
        "zero_eligible_controls_is_valid_outcome": True,
        "zero_controls_may_weaken_ontology_or_grammar": False,
        "label_observed_pool_expansion_allowed": False,
        "future_additional_pool_requires_new_prospective_version": True,
        "minimum_positive_per_group_for_future_matcher_evaluation": 1,
        "one_positive_per_group_establishes_three_class_calibration": False,
        "actual_independent_control_count": 0,
        "actual_independent_positive_count": 0,
    }


def _future_artifact_contracts() -> dict[str, Any]:
    return {
        "contract_version": "prospective-d118-plus-artifact-schemas-d117-v1",
        "schemas_are_plan_only": True,
        "materialized_in_d117": False,
        "actual_materialized_count": 0,
        "planned_schemas": [
            {
                "schema": "historical-public-pool-provenance-d118-v1",
                "purpose": "bind-pre-d116-source-and-membership-proof",
            },
            {
                "schema": "frozen-public-control-pool-manifest-d118-v1",
                "purpose": "deterministic-inclusion-exclusion-and-lineage-ledger",
            },
            {
                "schema": "isolated-role-session-receipt-d118-v1",
                "purpose": "capability-and-input-visibility-evidence",
            },
            {
                "schema": "opaque-public-applicability-review-packet-d118-v1",
                "purpose": "identity-free-title-description-language-and-d105-rubric",
            },
            {
                "schema": "sealed-public-applicability-first-pass-result-d118-v1",
                "purpose": "selector-or-adjudicator-independent-first-pass",
            },
            {
                "schema": "public-applicability-independence-audit-d118-v1",
                "purpose": "post-hoc-independent-fallback-decision",
            },
        ],
    }


def _prospective_execution_plan() -> dict[str, Any]:
    return {
        "plan_version": "isolated-preexisting-public-control-acquisition-plan-d117-v1",
        "current_status": "plan-only-no-pool-named-read-or-acquired",
        "ordered_future_steps": [
            "obtain-external-exact-pre-d116-public-development-source-snapshot-and-membership-proof-triples",
            "prepare-separate-exact-d118-execution-authorization-candidate",
            "after-later-exact-execution-approval-run-provenance-verifier-in-isolation",
            "if-and-only-if-proof-valid-run-pool-assembler-without-d105-or-d116",
            "freeze-complete-inclusion-exclusion-and-lineage-manifest",
            "run-blinding-broker-to-create-opaque-public-projection-packets",
            "run-selector-a-selector-b-and-adjudicator-in-separated-sessions",
            "seal-first-pass-results-before-any-cross-reveal",
            "run-independence-auditor-and-apply-fail-closed-fallback",
            "only-after-gold-and-independence-freeze-consider-separate-matcher-evaluation-gate",
        ],
        "d118_candidate_preparation_requires": [
            "exact-d117-candidate-id-body-sha-and-file-sha",
            "exact-external-public-development-source-snapshot-binding",
            "exact-pre-d116-membership-manifest-or-exhaustive-rule-binding",
            "exact-trusted-cutoff-anchor-binding",
            "exact-isolation-profile-binding",
        ],
        "d118_candidate_preparation_would_execute_acquisition": False,
        "actual_pool_or_issue_reads": 0,
        "actual_role_sessions": 0,
        "actual_matcher_classifier_or_calibration_runs": 0,
    }


def _authority(*, candidate_ready: bool) -> dict[str, Any]:
    return {
        "exact_d116_candidate_user_approval_received": True,
        "blind_control_acquisition_protocol_candidate_preparation_authorized": True,
        "blind_control_acquisition_protocol_prepared": True,
        "d116_cutoff_bound": True,
        "exact_d105_rubric_bound": True,
        "blind_control_acquisition_protocol_candidate_ready": candidate_ready,
        "source_pool_discovery_authorized": False,
        "source_pool_acquisition_authorized": False,
        "source_pool_identified": False,
        "source_pool_public_issue_read_count": 0,
        "held_out_public_issue_or_result_read_count": 0,
        "source_pool_acquired": False,
        "source_pool_frozen": False,
        "pool_manifest_count": 0,
        "pool_member_count": 0,
        "trusted_cutoff_anchor_verified": False,
        "pre_d116_membership_verified": False,
        "role_assignment_count": 0,
        "isolation_session_count": 0,
        "blind_packet_count": 0,
        "selector_result_count": 0,
        "adjudication_result_count": 0,
        "independent_control_count": 0,
        "independent_positive_count": 0,
        "matcher_evaluator_implementation_authorized": False,
        "matcher_evaluator_implemented": False,
        "matcher_evaluator_execution_count": 0,
        "classifier_implementation_authorized": False,
        "classifier_implemented": False,
        "classifier_execution_authorized": False,
        "classifier_execution_count": 0,
        "calibration_execution_authorized": False,
        "calibration_execution_count": 0,
        "calibration_results_present": False,
        "three_class_calibrated": False,
        "independent_generalization_validated": False,
        "true_relevance_established": False,
        "corrected_policy_selected": False,
        "score_policy_mutation_authorized": False,
        "score_weights_or_threshold_changed": False,
        "runtime_failure_class_signal_changed": False,
        "ranking_policy_changed": False,
        "memory_entry_index_or_marker_changed": False,
        "retrieval_ready": False,
        "retrieval_experiment_authorized": False,
        "runtime_memory_injection_count": 0,
        "agent_runs": 0,
        "provider_calls_made": 0,
        "evaluator_calls_made": 0,
        "network_capable_call_paths_invoked": 0,
        "core_campaign_unlocked": False,
        "analysis_ready": False,
        "memory_effect_established": False,
        "negative_transfer_established": False,
    }


def build_d117_approval_receipt(
    *,
    repository: str | Path | None = None,
    context: Mapping[str, Any] | None = None,
    protected_pre: Mapping[str, Any] | None = None,
    implementation_pre: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    repo = _repo_root(repository)
    current = dict(context) if context is not None else _load_exact_context(repo)
    current["repository"] = repo
    protected = dict(protected_pre) if protected_pre is not None else _protected_input_state(repo)
    implementation = (
        dict(implementation_pre) if implementation_pre is not None else _implementation_state(repo)
    )
    body = {
        "milestone": MILESTONE,
        "evidence_kind": "exact-d116-grammar-blind-protocol-candidate-approval-binding",
        "approval_recorded_at": APPROVAL_RECORDED_AT,
        "approval_action_id": EXPECTED_D116_ACTION_HASH,
        "approval_reference": {
            "candidate_id": EXPECTED_D116_CANDIDATE_ID,
            "semantic_body_hash": EXPECTED_D116_CANDIDATE_BODY_SHA,
            "file_sha256": EXPECTED_D116_CANDIDATE_FILE_SHA,
        },
        "approval_reference_mode": "exact-current-user-message-self-attested",
        "approval_statement_code": (
            "exact-d116-triple-d117-blind-acquisition-protocol-candidate-only-v1"
        ),
        "d116_source_gate": _artifact_binding(
            D116_SOURCE_GATE_PATH,
            repository=repo,
            payload=current["d116_gate"],
            content=current["d116_gate_content"],
            id_field="gate_id",
        ),
        "d116_candidate": _artifact_binding(
            D116_CANDIDATE_PATH,
            repository=repo,
            payload=current["d116_candidate"],
            content=current["d116_candidate_content"],
            id_field="candidate_id",
        ),
        "authorized_action_hash": EXPECTED_D116_ACTION_HASH,
        "authorized_scope": current["authorized_scope"],
        "materialization_scope": {
            "new_module_script_test_only": True,
            "new_artifact_paths": [
                DEFAULT_RECEIPT_PATH.as_posix(),
                DEFAULT_PREFLIGHT_PATH.as_posix(),
                DEFAULT_CANDIDATE_PATH.as_posix(),
                DEFAULT_SOURCE_GATE_PATH.as_posix(),
            ],
            "actual_pool_manifest_issue_bytes_blind_packet_or_label_allowed": False,
            "actual_pool_or_public_issue_read_allowed": False,
            "role_assignment_or_isolation_session_execution_allowed": False,
            "matcher_classifier_or_calibration_implementation_or_execution_allowed": False,
            "score_index_retrieval_injection_agent_provider_evaluator_or_core_allowed": False,
            "existing_predecessor_code_artifact_task_or_index_mutation_allowed": False,
        },
        "protected_pre_state": protected,
        "implementation_pre_state": implementation,
        "claim_semantics": {
            "receipt_is_protocol_candidate_authorization_binding_not_acquisition_claim": True,
            "idempotent_exact_materialization_allowed": True,
            "one_use_pool_acquisition_execution_claim": False,
            "pool_acquisition_execution_consumed": False,
            "current_process_or_agent_is_blind_reviewer": False,
            "global_or_cross_clone_exclusion_proved": False,
        },
        "self_attested": True,
        "approver_kind": "user",
        "approver_label": "repository-maintainer",
        "reviewer_identity_authenticated": False,
        "cryptographic_signature_verified": False,
        "execution_result_present": False,
    }
    body_hash = sha256_text(canonical_json(body))
    return {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "receipt_id": f"d117approval_{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": body,
    }


def build_d117_preflight(
    receipt: Mapping[str, Any],
    *,
    repository: str | Path | None = None,
    context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    repo = _repo_root(repository)
    current = dict(context) if context is not None else _load_exact_context(repo)
    current["repository"] = repo
    body = {
        "milestone": MILESTONE,
        "evidence_kind": "grammar-blind-preexisting-public-control-acquisition-protocol",
        "recorded_at": PREFLIGHT_RECORDED_AT,
        "approval_receipt": _output_binding(
            DEFAULT_RECEIPT_PATH,
            repository=repo,
            payload=receipt,
            id_field="receipt_id",
        ),
        "d116_source_gate": _artifact_binding(
            D116_SOURCE_GATE_PATH,
            repository=repo,
            payload=current["d116_gate"],
            content=current["d116_gate_content"],
            id_field="gate_id",
        ),
        "d116_candidate": _artifact_binding(
            D116_CANDIDATE_PATH,
            repository=repo,
            payload=current["d116_candidate"],
            content=current["d116_candidate_content"],
            id_field="candidate_id",
        ),
        "input_scope": {
            "exact_d116_artifact_and_implementation_bindings_read": True,
            "exact_d105_gate_and_three_rubric_renders_read": True,
            "d116_bound_task_manifests_reread": False,
            "new_source_pool_named_or_identified": False,
            "new_public_issue_or_pool_member_read_count": 0,
            "private_hidden_reference_known_bad_trace_patch_or_evaluator_read": False,
            "held_out_result_read": False,
            "held_out_public_issue_read": False,
            "runtime_memory_index_read_for_protocol": False,
        },
        "predecessor_contract_binding": {
            "d116_authorized_action_hash": EXPECTED_D116_ACTION_HASH,
            "d116_cutoff": EXPECTED_D116_CUTOFF,
            "d116_taxonomy_contract_hash": EXPECTED_D116_TAXONOMY_HASH,
            "d116_frozen_matcher_grammar_hash": EXPECTED_D116_GRAMMAR_HASH,
            "d116_current_process_or_agent_eligible_as_blind_selector": False,
            "authorized_scope_exact_copy": current["authorized_scope"],
        },
        "cutoff_and_preexistence_contract": _cutoff_and_preexistence_contract(),
        "d105_rubric_contract": _d105_rubric_contract(current),
        "role_separation_contract": _role_separation_contract(),
        "chain_of_custody_contract": _chain_of_custody_contract(),
        "independence_and_fallback_contract": _independence_and_fallback_contract(),
        "future_artifact_contracts": _future_artifact_contracts(),
        "prospective_execution_plan": _prospective_execution_plan(),
        "protected_pre_state": receipt["semantic_body"]["protected_pre_state"],
        "evidence_boundary": {
            "protocol_contract_and_plan_materialized": True,
            "source_pool_discovery_or_acquisition_authorized": False,
            "source_pool_identified_or_read": False,
            "held_out_public_issue_or_result_read_count": 0,
            "pool_manifest_or_member_count": 0,
            "role_or_isolation_session_count": 0,
            "blind_packet_selector_or_adjudication_result_count": 0,
            "independent_positive_count": 0,
            "matcher_classifier_or_calibration_implementation_count": 0,
            "matcher_classifier_or_calibration_execution_count": 0,
            "model_or_embedding_load_count": 0,
            "retrieval_calls": 0,
            "runtime_memory_injection_count": 0,
            "agent_runs": 0,
            "provider_calls_made": 0,
            "evaluator_calls_made": 0,
            "network_capable_call_paths_invoked": 0,
            "network_evidence_kind": "source-path-self-attested",
            "os_level_socket_block_or_instrumentation_verified": False,
            "added_model_cost_usd": 0,
        },
        "authority": _authority(candidate_ready=False),
    }
    body_hash = sha256_text(canonical_json(body))
    return {
        "schema_version": PREFLIGHT_SCHEMA_VERSION,
        "preflight_id": f"d117preflight_{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": body,
    }


def build_d117_candidate(
    receipt: Mapping[str, Any],
    preflight: Mapping[str, Any],
    *,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    repo = _repo_root(repository)
    preflight_body = preflight["semantic_body"]
    component_names = (
        "predecessor_contract_binding",
        "cutoff_and_preexistence_contract",
        "d105_rubric_contract",
        "role_separation_contract",
        "chain_of_custody_contract",
        "independence_and_fallback_contract",
        "future_artifact_contracts",
        "prospective_execution_plan",
    )
    component_hashes = {
        f"{name}_hash": sha256_text(canonical_json(preflight_body[name]))
        for name in component_names
    }
    proposed_next_action = {
        "action_kind": (
            "prepare-one-isolated-preexisting-public-pool-acquisition-execution-"
            "authorization-candidate"
        ),
        "future_milestone": "D-118",
        "exact_d117_candidate_triple_required": True,
        "exact_external_pre_d116_source_snapshot_triple_required": True,
        "external_source_snapshot_must_be_public_development_only": True,
        "held_out_task_issue_or_result_membership_or_read_allowed": False,
        "exact_pre_d116_membership_manifest_or_exhaustive_rule_triple_required": True,
        "exact_trusted_cutoff_anchor_triple_required": True,
        "exact_isolation_profile_triple_required": True,
        "candidate_preparation_may_inspect_only_explicitly_supplied_external_triples": True,
        "candidate_preparation_may_run_pool_acquisition": False,
        "candidate_preparation_may_read_unapproved_pool_or_issue_content": False,
        "current_process_or_any_d116_grammar_observer_may_be_blind_role": False,
        "same_checkout_subagent_or_prompt_only_blinding_is_sufficient": False,
        "missing_or_invalid_preexistence_proof_must_fail_closed": True,
        "unknown_independence_evidence_must_be_post_hoc_and_independent_false": True,
        "matcher_grammar_or_ontology_mutation_allowed": False,
        "matcher_classifier_or_calibration_implementation_or_execution_allowed": False,
        "score_policy_or_ranking_mutation_allowed": False,
        "retrieval_or_runtime_memory_injection_allowed": False,
        "agent_provider_evaluator_or_network_allowed": False,
        "core_or_analysis_campaign_allowed": False,
    }
    body = {
        "milestone": MILESTONE,
        "evidence_kind": "blind-public-control-acquisition-execution-authorization-candidate",
        "recorded_at": CANDIDATE_RECORDED_AT,
        "approval_receipt": _output_binding(
            DEFAULT_RECEIPT_PATH,
            repository=repo,
            payload=receipt,
            id_field="receipt_id",
        ),
        "preflight": _output_binding(
            DEFAULT_PREFLIGHT_PATH,
            repository=repo,
            payload=preflight,
            id_field="preflight_id",
        ),
        "protocol_component_hashes": component_hashes,
        "candidate_status": (
            "protocol-sealed-no-pool-inspected-acquisition-and-independent-positives-still-blocked"
        ),
        "unresolved_prerequisites": [
            "no-exact-external-pre-d116-source-snapshot-binding-supplied",
            "no-exact-pre-d116-membership-manifest-or-exhaustive-rule-binding-supplied",
            "no-trusted-cutoff-anchor-verified",
            "no-capability-separated-role-principals-or-isolation-images-bound",
            "source-pool-not-identified-read-acquired-or-frozen",
            "blind-review-packet-and-sealed-first-pass-results-absent",
            "independent-positive-count-is-zero",
            "matcher-classifier-calibration-not-implemented-or-executed",
        ],
        "proposed_next_action": proposed_next_action,
        "proposed_next_action_hash": sha256_text(canonical_json(proposed_next_action)),
        "approval_contract": {
            "separate_user_message_required": True,
            "exact_candidate_id_required": True,
            "exact_semantic_body_hash_required": True,
            "exact_file_sha256_required": True,
            "generic_continue_message_is_approval": False,
            "external_source_membership_cutoff_and_isolation_triples_also_required": True,
            "approval_would_only_authorize_d118_execution_authorization_candidate": True,
            "approval_would_authorize_actual_acquisition_or_review": False,
            "approval_would_authorize_matcher_classifier_calibration_or_score_change": False,
            "approval_would_authorize_retrieval_agent_provider_evaluator_or_core": False,
        },
        "authority": _authority(candidate_ready=True),
    }
    body_hash = sha256_text(canonical_json(body))
    return {
        "schema_version": CANDIDATE_SCHEMA_VERSION,
        "candidate_id": f"d117blindprotocolcandidate_{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": body,
    }


def build_d117_source_gate(
    receipt: Mapping[str, Any],
    preflight: Mapping[str, Any],
    candidate: Mapping[str, Any],
    *,
    repository: str | Path | None = None,
    context: Mapping[str, Any] | None = None,
    protected_pre: Mapping[str, Any],
    protected_post: Mapping[str, Any],
    implementation_pre: Mapping[str, Any],
    implementation_post: Mapping[str, Any],
) -> dict[str, Any]:
    repo = _repo_root(repository)
    current = dict(context) if context is not None else _load_exact_context(repo)
    current["repository"] = repo
    _require(protected_pre == protected_post, "D-117 protected inputs changed during build")
    _require(
        implementation_pre == implementation_post,
        "D-117 implementation changed during build",
    )
    authority = candidate["semantic_body"]["authority"]
    _require(
        authority == _authority(candidate_ready=True),
        "D-117 candidate authority expanded or drifted",
    )
    body = {
        "milestone": MILESTONE,
        "evidence_kind": "grammar-blind-public-control-acquisition-protocol-source-gate",
        "recorded_at": GATE_RECORDED_AT,
        "approval_receipt": _output_binding(
            DEFAULT_RECEIPT_PATH,
            repository=repo,
            payload=receipt,
            id_field="receipt_id",
        ),
        "d116_source_gate": _artifact_binding(
            D116_SOURCE_GATE_PATH,
            repository=repo,
            payload=current["d116_gate"],
            content=current["d116_gate_content"],
            id_field="gate_id",
        ),
        "d116_candidate": _artifact_binding(
            D116_CANDIDATE_PATH,
            repository=repo,
            payload=current["d116_candidate"],
            content=current["d116_candidate_content"],
            id_field="candidate_id",
        ),
        "preflight": _output_binding(
            DEFAULT_PREFLIGHT_PATH,
            repository=repo,
            payload=preflight,
            id_field="preflight_id",
        ),
        "protocol_candidate": _output_binding(
            DEFAULT_CANDIDATE_PATH,
            repository=repo,
            payload=candidate,
            id_field="candidate_id",
        ),
        "implementation_files": implementation_pre["files"],
        "protected_input_integrity": {
            "pre_build": protected_pre,
            "post_build": protected_post,
            "fingerprints_equal": True,
            "implementation_pre_build": implementation_pre,
            "implementation_post_build": implementation_post,
            "implementation_fingerprints_equal": True,
        },
        "qualification": {
            "exact_d116_candidate_user_approval_bound": True,
            "exact_d116_source_gate_and_action_hash_validated": True,
            "exact_d116_cutoff_and_frozen_grammar_hash_bound": True,
            "exact_d105_three_group_rubric_set_bound": True,
            "protocol_only_no_pool_named_identified_or_read": True,
            "future_pool_scope_is_public_development_only_and_held_out_excluded": True,
            "pre_d116_bytes_and_membership_proof_contract_defined": True,
            "created_at_mtime_git_time_or_current_fetch_alone_rejected": True,
            "capability_separated_role_visibility_contract_defined": True,
            "current_process_agent_and_same_checkout_subagent_ineligible_for_blind_roles": True,
            "selector_a_b_and_adjudicator_first_pass_seal_required": True,
            "post_hoc_independent_false_fallback_defined": True,
            "zero_control_outcome_preserves_three_group_ontology": True,
            "future_artifact_schemas_are_plan_only": True,
            "source_pool_identified": False,
            "public_issue_read_count": 0,
            "pool_manifest_or_member_count": 0,
            "role_or_isolation_session_count": 0,
            "blind_packet_or_review_result_count": 0,
            "independent_positive_count": 0,
            "matcher_classifier_or_calibration_executed": False,
            "score_index_retrieval_injection_agent_or_core_unchanged": True,
            "protected_inputs_unchanged": True,
            "implementation_unchanged": True,
        },
        "evidence_boundary": dict(preflight["semantic_body"]["evidence_boundary"]),
        "authority": dict(authority),
        "next_gate": (
            "exact-d117-candidate-triple-plus-external-source-membership-cutoff-and-"
            "isolation-triples-d118-execution-authorization-candidate-approval"
        ),
    }
    body_hash = sha256_text(canonical_json(body))
    return {
        "schema_version": SOURCE_GATE_SCHEMA_VERSION,
        "gate_id": f"d117_{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": body,
    }


def _parse_time(value: Any, *, label: str) -> datetime:
    _require(isinstance(value, str), f"D-117 {label} timestamp must be a string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise D117BlindProtocolError(f"D-117 {label} timestamp is invalid") from exc
    _require(parsed.tzinfo is not None, f"D-117 {label} timestamp must be timezone-aware")
    return parsed


def _validate_chronology(
    receipt: Mapping[str, Any],
    preflight: Mapping[str, Any],
    candidate: Mapping[str, Any] | None = None,
    gate: Mapping[str, Any] | None = None,
) -> None:
    times = [
        _parse_time(receipt["semantic_body"]["approval_recorded_at"], label="approval"),
        _parse_time(preflight["semantic_body"]["recorded_at"], label="preflight"),
    ]
    if candidate is not None:
        times.append(_parse_time(candidate["semantic_body"]["recorded_at"], label="candidate"))
    if gate is not None:
        times.append(_parse_time(gate["semantic_body"]["recorded_at"], label="source gate"))
    _require(
        all(left < right for left, right in pairwise(times)),
        "D-117 artifact chronology must be strictly increasing",
    )


def _write_exact(path: Path, content: bytes, *, repository: Path) -> None:
    _require(path != repository, "D-117 output cannot be repository root")
    path.parent.mkdir(parents=True, exist_ok=True)
    _require(not _is_linklike(path.parent), "D-117 output parent cannot be linked")
    if path.exists():
        _require(
            _read_stable(path, label="existing D-117 output") == content,
            "D-117 existing output differs from deterministic rebuild",
        )
        return
    try:
        with path.open("xb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as exc:
        raise D117BlindProtocolError("D-117 output exclusive-create write failed") from exc
    _require(
        _read_stable(path, label="committed D-117 output") == content,
        "D-117 committed output read-back mismatch",
    )


def _output_paths(repository: Path) -> tuple[Path, ...]:
    return tuple(
        _resolved(path, repository=repository, label="D-117 output", must_exist=False)
        for path in (
            DEFAULT_RECEIPT_PATH,
            DEFAULT_PREFLIGHT_PATH,
            DEFAULT_CANDIDATE_PATH,
            DEFAULT_SOURCE_GATE_PATH,
        )
    )


def _require_all_or_none_output_state(repository: Path) -> bool:
    paths = _output_paths(repository)
    existence = [path.exists() for path in paths]
    _require(
        not any(existence) or all(existence),
        "D-117 partial artifact set exists; no automatic retry, repair, or overwrite allowed",
    )
    return all(existence)


def validate_d117_receipt(
    path: str | Path = DEFAULT_RECEIPT_PATH,
    *,
    repository: str | Path | None = None,
    context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    repo = _repo_root(repository)
    selected = _resolved(path, repository=repo, label="D-117 approval receipt")
    content = _read_stable(selected, label="D-117 approval receipt")
    parsed = _parse_json(content, label="D-117 approval receipt")
    body = _validate_envelope(
        parsed,
        root_keys=RECEIPT_ROOT_KEYS,
        body_keys=RECEIPT_BODY_KEYS,
        id_field="receipt_id",
        id_prefix="d117approval_",
        label="D-117 approval receipt",
    )
    _require(
        body["execution_result_present"] is False
        and body["claim_semantics"]["one_use_pool_acquisition_execution_claim"] is False
        and body["claim_semantics"]["current_process_or_agent_is_blind_reviewer"] is False,
        "D-117 receipt overclaims acquisition or blindness",
    )
    current = dict(context) if context is not None else _load_exact_context(repo)
    current["repository"] = repo
    expected = build_d117_approval_receipt(
        repository=repo,
        context=current,
        protected_pre=_protected_input_state(repo),
        implementation_pre=_implementation_state(repo),
    )
    _require(parsed == expected, "D-117 approval receipt full expected payload mismatch")
    _require(content == _pretty_json(expected), "D-117 approval receipt exact bytes drifted")
    return parsed


def validate_d117_preflight(
    path: str | Path = DEFAULT_PREFLIGHT_PATH,
    *,
    repository: str | Path | None = None,
    context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    repo = _repo_root(repository)
    selected = _resolved(path, repository=repo, label="D-117 preflight")
    content = _read_stable(selected, label="D-117 preflight")
    parsed = _parse_json(content, label="D-117 preflight")
    _validate_envelope(
        parsed,
        root_keys=PREFLIGHT_ROOT_KEYS,
        body_keys=PREFLIGHT_BODY_KEYS,
        id_field="preflight_id",
        id_prefix="d117preflight_",
        label="D-117 preflight",
    )
    current = dict(context) if context is not None else _load_exact_context(repo)
    current["repository"] = repo
    receipt = validate_d117_receipt(repository=repo, context=current)
    expected = build_d117_preflight(receipt, repository=repo, context=current)
    _require(parsed == expected, "D-117 preflight full expected payload mismatch")
    _require(content == _pretty_json(expected), "D-117 preflight exact bytes drifted")
    _validate_chronology(receipt, parsed)
    return parsed


def validate_d117_candidate(
    path: str | Path = DEFAULT_CANDIDATE_PATH,
    *,
    repository: str | Path | None = None,
    context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    repo = _repo_root(repository)
    selected = _resolved(path, repository=repo, label="D-117 protocol candidate")
    content = _read_stable(selected, label="D-117 protocol candidate")
    parsed = _parse_json(content, label="D-117 protocol candidate")
    body = _validate_envelope(
        parsed,
        root_keys=CANDIDATE_ROOT_KEYS,
        body_keys=CANDIDATE_BODY_KEYS,
        id_field="candidate_id",
        id_prefix="d117blindprotocolcandidate_",
        label="D-117 protocol candidate",
    )
    _require_exact_keys(
        body["authority"],
        tuple(_authority(candidate_ready=True)),
        label="D-117 candidate authority",
    )
    _require(
        body["authority"] == _authority(candidate_ready=True),
        "D-117 candidate authority value drifted",
    )
    current = dict(context) if context is not None else _load_exact_context(repo)
    current["repository"] = repo
    receipt = validate_d117_receipt(repository=repo, context=current)
    preflight = validate_d117_preflight(repository=repo, context=current)
    expected = build_d117_candidate(receipt, preflight, repository=repo)
    _require(parsed == expected, "D-117 candidate full expected payload mismatch")
    _require(content == _pretty_json(expected), "D-117 candidate exact bytes drifted")
    _validate_chronology(receipt, preflight, parsed)
    return parsed


def validate_d117_source_gate(
    path: str | Path = DEFAULT_SOURCE_GATE_PATH,
    *,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    repo = _repo_root(repository)
    selected = _resolved(path, repository=repo, label="D-117 source gate")
    content = _read_stable(selected, label="D-117 source gate")
    parsed = _parse_json(content, label="D-117 source gate")
    body = _validate_envelope(
        parsed,
        root_keys=GATE_ROOT_KEYS,
        body_keys=GATE_BODY_KEYS,
        id_field="gate_id",
        id_prefix="d117_",
        label="D-117 source gate",
    )
    current = _load_exact_context(repo)
    current["repository"] = repo
    receipt = validate_d117_receipt(repository=repo, context=current)
    preflight = validate_d117_preflight(repository=repo, context=current)
    candidate = validate_d117_candidate(repository=repo, context=current)
    protected = _protected_input_state(repo)
    implementation = _implementation_state(repo)
    expected = build_d117_source_gate(
        receipt,
        preflight,
        candidate,
        repository=repo,
        context=current,
        protected_pre=protected,
        protected_post=protected,
        implementation_pre=implementation,
        implementation_post=implementation,
    )
    _require(parsed == expected, "D-117 source gate full expected payload mismatch")
    _require(content == _pretty_json(expected), "D-117 source gate exact bytes drifted")
    _validate_chronology(receipt, preflight, candidate, parsed)
    _require(
        body["authority"] == _authority(candidate_ready=True)
        and body["authority"]["source_pool_public_issue_read_count"] == 0
        and body["authority"]["independent_positive_count"] == 0
        and body["authority"]["classifier_execution_count"] == 0
        and body["authority"]["calibration_execution_count"] == 0
        and body["authority"]["retrieval_ready"] is False,
        "D-117 source-gate authority expanded",
    )
    return parsed


def run_d117_protocol_candidate(*, repository: str | Path | None = None) -> dict[str, Any]:
    repo = _repo_root(repository)
    complete_set_preexists = _require_all_or_none_output_state(repo)
    context = _load_exact_context(repo)
    context["repository"] = repo
    protected_pre = _protected_input_state(repo)
    implementation_pre = _implementation_state(repo)
    receipt = build_d117_approval_receipt(
        repository=repo,
        context=context,
        protected_pre=protected_pre,
        implementation_pre=implementation_pre,
    )
    preflight = build_d117_preflight(receipt, repository=repo, context=context)
    candidate = build_d117_candidate(receipt, preflight, repository=repo)
    protected_post = _protected_input_state(repo)
    implementation_post = _implementation_state(repo)
    gate = build_d117_source_gate(
        receipt,
        preflight,
        candidate,
        repository=repo,
        context=context,
        protected_pre=protected_pre,
        protected_post=protected_post,
        implementation_pre=implementation_pre,
        implementation_post=implementation_post,
    )
    pre_gate_outputs = (
        (DEFAULT_RECEIPT_PATH, receipt),
        (DEFAULT_PREFLIGHT_PATH, preflight),
        (DEFAULT_CANDIDATE_PATH, candidate),
    )
    for relative, payload in pre_gate_outputs:
        selected = _resolved(relative, repository=repo, label="D-117 output", must_exist=False)
        _write_exact(selected, _pretty_json(payload), repository=repo)
    validate_d117_receipt(repository=repo, context=context)
    validate_d117_preflight(repository=repo, context=context)
    validate_d117_candidate(repository=repo, context=context)
    gate_path = _resolved(
        DEFAULT_SOURCE_GATE_PATH,
        repository=repo,
        label="D-117 source gate",
        must_exist=False,
    )
    _write_exact(gate_path, _pretty_json(gate), repository=repo)
    _require_all_or_none_output_state(repo)
    validate_d117_source_gate(repository=repo)
    candidate_content = _pretty_json(candidate)
    gate_content = _pretty_json(gate)
    return {
        "receipt_id": receipt["receipt_id"],
        "preflight_id": preflight["preflight_id"],
        "candidate_id": candidate["candidate_id"],
        "candidate_semantic_body_hash": candidate["semantic_body_hash"],
        "candidate_file_bytes": len(candidate_content),
        "candidate_file_sha256": sha256_bytes(candidate_content),
        "gate_id": gate["gate_id"],
        "gate_semantic_body_hash": gate["semantic_body_hash"],
        "gate_file_bytes": len(gate_content),
        "gate_file_sha256": sha256_bytes(gate_content),
        "candidate_status": candidate["semantic_body"]["candidate_status"],
        "complete_exact_set_preexisted": complete_set_preexists,
        "source_pool_public_issue_read_count": 0,
        "held_out_public_issue_or_result_read_count": 0,
        "pool_manifest_count": 0,
        "role_assignment_count": 0,
        "blind_packet_count": 0,
        "independent_positive_count": 0,
        "matcher_classifier_calibration_execution_count": 0,
        "score_policy_mutation_authorized": False,
        "retrieval_ready": False,
        "runtime_memory_injection_count": 0,
        "agent_runs": 0,
        "provider_calls_made": 0,
        "evaluator_calls_made": 0,
        "core_campaign_unlocked": False,
    }
