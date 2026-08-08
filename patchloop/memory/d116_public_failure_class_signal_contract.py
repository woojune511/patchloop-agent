"""Prepare the D-116 public applicability-signal contract candidate.

D-116 consumes the exact D-115 approval only to seal a classifier-facing
contract and a prospective public calibration plan.  It does not implement or
execute a classifier, assign failure-cause ground truth, change the scorer, or
run retrieval, an agent, a provider, or an evaluator.
"""

from __future__ import annotations

import json
import os
import re
import stat
import unicodedata
from collections.abc import Mapping, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from patchloop.errors import ContractError
from patchloop.memory import d115_score_policy_decision as d115
from patchloop.util import canonical_json, sha256_bytes, sha256_text

MILESTONE = "D-116"
RECEIPT_SCHEMA_VERSION = "public-failure-class-signal-approval-receipt-d116-v1"
PREFLIGHT_SCHEMA_VERSION = "public-failure-class-signal-contract-preflight-d116-v1"
CANDIDATE_SCHEMA_VERSION = "public-failure-class-signal-calibration-authorization-candidate-d116-v1"
SOURCE_GATE_SCHEMA_VERSION = "public-failure-class-signal-contract-source-gate-d116-v1"
PROJECTION_SCHEMA_VERSION = "public-applicability-signal-input-d116-v1"
RESULT_SCHEMA_VERSION = "public-applicability-signal-result-d116-v1"

APPROVAL_RECORDED_AT = "2026-08-07T06:22:51.021003Z"
PREFLIGHT_RECORDED_AT = "2026-08-07T06:22:52Z"
CANDIDATE_RECORDED_AT = "2026-08-07T06:22:53Z"
GATE_RECORDED_AT = "2026-08-07T06:22:54Z"

DEFAULT_RECEIPT_PATH = Path(
    "reports/memory-development/d116-public-failure-class-signal-approval-receipt.json"
)
DEFAULT_PREFLIGHT_PATH = Path(
    "reports/memory-development/d116-public-failure-class-signal-preflight.json"
)
DEFAULT_CANDIDATE_PATH = Path(
    "reports/memory-development/d116-public-failure-class-signal-calibration-candidate.json"
)
DEFAULT_SOURCE_GATE_PATH = Path(
    "reports/memory-development/d116-public-failure-class-signal-source-gate.json"
)

D116_IMPLEMENTATION_PATHS = (
    Path("patchloop/memory/d116_public_failure_class_signal_contract.py"),
    Path("scripts/build_d116_public_failure_class_signal_candidate.py"),
    Path("tests/test_d116_public_failure_class_signal_contract.py"),
)

EXPECTED_D115_CANDIDATE_ID = (
    "d115scoredecisioncandidate_91e3ef5af000fe830483012b5deee4eeb47f5a117fa5904d93d713b03f2308ec"
)
EXPECTED_D115_CANDIDATE_BODY_SHA = (
    "sha256:91e3ef5af000fe830483012b5deee4eeb47f5a117fa5904d93d713b03f2308ec"
)
EXPECTED_D115_CANDIDATE_BYTES = 6_839
EXPECTED_D115_CANDIDATE_FILE_SHA = (
    "sha256:1fd424eab88c60a9d8480e756642b2c70b03afd03dd777e27bf36a3ea428df7a"
)
EXPECTED_D115_GATE_ID = "d115_ab5e8f0e9f57c5fb37f05137da5b6cf8ca6421856ade33616448023d39c4a805"
EXPECTED_D115_GATE_BODY_SHA = (
    "sha256:ab5e8f0e9f57c5fb37f05137da5b6cf8ca6421856ade33616448023d39c4a805"
)
EXPECTED_D115_GATE_BYTES = 13_730
EXPECTED_D115_GATE_FILE_SHA = (
    "sha256:67f62c23e9f5e14fe9cd1d075b2c6f679764c18644837914b0031348c4a21b72"
)
EXPECTED_D115_ACTION_HASH = (
    "sha256:180c9456da225b95f8ddcf8ab4d05df1732d670b43f901e2220d841bfa5cb466"
)

DEFAULT_D105_GATE_PATH = Path(
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

TAXONOMY_RENDER_SPECS = (
    {
        "order": 1,
        "path": "reports/memory-development/rendered/d105/"
        "memgrp_649483b80292fea26e4009ebdb72df31.txt",
        "memory_id": "memgrp_649483b80292fea26e4009ebdb72df31",
        "semantic_group_id": "platform-emulation-matrix-gap",
        "failure_class": "PLATFORM_EMULATION_MATRIX_GAP",
        "file_bytes": 1_191,
        "file_sha256": ("sha256:f1cd44ed10d527ff7f5c44dd0be4e6957810530cd055d3329da0d7962d3cec7c"),
    },
    {
        "order": 2,
        "path": "reports/memory-development/rendered/d105/"
        "memgrp_b421547d481faabf9be3511217258de5.txt",
        "memory_id": "memgrp_b421547d481faabf9be3511217258de5",
        "semantic_group_id": "request-context-propagation-gap",
        "failure_class": "CONTEXT_PROPAGATION_GAP",
        "file_bytes": 1_164,
        "file_sha256": ("sha256:ab0273b575f76efd4ca9facda9540d87f2ea85e69a333cf87e4d7ac781287c2a"),
    },
    {
        "order": 3,
        "path": "reports/memory-development/rendered/d105/"
        "memgrp_5a23f463cba43bf3ba395f67cf976047.txt",
        "memory_id": "memgrp_5a23f463cba43bf3ba395f67cf976047",
        "semantic_group_id": "exception-origin-state-conflation",
        "failure_class": "SEMANTIC_STATE_CONFLATION",
        "file_bytes": 1_161,
        "file_sha256": ("sha256:00ceca8ed912a48f36ab26fb50b1d7eb428fe261a83b2bd84e231f0c6e786bf7"),
    },
)

PUBLIC_FILE_SPECS = (
    {
        "path": "tasks/dev-train/anyio-interrupt-runner-cleanup/public.yaml",
        "split": "dev-train",
        "file_bytes": 1_864,
        "file_sha256": ("sha256:ea977422306f9ce7203b4fc92aac83a73bc41554813d9ce1d794546767e76ddd"),
        "eligibility": "prospective-calibration",
        "case_role": "abstention-control-ambiguous-lifecycle",
        "candidate_expectation": "ABSTAIN",
        "candidate_group_id": None,
        "acceptance_included": True,
        "independent_positive": False,
    },
    {
        "path": "tasks/dev-train/csv-final-record-flush/public.yaml",
        "split": "dev-train",
        "file_bytes": 1_096,
        "file_sha256": ("sha256:58ad92151b819e338be09e15b23bd9e23dd50ec7ae402094ff4e0f0d190c4662"),
        "eligibility": "bootstrap-excluded",
        "case_role": "bootstrap-fixture-not-research-calibration",
        "candidate_expectation": None,
        "candidate_group_id": None,
        "acceptance_included": False,
        "independent_positive": False,
    },
    {
        "path": "tasks/dev-train/duration-minute-boundary/public.yaml",
        "split": "dev-train",
        "file_bytes": 1_065,
        "file_sha256": ("sha256:3d150a9420989ba938fa4ea543d31b485a09a186852dcf5632427246a318c9f8"),
        "eligibility": "bootstrap-excluded",
        "case_role": "bootstrap-fixture-not-research-calibration",
        "candidate_expectation": None,
        "candidate_group_id": None,
        "acceptance_included": False,
        "independent_positive": False,
    },
    {
        "path": "tasks/dev-train/hf-hub-xet-endpoint-propagation/public.yaml",
        "split": "dev-train",
        "file_bytes": 1_825,
        "file_sha256": ("sha256:3500452712d3977761f24da95170f073f86ec2a0589b69522321f91f5f473c4f"),
        "eligibility": "prospective-calibration",
        "case_role": "source-anchor-conformance",
        "candidate_expectation": "SELECT",
        "candidate_group_id": "request-context-propagation-gap",
        "acceptance_included": True,
        "independent_positive": False,
    },
    {
        "path": "tasks/dev-train/loguru-invalid-format-feedback/public.yaml",
        "split": "dev-train",
        "file_bytes": 2_392,
        "file_sha256": ("sha256:efec17dc692c0935553e9e3c67ad5463d977254ea52a536c1dcf4a4c43831f10"),
        "eligibility": "prospective-calibration",
        "case_role": "abstention-control-diagnostic-keyword-overlap",
        "candidate_expectation": "ABSTAIN",
        "candidate_group_id": None,
        "acceptance_included": True,
        "independent_positive": False,
    },
    {
        "path": "tasks/dev-train/pdm-ignore-active-venv-resolution/public.yaml",
        "split": "dev-train",
        "file_bytes": 1_986,
        "file_sha256": ("sha256:3d819ce8136e11d0572954f1afcc1918134aeef2e84d8fa365970c45ff671c24"),
        "eligibility": "prospective-calibration",
        "case_role": "abstention-control-cross-class-ambiguity",
        "candidate_expectation": "ABSTAIN",
        "candidate_group_id": None,
        "acceptance_included": True,
        "independent_positive": False,
    },
    {
        "path": "tasks/dev-train/pyfakefs-makedirs-parent-traversal/public.yaml",
        "split": "dev-train",
        "file_bytes": 1_852,
        "file_sha256": ("sha256:5be7e6f6d2ad9722ee90c5a829aa043bf94c70ac317d5ce45254e4f3f9458eb0"),
        "eligibility": "prospective-calibration",
        "case_role": "source-anchor-conformance",
        "candidate_expectation": "SELECT",
        "candidate_group_id": "platform-emulation-matrix-gap",
        "acceptance_included": True,
        "independent_positive": False,
    },
    {
        "path": "tasks/dev-train/tox-cross-section-empty-substitution/public.yaml",
        "split": "dev-train",
        "file_bytes": 1_903,
        "file_sha256": ("sha256:cf100f771e799824b2928f28faec4be76f011aa84667b1573b6fa373860b0c82"),
        "eligibility": "prospective-calibration",
        "case_role": "abstention-control-incomplete-source-overlap",
        "candidate_expectation": "ABSTAIN",
        "candidate_group_id": None,
        "acceptance_included": True,
        "independent_positive": False,
    },
    {
        "path": "tasks/dev-validation/babel-strict-grouped-decimal-trailing-zeroes/public.yaml",
        "split": "dev-validation",
        "file_bytes": 2_023,
        "file_sha256": ("sha256:d65e09fe70bb0449c85e663d0eeb695fe52bc7fb34619debbbe81a0b16ab2aca"),
        "eligibility": "prospective-calibration",
        "case_role": "public-abstention-control",
        "candidate_expectation": "ABSTAIN",
        "candidate_group_id": None,
        "acceptance_included": True,
        "independent_positive": False,
    },
    {
        "path": "tasks/dev-validation/moto-query-scanned-count/public.yaml",
        "split": "dev-validation",
        "file_bytes": 2_839,
        "file_sha256": ("sha256:4005b070d9e46c72a68554fbe998e9d81e920321a31e8bf633d3fd32277857f7"),
        "eligibility": "prospective-calibration",
        "case_role": "hypothesis-only-boundary-diagnostic",
        "candidate_expectation": "ABSTAIN",
        "candidate_group_id": None,
        "acceptance_included": False,
        "independent_positive": False,
    },
)

EXPECTED_PUBLIC_FILE_SET_SHA = (
    "sha256:d8b2c5b47a6536b19d2823c191bbf105834924bdc75f1d4692fea5f1413d29bb"
)

PROTECTED_FILE_SPECS = (
    {
        "path": str(d115.DEFAULT_PREFLIGHT_PATH).replace("\\", "/"),
        "file_bytes": 59_725,
        "file_sha256": ("sha256:91908b43eb581b09249f8285e5f1d09389092c5b40c1c794b9ab139667c86bad"),
    },
    {
        "path": str(d115.DEFAULT_CANDIDATE_PATH).replace("\\", "/"),
        "file_bytes": EXPECTED_D115_CANDIDATE_BYTES,
        "file_sha256": EXPECTED_D115_CANDIDATE_FILE_SHA,
    },
    {
        "path": str(d115.DEFAULT_SOURCE_GATE_PATH).replace("\\", "/"),
        "file_bytes": EXPECTED_D115_GATE_BYTES,
        "file_sha256": EXPECTED_D115_GATE_FILE_SHA,
    },
    {
        "path": "patchloop/memory/d115_score_policy_decision.py",
        "file_bytes": 48_275,
        "file_sha256": ("sha256:1199605de49c5f9e8ebafa8e7a161e17c5af05e00888fb13ec9fb524f20a5081"),
    },
    {
        "path": "scripts/build_d115_score_policy_decision_candidate.py",
        "file_bytes": 1_679,
        "file_sha256": ("sha256:6ccb44b4f77a336addeb075d051ec3131e24be2297cd1854d5febb4a77ab4b21"),
    },
    {
        "path": "tests/test_d115_score_policy_decision.py",
        "file_bytes": 19_823,
        "file_sha256": ("sha256:516766e65580bf8e23746c7ed1c9f10d15a46f77f5caacf4f0d5000ce3973efc"),
    },
    {
        "path": DEFAULT_D105_GATE_PATH.as_posix(),
        "file_bytes": EXPECTED_D105_GATE_BYTES,
        "file_sha256": EXPECTED_D105_GATE_FILE_SHA,
    },
    *(
        {
            "path": str(spec["path"]),
            "file_bytes": int(spec["file_bytes"]),
            "file_sha256": str(spec["file_sha256"]),
        }
        for spec in TAXONOMY_RENDER_SPECS
    ),
    *(
        {
            "path": str(spec["path"]),
            "file_bytes": int(spec["file_bytes"]),
            "file_sha256": str(spec["file_sha256"]),
        }
        for spec in PUBLIC_FILE_SPECS
    ),
)

ROOT_KEYS = ("schema_version", "semantic_body_hash", "semantic_body")
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
    "d115_source_gate",
    "d115_candidate",
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
    "d115_source_gate",
    "d115_candidate",
    "input_scope",
    "public_development_inventory",
    "taxonomy_contract",
    "signal_input_contract",
    "signal_result_contract",
    "deterministic_abstention_contract",
    "prospective_predicate_contract",
    "prospective_calibration_plan",
    "conditional_tuple_boundary",
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
    "contract_binding",
    "calibration_plan_binding",
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
    "d115_source_gate",
    "d115_candidate",
    "preflight",
    "calibration_candidate",
    "implementation_files",
    "protected_input_integrity",
    "qualification",
    "evidence_boundary",
    "authority",
    "next_gate",
)


class D116SignalContractError(ContractError):
    """Raised when D-116 scope, public inputs, or artifacts drift."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise D116SignalContractError(message)


def _repo_root(repository: str | Path | None) -> Path:
    selected = Path(repository) if repository is not None else Path(__file__).resolve().parents[2]
    try:
        return selected.resolve()
    except OSError as exc:
        raise D116SignalContractError("D-116 repository root cannot be resolved") from exc


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
    candidate = repository / Path(relative)
    try:
        selected = candidate.resolve(strict=must_exist)
        selected.relative_to(repository)
    except (OSError, ValueError) as exc:
        raise D116SignalContractError(f"D-116 {label} escapes or is missing") from exc
    current = candidate
    while current != repository:
        _require(not _is_linklike(current), f"D-116 {label} cannot use a link or junction")
        current = current.parent
    return selected


def _read_stable(path: Path, *, label: str) -> bytes:
    try:
        before = path.stat()
        content = path.read_bytes()
        after = path.stat()
    except OSError as exc:
        raise D116SignalContractError(f"D-116 {label} cannot be read") from exc
    _require(
        (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns),
        f"D-116 {label} changed while being read",
    )
    return content


def _parse_json(content: bytes, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise D116SignalContractError(f"D-116 {label} is not valid UTF-8 JSON") from exc
    _require(isinstance(value, dict), f"D-116 {label} root must be an object")
    return value


def _pretty_json(payload: Mapping[str, Any]) -> bytes:
    return (json.dumps(payload, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def _require_exact_keys(value: Any, expected: Sequence[str], *, label: str) -> None:
    _require(isinstance(value, dict), f"D-116 {label} must be an object")
    actual = set(value)
    wanted = set(expected)
    _require(
        actual == wanted,
        f"D-116 {label} key set mismatch: missing={sorted(wanted - actual)}, "
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
    _require(payload.get("semantic_body_hash") == body_hash, f"D-116 {label} body hash mismatch")
    _require(
        payload.get(id_field) == id_prefix + body_hash.removeprefix("sha256:"),
        f"D-116 {label} identifier mismatch",
    )
    return body


def _file_binding(relative: str | Path, *, repository: Path, label: str) -> dict[str, Any]:
    selected = _resolved(relative, repository=repository, label=label)
    content = _read_stable(selected, label=label)
    return {
        "path": selected.relative_to(repository).as_posix(),
        "file_bytes": len(content),
        "file_sha256": sha256_bytes(content),
    }


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
        f"D-116 {label} exact file binding mismatch",
    )
    return _parse_json(content, label=label), content


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
    selected = _resolved(relative, repository=repository, label="D-116 output", must_exist=False)
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
    for spec in PROTECTED_FILE_SPECS:
        binding = _file_binding(spec["path"], repository=repository, label="protected input")
        _require(
            binding["file_bytes"] == spec["file_bytes"]
            and binding["file_sha256"] == spec["file_sha256"],
            f"D-116 protected input drifted: {spec['path']}",
        )
        rows.append(binding)
    return {"files": rows, "fingerprint": sha256_text(canonical_json(rows))}


def _implementation_state(repository: Path) -> dict[str, Any]:
    rows = [
        _file_binding(path, repository=repository, label="D-116 implementation")
        for path in D116_IMPLEMENTATION_PATHS
    ]
    return {"files": rows, "fingerprint": sha256_text(canonical_json(rows))}


def _canonical_public_value(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value.replace("\r\n", "\n").replace("\r", "\n"))
    return " ".join(normalized.casefold().split())


def _public_projection(payload: Mapping[str, Any]) -> dict[str, Any]:
    issue = payload.get("issue")
    repository = payload.get("repository")
    _require(isinstance(issue, dict), "D-116 public issue must be an object")
    _require(isinstance(repository, dict), "D-116 public repository must be an object")
    title = issue.get("title")
    description = issue.get("description")
    language = repository.get("language")
    _require(isinstance(title, str) and title.strip(), "D-116 issue title is invalid")
    _require(
        isinstance(description, str) and description.strip(),
        "D-116 issue description is invalid",
    )
    _require(isinstance(language, str) and language.strip(), "D-116 language is invalid")
    projection = {
        "schema_version": PROJECTION_SCHEMA_VERSION,
        "issue_title": _canonical_public_value(title),
        "issue_description": _canonical_public_value(description),
        "language": _canonical_public_value(language),
    }
    return {
        "projection": projection,
        "projection_sha256": sha256_text(canonical_json(projection)),
    }


def _load_public_inventory(repository: Path) -> list[dict[str, Any]]:
    bindings = [
        {
            "path": str(spec["path"]),
            "file_bytes": int(spec["file_bytes"]),
            "file_sha256": str(spec["file_sha256"]),
        }
        for spec in PUBLIC_FILE_SPECS
    ]
    _require(
        sha256_text(canonical_json(bindings)) == EXPECTED_PUBLIC_FILE_SET_SHA,
        "D-116 public file-set hash constant drifted",
    )
    rows: list[dict[str, Any]] = []
    for spec in PUBLIC_FILE_SPECS:
        selected = _resolved(spec["path"], repository=repository, label="public task input")
        content = _read_stable(selected, label="public task input")
        _require(
            len(content) == spec["file_bytes"] and sha256_bytes(content) == spec["file_sha256"],
            f"D-116 public task exact binding mismatch: {spec['path']}",
        )
        try:
            payload = yaml.safe_load(content.decode("utf-8"))
        except (UnicodeDecodeError, yaml.YAMLError) as exc:
            raise D116SignalContractError("D-116 public task is not valid UTF-8 YAML") from exc
        _require(isinstance(payload, dict), "D-116 public task root must be an object")
        _require(payload.get("schema_version") == "task-public-v1", "D-116 public schema drifted")
        _require(payload.get("split") == spec["split"], "D-116 public split drifted")
        projection = _public_projection(payload)
        rows.append(
            {
                "path": str(spec["path"]),
                "split": str(spec["split"]),
                "file_bytes": len(content),
                "file_sha256": sha256_bytes(content),
                "eligibility": str(spec["eligibility"]),
                "classifier_projection": projection,
                "classifier_projection_excludes_task_id_and_path": True,
                "classifier_execution_result_present": False,
            }
        )
    _require(len(rows) == 10, "D-116 public inventory count drifted")
    return rows


def _load_exact_context(repository: Path) -> dict[str, Any]:
    d115.validate_d115_source_gate(repository=repository)
    candidate, candidate_content = _load_exact_json(
        d115.DEFAULT_CANDIDATE_PATH,
        repository=repository,
        expected_bytes=EXPECTED_D115_CANDIDATE_BYTES,
        expected_sha=EXPECTED_D115_CANDIDATE_FILE_SHA,
        label="D-115 candidate",
    )
    gate, gate_content = _load_exact_json(
        d115.DEFAULT_SOURCE_GATE_PATH,
        repository=repository,
        expected_bytes=EXPECTED_D115_GATE_BYTES,
        expected_sha=EXPECTED_D115_GATE_FILE_SHA,
        label="D-115 source gate",
    )
    _require(
        candidate["candidate_id"] == EXPECTED_D115_CANDIDATE_ID
        and candidate["semantic_body_hash"] == EXPECTED_D115_CANDIDATE_BODY_SHA,
        "D-116 exact D-115 candidate identity mismatch",
    )
    _require(
        gate["gate_id"] == EXPECTED_D115_GATE_ID
        and gate["semantic_body_hash"] == EXPECTED_D115_GATE_BODY_SHA,
        "D-116 exact D-115 source gate identity mismatch",
    )
    candidate_body = candidate["semantic_body"]
    _require(
        candidate_body["proposed_next_action_hash"] == EXPECTED_D115_ACTION_HASH,
        "D-116 D-115 authorized action hash mismatch",
    )
    authorized_scope = candidate_body["proposed_next_action"]
    _require(
        authorized_scope["future_milestone"] == MILESTONE
        and authorized_scope["action_kind"]
        == "prepare-public-failure-class-signal-contract-and-calibration-candidate"
        and authorized_scope["score_policy_mutation_allowed"] is False
        and authorized_scope["runtime_retrieval_allowed"] is False
        and authorized_scope["runtime_memory_injection_allowed"] is False
        and authorized_scope["agent_run_allowed"] is False
        and authorized_scope["provider_or_evaluator_call_allowed"] is False
        and authorized_scope["network_access_allowed"] is False
        and authorized_scope["core_campaign_allowed"] is False,
        "D-116 authorized scope drifted",
    )
    d105_gate, d105_content = _load_exact_json(
        DEFAULT_D105_GATE_PATH,
        repository=repository,
        expected_bytes=EXPECTED_D105_GATE_BYTES,
        expected_sha=EXPECTED_D105_GATE_FILE_SHA,
        label="D-105 render gate",
    )
    _require(
        d105_gate["gate_id"] == EXPECTED_D105_GATE_ID
        and d105_gate["semantic_body_hash"] == EXPECTED_D105_GATE_BODY_SHA,
        "D-116 exact D-105 gate identity mismatch",
    )
    recorded_entries = d105_gate["semantic_body"]["entries"]
    taxonomy: list[dict[str, Any]] = []
    for spec in TAXONOMY_RENDER_SPECS:
        entry = next(
            row for row in recorded_entries if row["proposed_memory_id"] == spec["memory_id"]
        )
        _require(
            entry["order"] == spec["order"]
            and entry["path"] == spec["path"]
            and entry["semantic_group_id"] == spec["semantic_group_id"]
            and entry["file_bytes"] == spec["file_bytes"]
            and entry["file_sha256"] == spec["file_sha256"],
            f"D-116 D-105 taxonomy binding drifted: {spec['memory_id']}",
        )
        selected = _resolved(spec["path"], repository=repository, label="D-105 taxonomy render")
        content = _read_stable(selected, label="D-105 taxonomy render")
        _require(
            len(content) == spec["file_bytes"] and sha256_bytes(content) == spec["file_sha256"],
            f"D-116 D-105 render bytes drifted: {spec['memory_id']}",
        )
        try:
            text = content.decode("ascii")
        except UnicodeDecodeError as exc:
            raise D116SignalContractError("D-116 D-105 render is not ASCII") from exc
        _require(
            f"Failure class: {spec['failure_class']}\n" in text,
            f"D-116 D-105 failure-class text drifted: {spec['memory_id']}",
        )
        taxonomy.append(
            {
                "order": spec["order"],
                "memory_id": spec["memory_id"],
                "semantic_group_id": spec["semantic_group_id"],
                "failure_class": spec["failure_class"],
                "model_facing_text": text,
                "render": {
                    "path": spec["path"],
                    "file_bytes": len(content),
                    "file_sha256": sha256_bytes(content),
                },
            }
        )
    return {
        "candidate": candidate,
        "candidate_content": candidate_content,
        "gate": gate,
        "gate_content": gate_content,
        "authorized_scope": authorized_scope,
        "d105_gate": d105_gate,
        "d105_content": d105_content,
        "taxonomy": taxonomy,
        "public_inventory": _load_public_inventory(repository),
    }


def _prospective_predicate_contract() -> dict[str, Any]:
    return {
        "contract_version": "frozen-public-matcher-grammar-d116-v1",
        "formal_matcher_grammar_complete": True,
        "matcher_evaluator_implementation_present": False,
        "matcher_evaluator_execution_count": 0,
        "task_specific_branch_allowed": False,
        "embedding_or_llm_judgment_allowed": False,
        "generic_keyword_count_is_sufficient": False,
        "predicate_evidence_spans_required": True,
        "matcher_algorithm": {
            "regex_engine": "python-stdlib-re",
            "regex_runtime_contract": "CPython-3.12",
            "regex_flags": ["ASCII"],
            "classifier_text_fields_in_order": ["issue_title", "issue_description"],
            "token_pattern": r"[a-z0-9]+(?:-[a-z0-9]+)*",
            "sentence_boundary_pattern": r"[.!?]+(?:\s+|$)",
            "clause_boundary_patterns": [
                r"[,;:]",
                r"\b(?:but|while|whereas|rather than|instead of)\b",
            ],
            "sentence_and_clause_indices": (
                "sentence_index and clause_index are each zero-based global counters within one "
                "canonical field; clause_index does not reset at sentence boundaries"
            ),
            "token_offset_contract": (
                "Tokens are re.finditer(token_pattern, ASCII) results in occurrence order. For a "
                "regex match, token_start is the first token index whose end is greater than the "
                "match start; token_end is one plus the last token index whose start is less than "
                "the match end. Both are zero-based half-open token offsets; reject a match that "
                "overlaps no token."
            ),
            "sentence_segmentation_contract": (
                "Enumerate non-overlapping sentence-boundary matches left to right. A sentence "
                "interval starts at the previous boundary end and ends at the current boundary "
                "end, so punctuation and following whitespace belong to the preceding sentence. "
                "Add the non-empty trailing interval; drop empty intervals. Reject an atom match "
                "that crosses a sentence interval boundary."
            ),
            "clause_segmentation_contract": (
                "Within each sentence, enumerate matches from every clause-boundary pattern, sort "
                "by start,end,pattern-index, retain the first and discard later overlapping "
                "boundaries. Clause intervals are the non-empty text between boundary spans. A "
                "match has clause_index null exactly when match_start < boundary_end and "
                "match_end > boundary_start for a retained boundary; half-open adjacency alone "
                "is not overlap. A null-clause match is ineligible for a same-clause relation; "
                "otherwise assign clause indices globally across the field in sentence order."
            ),
            "negation_tokens": ["not", "never", "without", "neither"],
            "negation_scope": (
                "Discard an atom match when any negation token occurs among the immediately "
                "preceding three tokens in the same clause. For clause_index null, use the same "
                "sentence instead."
            ),
            "atomic_match_enumeration": (
                "For each atom, enumerate every re.finditer match and sort by "
                "field-index,start,end,alternative-pattern-index."
            ),
            "all_atoms_relation": (
                "After negation filtering, enumerate the Cartesian product of one match per atom "
                "in declared atom order. Retain only tuples whose spans are distinct and "
                "non-overlapping, whose field is identical, whose relation_scope is satisfied, "
                "and whose max(token_end)-min(token_start) is <= max_token_span. Sort retained "
                "tuples by the concatenated per-atom match keys "
                "(field-index,start,end,pattern-index) and choose the first valid tuple. Never "
                "choose an invalid tuple and stop. same-clause means identical non-null clause "
                "index; same-sentence means identical sentence index; same-or-adjacent-sentences "
                "means maximum minus minimum sentence index is <= 1."
            ),
            "minimum_distinct_atoms_same_field": (
                "Enumerate declared-order atom-index subsets of exactly minimum_distinct_atoms, "
                "then each subset's Cartesian match products after negation filtering. Retain "
                "only one-field tuples with distinct non-overlapping spans. Sort valid candidates "
                "by field-index,atom-index-subset,then concatenated per-atom match keys and choose "
                "the first. Report only that selected minimum subset."
            ),
            "cross_predicate_span_reuse": (
                "The same canonical character span may be selected by different predicate IDs; "
                "it may not be reused by two atom IDs within one predicate. No global "
                "cross-predicate backtracking is performed."
            ),
            "partial_predicate_evidence": (
                "A required predicate is partial only when it is not satisfied and at least one "
                "of its atoms has a non-negated match. If no group is fully supported and at "
                "least one predicate is partial, use PARTIAL_PREDICATE_EVIDENCE; otherwise use "
                "NO_FULL_GROUP."
            ),
            "contradiction_match": (
                "For each contradiction in group order, choose its first non-negated match by "
                "field-index,start,end,pattern-index; any selected contradiction causes global "
                "abstention."
            ),
            "contradiction_scope": "global-all-groups-before-group-selection",
            "group_full_support": (
                "every required predicate is satisfied and no group contradiction matches"
            ),
            "decision_precedence": [
                "contract-error-on-invalid-or-noncanonical-projection",
                "abstain-on-unsupported-language",
                "abstain-on-any-matched-group-contradiction",
                "abstain-on-more-than-one-fully-supported-group",
                "select-the-only-fully-supported-group",
                "abstain-on-partial-predicate-evidence",
                "abstain-on-no-match",
            ],
            "unsupported_language_short_circuit": (
                "After exact projection and canonical_input_sha256 validation, an unsupported "
                "language returns ABSTAIN/UNSUPPORTED_LANGUAGE without tokenizing or matching "
                "text; matched_required_predicates, missing_required_predicates, "
                "contradiction_predicates, competing_group_ids, and evidence_spans are all empty "
                "arrays and selected_group_id is null."
            ),
            "pattern_or_match_score_allowed": False,
            "semantic_fallback_allowed": False,
        },
        "evidence_span_contract": {
            "field_enum": ["issue_title", "issue_description"],
            "coordinate_system": (
                "zero-based Unicode-code-point half-open offsets over the exact canonical field"
            ),
            "required_span_fields": [
                "predicate_id",
                "atom_id",
                "field",
                "start",
                "end",
                "matched_text",
                "pattern",
                "pattern_index",
                "sentence_index",
                "clause_index",
                "token_start",
                "token_end",
            ],
            "field_types": {
                "predicate_id": "string",
                "atom_id": "string",
                "field": "enum-string",
                "start": "nonnegative-integer",
                "end": "positive-integer-greater-than-start",
                "matched_text": "string",
                "pattern": "exact-declared-regex-string",
                "pattern_index": "nonnegative-integer-within-declared-pattern-list",
                "sentence_index": "nonnegative-integer",
                "clause_index": "nonnegative-integer-or-null",
                "token_start": "nonnegative-integer",
                "token_end": "positive-integer-greater-than-token-start",
            },
            "matched_text_must_equal_canonical_field_slice": True,
            "ordering": (
                "field-order,start,end,group-order,predicate-order,atom-order,pattern-index "
                "ascending"
            ),
            "duplicate_or_overlapping_selected_spans_within_one_predicate_allowed": False,
            "same_span_reuse_across_different_predicate_ids_allowed": True,
            "composite_role_exceptions": [],
        },
        "groups": [
            {
                "semantic_group_id": "platform-emulation-matrix-gap",
                "required_predicates": [
                    {
                        "predicate_id": "P1-explicit-emulation-reference-parity",
                        "mode": "all-atoms-relation",
                        "relation_scope": "same-sentence",
                        "max_token_span": 28,
                        "atoms": [
                            {
                                "atom_id": "P1-emulation",
                                "alternatives": [r"\b(?:fake|emulated|mock(?:ed)?|simulated)\b"],
                            },
                            {
                                "atom_id": "P1-reference",
                                "alternatives": [r"\b(?:real|native|reference|operating-system)\b"],
                            },
                            {
                                "atom_id": "P1-parity-or-contrast",
                                "alternatives": [
                                    r"\b(?:differ(?:s|ed|ent|ently)?|match(?:es|ed)?|parity|equivalent)\b"
                                ],
                            },
                        ],
                    },
                    {
                        "predicate_id": "P2-observable-intermediate-effect",
                        "mode": "all-atoms-relation",
                        "relation_scope": "same-or-adjacent-sentences",
                        "max_token_span": 45,
                        "atoms": [
                            {
                                "atom_id": "P2-terminal-outcome",
                                "alternatives": [
                                    r"\b(?:requested final|final (?:directory|outcome)|resulting)\b"
                                ],
                            },
                            {
                                "atom_id": "P2-intermediate-effect",
                                "alternatives": [
                                    (
                                        r"\b(?:intermediate|side effects?|walking|traversal|"
                                        r"directories created)\b"
                                    )
                                ],
                            },
                            {
                                "atom_id": "P2-distinction",
                                "alternatives": [
                                    (
                                        r"\b(?:while|rather than|instead of|before|after|"
                                        r"differ(?:s|ed|ent|ently)?)\b"
                                    )
                                ],
                            },
                        ],
                    },
                    {
                        "predicate_id": "P3-multi-dimension-public-matrix",
                        "mode": "minimum-distinct-atoms-same-field",
                        "minimum_distinct_atoms": 2,
                        "atoms": [
                            {
                                "atom_id": "P3-platform",
                                "alternatives": [
                                    r"\b(?:posix|windows|platform|operating-system)\b"
                                ],
                            },
                            {
                                "atom_id": "P3-path-type",
                                "alternatives": [
                                    (
                                        r"\b(?:relative paths?|bytes paths?|parent-directory|"
                                        r"path type)\b"
                                    )
                                ],
                            },
                            {
                                "atom_id": "P3-state",
                                "alternatives": [
                                    r"\b(?:existing destinations?|missing|existing|state)\b"
                                ],
                            },
                            {
                                "atom_id": "P3-mode",
                                "alternatives": [
                                    r"\b(?:filesystem modes?|creation modes?|strict mode)\b"
                                ],
                            },
                            {
                                "atom_id": "P3-error",
                                "alternatives": [
                                    r"\b(?:invalid parents?|errors?|exceptions?|failure)\b"
                                ],
                            },
                        ],
                    },
                ],
                "contradiction_predicates": [
                    {
                        "predicate_id": "PX-intentional-identical-semantics",
                        "atom_id": "PX-contradiction",
                        "patterns": [
                            (
                                r"\b(?:intentionally|by design) (?:share|have) (?:the )?"
                                r"(?:same|identical) (?:behavior|semantics)\b"
                            )
                        ],
                    }
                ],
            },
            {
                "semantic_group_id": "request-context-propagation-gap",
                "required_predicates": [
                    {
                        "predicate_id": "C1-caller-selected-scoped-context",
                        "mode": "all-atoms-relation",
                        "relation_scope": "same-clause",
                        "max_token_span": 12,
                        "atoms": [
                            {
                                "atom_id": "C1-actor",
                                "alternatives": [r"\b(?:caller|client|request)\b"],
                            },
                            {
                                "atom_id": "C1-scope-selection",
                                "alternatives": [
                                    r"\b(?:configured|custom|request-specific|explicit)\b"
                                ],
                            },
                            {
                                "atom_id": "C1-context-object",
                                "alternatives": [r"\b(?:endpoint|context|origin)\b"],
                            },
                        ],
                    },
                    {
                        "predicate_id": "C2-context-ownership-difference",
                        "mode": "all-atoms-relation",
                        "relation_scope": "same-sentence",
                        "max_token_span": 45,
                        "atoms": [
                            {
                                "atom_id": "C2-scoped-value",
                                "alternatives": [
                                    r"\b(?:configured|custom|request-specific|explicit)\b"
                                ],
                            },
                            {
                                "atom_id": "C2-other-ownership",
                                "alternatives": [
                                    r"\b(?:default|global|relative|another|foreign)\b"
                                ],
                            },
                            {
                                "atom_id": "C2-owned-object",
                                "alternatives": [r"\b(?:endpoint|origin|host|ownership|owned)\b"],
                            },
                            {
                                "atom_id": "C2-distinction-or-preservation",
                                "alternatives": [
                                    (
                                        r"\b(?:rebase|onto|while|rather than|instead|"
                                        r"preserv(?:e|es|ed|ing))\b"
                                    )
                                ],
                            },
                        ],
                    },
                    {
                        "predicate_id": "C3-multiple-propagation-paths",
                        "mode": "all-atoms-relation",
                        "relation_scope": "same-clause",
                        "max_token_span": 20,
                        "atoms": [
                            {
                                "atom_id": "C3-multiplicity",
                                "alternatives": [
                                    r"\b(?:every|all|multiple|more than one|across)\b"
                                ],
                            },
                            {
                                "atom_id": "C3-path",
                                "alternatives": [
                                    (
                                        r"\b(?:(?:metadata )?access paths?|caller paths?|"
                                        r"construction paths?|ownership paths?)\b"
                                    )
                                ],
                            },
                            {
                                "atom_id": "C3-propagation",
                                "alternatives": [
                                    r"\b(?:preserv(?:e|es|ed|ing)|propagat(?:e|es|ed|ing)|through|across)\b"
                                ],
                            },
                        ],
                    },
                ],
                "contradiction_predicates": [
                    {
                        "predicate_id": "CX-intentionally-global",
                        "atom_id": "CX-global-contradiction",
                        "patterns": [r"\b(?:intentionally|by design) (?:process-wide|global)\b"],
                    },
                    {
                        "predicate_id": "CX-one-path-only",
                        "atom_id": "CX-one-path-contradiction",
                        "patterns": [
                            r"\bonly one (?:construction|access|caller|ownership) path exists\b"
                        ],
                    },
                ],
            },
            {
                "semantic_group_id": "exception-origin-state-conflation",
                "required_predicates": [
                    {
                        "predicate_id": "S1-missing-versus-existing-empty-state",
                        "mode": "all-atoms-relation",
                        "relation_scope": "same-sentence",
                        "max_token_span": 35,
                        "atoms": [
                            {
                                "atom_id": "S1-absence",
                                "alternatives": [
                                    r"\b(?:missing|unresolved|not found|absent|undefined)\b"
                                ],
                            },
                            {
                                "atom_id": "S1-existing",
                                "alternatives": [r"\b(?:existing|present|defined)\b"],
                            },
                            {
                                "atom_id": "S1-empty-or-transformed",
                                "alternatives": [r"\b(?:empty|string|transformed|filtered)\b"],
                            },
                            {
                                "atom_id": "S1-distinction",
                                "alternatives": [
                                    (
                                        r"\b(?:vs|versus|rather than|instead of|"
                                        r"distinguish(?:es|ed)?|different)\b"
                                    )
                                ],
                            },
                        ],
                    },
                    {
                        "predicate_id": "S2-distinct-processing-stages",
                        "mode": "all-atoms-relation",
                        "relation_scope": "same-sentence",
                        "max_token_span": 45,
                        "atoms": [
                            {
                                "atom_id": "S2-origin-stage",
                                "alternatives": [
                                    r"\b(?:lookup|reference|referenced|resolve|resolution|source)\b"
                                ],
                            },
                            {
                                "atom_id": "S2-transform-stage",
                                "alternatives": [
                                    r"\b(?:filter|filtering|substitution|defaulting|transformation|replacement)\b"
                                ],
                            },
                            {
                                "atom_id": "S2-stage-order",
                                "alternatives": [
                                    r"\b(?:after|before|from|instead of|distinct|separate)\b"
                                ],
                            },
                        ],
                    },
                    {
                        "predicate_id": "S3-shared-error-boundary-collapse",
                        "mode": "all-atoms-relation",
                        "relation_scope": "same-sentence",
                        "max_token_span": 35,
                        "atoms": [
                            {
                                "atom_id": "S3-origin-stage",
                                "alternatives": [r"\b(?:lookup|reference|resolution|source)\b"],
                            },
                            {
                                "atom_id": "S3-transform-stage",
                                "alternatives": [
                                    r"\b(?:filtering|substitution|defaulting|transformation)\b"
                                ],
                            },
                            {
                                "atom_id": "S3-shared-boundary",
                                "alternatives": [
                                    (
                                        r"\b(?:same (?:exception|error)(?: boundary)?|"
                                        r"collapse(?:s|d)? (?:at|into) (?:the )?(?:same )?"
                                        r"(?:exception|error)(?: boundary)?|reported as (?:the )?"
                                        r"same (?:exception|error))\b"
                                    )
                                ],
                            },
                        ],
                    },
                ],
                "contradiction_predicates": [
                    {
                        "predicate_id": "SX-intentionally-identical-stage-failure",
                        "atom_id": "SX-contradiction",
                        "patterns": [
                            (
                                r"\b(?:lookup|resolution) and (?:filtering|substitution|"
                                r"defaulting|transformation) (?:are|is) intentionally "
                                r"(?:the same|identical)\b"
                            )
                        ],
                    }
                ],
            },
        ],
    }


def _validate_matcher_grammar(contract: Mapping[str, Any]) -> None:
    _require(
        contract.get("formal_matcher_grammar_complete") is True
        and contract.get("matcher_evaluator_implementation_present") is False,
        "D-116 formal matcher grammar boundary is invalid",
    )
    algorithm = contract.get("matcher_algorithm")
    _require(isinstance(algorithm, dict), "D-116 matcher algorithm must be an object")
    _require(
        algorithm.get("regex_engine") == "python-stdlib-re"
        and algorithm.get("regex_flags") == ["ASCII"],
        "D-116 matcher regex contract drifted",
    )
    grammar_patterns = [
        algorithm.get("token_pattern"),
        algorithm.get("sentence_boundary_pattern"),
        *(algorithm.get("clause_boundary_patterns") or []),
    ]
    _require(
        all(isinstance(pattern, str) and pattern for pattern in grammar_patterns),
        "D-116 matcher token or boundary grammar is invalid",
    )
    for pattern in grammar_patterns:
        try:
            re.compile(pattern, flags=re.ASCII)
        except re.error as exc:
            raise D116SignalContractError("D-116 matcher boundary regex is invalid") from exc
    groups = contract.get("groups")
    _require(isinstance(groups, list) and len(groups) == 3, "D-116 matcher groups drifted")
    expected_groups = [spec["semantic_group_id"] for spec in TAXONOMY_RENDER_SPECS]
    _require(
        [group.get("semantic_group_id") for group in groups] == expected_groups,
        "D-116 matcher group order drifted",
    )
    predicate_ids: set[str] = set()
    for group in groups:
        required = group.get("required_predicates")
        contradictions = group.get("contradiction_predicates")
        _require(
            isinstance(required, list) and len(required) == 3,
            "D-116 each matcher group requires exactly three predicates",
        )
        _require(
            isinstance(contradictions, list) and contradictions,
            "D-116 each matcher group requires a contradiction grammar",
        )
        for predicate in required:
            predicate_id = predicate.get("predicate_id")
            mode = predicate.get("mode")
            atoms = predicate.get("atoms")
            _require(
                isinstance(predicate_id, str) and predicate_id not in predicate_ids,
                "D-116 matcher predicate IDs must be unique strings",
            )
            predicate_ids.add(predicate_id)
            _require(
                mode
                in {
                    "all-atoms-relation",
                    "minimum-distinct-atoms-same-field",
                },
                "D-116 matcher predicate mode is invalid",
            )
            _require(isinstance(atoms, list) and atoms, "D-116 matcher atoms are missing")
            atom_ids: set[str] = set()
            for atom in atoms:
                atom_id = atom.get("atom_id")
                alternatives = atom.get("alternatives")
                _require(
                    isinstance(atom_id, str) and atom_id not in atom_ids,
                    "D-116 matcher atom IDs must be unique within a predicate",
                )
                atom_ids.add(atom_id)
                _require(
                    isinstance(alternatives, list)
                    and alternatives
                    and all(isinstance(pattern, str) and pattern for pattern in alternatives),
                    "D-116 matcher alternatives are invalid",
                )
                for pattern in alternatives:
                    try:
                        re.compile(pattern, flags=re.ASCII)
                    except re.error as exc:
                        raise D116SignalContractError(
                            f"D-116 matcher regex is invalid: {predicate_id}/{atom_id}"
                        ) from exc
            if mode == "all-atoms-relation":
                _require(
                    predicate.get("relation_scope")
                    in {"same-clause", "same-sentence", "same-or-adjacent-sentences"}
                    and isinstance(predicate.get("max_token_span"), int)
                    and predicate["max_token_span"] > 0,
                    "D-116 matcher relation scope and token span are invalid",
                )
            else:
                minimum = predicate.get("minimum_distinct_atoms")
                _require(
                    isinstance(minimum, int) and 1 <= minimum <= len(atoms),
                    "D-116 matcher distinct-atom threshold is invalid",
                )
        for contradiction in contradictions:
            contradiction_id = contradiction.get("predicate_id")
            contradiction_atom_id = contradiction.get("atom_id")
            patterns = contradiction.get("patterns")
            _require(
                isinstance(contradiction_id, str)
                and contradiction_id not in predicate_ids
                and isinstance(contradiction_atom_id, str)
                and contradiction_atom_id
                and isinstance(patterns, list)
                and patterns,
                "D-116 contradiction grammar is invalid",
            )
            predicate_ids.add(contradiction_id)
            for pattern in patterns:
                _require(isinstance(pattern, str) and pattern, "D-116 contradiction regex is empty")
                try:
                    re.compile(pattern, flags=re.ASCII)
                except re.error as exc:
                    raise D116SignalContractError(
                        f"D-116 contradiction regex is invalid: {contradiction_id}"
                    ) from exc


def _signal_input_contract() -> dict[str, Any]:
    return {
        "schema_version": PROJECTION_SCHEMA_VERSION,
        "allowed_fields_in_order": ["issue_title", "issue_description", "language"],
        "exact_key_set_required": True,
        "supported_languages": ["python"],
        "canonicalization": {
            "unicode": "NFKC",
            "line_endings": "LF-before-whitespace-collapse",
            "case": "unicode-casefold",
            "whitespace": "collapse-runs-to-ascii-space-and-trim",
            "hash": "sha256-of-canonical-json",
        },
        "boundary_behavior": {
            "raw_manifest_valid_string_values_are_canonicalized": True,
            "classifier_accepts_only_exact_canonical_projection": True,
            "wrong-type-empty-extra-missing-or-noncanonical-projection": "CONTRACT_ERROR",
            "valid-canonical-unsupported-language": "ABSTAIN",
        },
        "forbidden_classifier_inputs": [
            "task-id",
            "directory-or-file-path",
            "split",
            "repository-url-or-name",
            "base-commit",
            "tags",
            "visible-check-id-or-command",
            "allowed-or-forbidden-paths",
            "d112-hypothesized-group",
            "source-memory-or-group-association",
            "phase",
            "trace-or-patch",
            "test-or-evaluator-result",
            "private-hidden-reference-known-bad-or-held-out-result",
        ],
        "phase_independent_signal_required": True,
        "same_public_projection_same_signal_across_phases_required": True,
    }


def _signal_result_contract() -> dict[str, Any]:
    return {
        "schema_version": RESULT_SCHEMA_VERSION,
        "signal_semantics": "public-applicability-not-failure-cause-ground-truth",
        "decision_enum": ["SELECT", "ABSTAIN"],
        "selected_group_domain": [
            "platform-emulation-matrix-gap",
            "request-context-propagation-gap",
            "exception-origin-state-conflation",
            None,
        ],
        "required_fields": [
            "schema_version",
            "contract_version",
            "canonical_input_sha256",
            "decision",
            "selected_group_id",
            "matched_required_predicates",
            "missing_required_predicates",
            "contradiction_predicates",
            "competing_group_ids",
            "evidence_spans",
            "reason_code",
        ],
        "evidence_span_coordinate_contract": (
            "field plus zero-based Unicode-code-point half-open start/end over canonical value"
        ),
        "result_collection_contract": {
            "matched_required_predicates": (
                "unique predicate-id strings for fully satisfied predicates, ordered by group "
                "order then required-predicate order"
            ),
            "missing_required_predicates": (
                "unique predicate-id strings for unsatisfied predicates, ordered by group order "
                "then required-predicate order"
            ),
            "contradiction_predicates": (
                "unique matched contradiction predicate-id strings in group and declaration order"
            ),
            "competing_group_ids": (
                "all fully supported semantic-group-id strings in taxonomy group order; empty for "
                "no full group and one element for SELECT"
            ),
            "evidence_spans": (
                "selected tuples for every matched required predicate plus the selected first "
                "match for every contradiction; order by the evidence-span ordering contract"
            ),
            "all_collections_are_json_arrays": True,
            "duplicate_identifiers_allowed": False,
            "null_elements_allowed": False,
        },
        "contract_error_is_not_a_signal_result": True,
        "select_reason_code": "SELECT_UNIQUE_FULL_GROUP",
        "abstain_reason_codes_in_precedence_order": [
            "UNSUPPORTED_LANGUAGE",
            "CONTRADICTION_PRESENT",
            "MULTIPLE_FULL_GROUPS",
            "PARTIAL_PREDICATE_EVIDENCE",
            "NO_FULL_GROUP",
        ],
        "contract_error_reason_codes": [
            "INVALID_PROJECTION_KEY_SET",
            "INVALID_PROJECTION_VALUE_TYPE",
            "EMPTY_PROJECTION_VALUE",
            "NONCANONICAL_PROJECTION_VALUE",
            "PROJECTION_HASH_MISMATCH",
            "INVALID_RESULT_SPAN",
        ],
        "select_requires_exactly_one_fully_supported_group": True,
        "select_establishes_true_relevance": False,
        "abstain_selected_group_must_be_null": True,
        "confidence_probability_allowed_before_calibration": False,
        "numeric_failure_class_component_mapping_authorized": False,
        "runtime_memory_selection_authorized": False,
    }


def _abstention_contract() -> dict[str, Any]:
    return {
        "contract_version": "deterministic-abstention-d116-v1",
        "abstain_when": [
            "no-group-satisfies-every-required-predicate",
            "more-than-one-group-satisfies-every-required-predicate",
            "any-required-predicate-has-only-partial-evidence",
            "a-contradiction-predicate-is-present",
            "language-is-not-supported",
        ],
        "invalid_or_noncanonical_input_behavior": "CONTRACT_ERROR-before-matching",
        "abstain_means_unknown_not_negative_ground_truth": True,
        "abstain_to_numeric_zero_mapping_authorized": False,
        "ties_must_abstain": True,
        "fallback_to-semantic-top_allowed": False,
    }


def _prospective_calibration_plan(inventory: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    eligible = [row for row in inventory if row["eligibility"] == "prospective-calibration"]
    bootstrap = [row for row in inventory if row["eligibility"] == "bootstrap-excluded"]
    spec_by_path = {str(spec["path"]): spec for spec in PUBLIC_FILE_SPECS}
    source_anchors = [
        row
        for row in eligible
        if spec_by_path[row["path"]]["case_role"] == "source-anchor-conformance"
    ]
    independent = [
        row for row in eligible if spec_by_path[row["path"]]["independent_positive"] is True
    ]
    _require(len(eligible) == 8 and len(bootstrap) == 2, "D-116 calibration inventory drifted")
    _require(len(source_anchors) == 2 and not independent, "D-116 source-anchor counts drifted")
    return {
        "plan_version": "prospective-public-calibration-plan-d116-v1",
        "plan_only_no_execution": True,
        "current_panel_used_during_contract_authoring": True,
        "current_panel_blind_validation": False,
        "candidate_expectations_are_ground_truth": False,
        "public_inventory_count": len(inventory),
        "eligible_case_count": len(eligible),
        "bootstrap_excluded_count": len(bootstrap),
        "source_anchor_conformance_count": len(source_anchors),
        "independent_positive_count": len(independent),
        "classifier_inputs": [
            {
                "input_ref": row["classifier_projection"]["projection_sha256"],
                "classifier_payload": row["classifier_projection"]["projection"],
                "classifier_payload_sha256": row["classifier_projection"]["projection_sha256"],
            }
            for row in eligible
        ],
        "review_expectations": [
            {
                "input_ref": row["classifier_projection"]["projection_sha256"],
                "source_path_for_review_only": row["path"],
                "case_role": spec_by_path[row["path"]]["case_role"],
                "candidate_expectation": spec_by_path[row["path"]]["candidate_expectation"],
                "candidate_group_id": spec_by_path[row["path"]]["candidate_group_id"],
                "acceptance_included": spec_by_path[row["path"]]["acceptance_included"],
                "independent_positive": spec_by_path[row["path"]]["independent_positive"],
                "expectation_is_ground_truth": False,
            }
            for row in eligible
        ],
        "classifier_executor_receives_review_expectations": False,
        "classifier_executor_argument": "classifier_inputs[].classifier_payload-only",
        "bootstrap_exclusions": [dict(row) for row in bootstrap],
        "source_anchor_overlap_counts_as_independent_evidence": False,
        "moto_d112_hypothesis_counts_as_label": False,
        "moto_case_included_in_mechanical_acceptance": False,
        "minimum_independent_positive_per_group_for_execution_admission": 1,
        "future_controls_acquired_after_matcher_contract_hash_is_sealed": True,
        "future_control_selection_may_use_matcher_output": False,
        "future_control_label_adjudication_may_use_matcher_output": False,
        "future_control_acquisition_blinded_to_matcher_output": True,
        "future_control_source_pool_must_preexist_d116": True,
        "future_control_issue_prose_authoring_or_rewriting_after_d116_allowed": False,
        "future_control_pool_cutoff_must_precede": APPROVAL_RECORDED_AT,
        "future_control_pool_bytes_cutoff_and_provenance_must_be_hashed": True,
        "future_exact_pool_membership_manifest_or_exhaustive_inclusion_rule_must_predate_d116": (
            True
        ),
        "future_exact_pool_membership_manifest_bytes_and_hash_required": True,
        "future_pool_assembler_may_view_matcher_grammar_hash_or_output": False,
        "future_pool_assembler_must_be_isolated_from_grammar_observers": True,
        "future_selector_and_adjudicator_may_view_matcher_grammar_or_hash": False,
        "future_selector_and_adjudicator_receive_only_d105_applicability_rubric": True,
        "future_selector_and_adjudicator_must_be_isolated_from_grammar_observers": True,
        "current_process_or_agent_is_eligible_as_blind_selector": False,
        "if_blinding_cannot_be_enforced_mark_controls_post_hoc_and_independent_false": True,
        "pool_assembler_selector_or_adjudicator_blinding_failure_triggers_fallback": True,
        "matcher_grammar_change_after_control_acquisition_allowed": False,
        "grammar_change_requires_new_contract_version_and_invalidates_blind_status": True,
        "independent_positive_groups_available": [],
        "groups_missing_independent_positive": [
            "platform-emulation-matrix-gap",
            "request-context-propagation-gap",
            "exception-origin-state-conflation",
        ],
        "strict_public_source_anchor_expectations": {
            "platform-emulation-matrix-gap": "SELECT-on-pyfakefs-source-anchor-only",
            "request-context-propagation-gap": "SELECT-on-hf-hub-source-anchor-only",
            "exception-origin-state-conflation": (
                "ABSTAIN-on-tox-because-public-prose-does-not-state-S3-shared-error-boundary"
            ),
        },
        "synthetic_conformance_plan": {
            "plan_only_no_execution": True,
            "required_before_any_independent_control_is_scored": True,
            "synthetic_cases_count_as_independent_calibration_evidence": False,
            "cases": [
                {
                    "case_id": "platform-conformance-positive",
                    "purpose": (
                        "emulated versus native behavior, final-versus-traversal effect, and two "
                        "public branch dimensions"
                    ),
                    "expected_outcome": "SELECT-platform-emulation-matrix-gap",
                },
                {
                    "case_id": "context-conformance-positive",
                    "purpose": (
                        "client-selected context contrasted with default ownership and preserved "
                        "through every access path"
                    ),
                    "expected_outcome": "SELECT-request-context-propagation-gap",
                },
                {
                    "case_id": "semantic-conformance-positive",
                    "purpose": (
                        "missing versus existing-empty state across two stages explicitly "
                        "collapsed at one error boundary"
                    ),
                    "expected_outcome": "SELECT-exception-origin-state-conflation",
                },
                {
                    "case_id": "tox-like-missing-S3",
                    "purpose": "S1 and S2 evidence without any shared error-boundary statement",
                    "expected_outcome": "ABSTAIN-partial-evidence",
                },
                {
                    "case_id": "keyword-salad",
                    "purpose": "all common words without the required sentence or clause relations",
                    "expected_outcome": "ABSTAIN-no-full-group",
                },
                {
                    "case_id": "negated-emulation-with-contradiction",
                    "purpose": "negated emulation cue plus intentionally identical-semantics cue",
                    "expected_outcome": "ABSTAIN-contradiction-present",
                },
                {
                    "case_id": "context-partial",
                    "purpose": "custom endpoint without ownership contrast or multiple paths",
                    "expected_outcome": "ABSTAIN-partial-evidence",
                },
                {
                    "case_id": "two-full-group-matches",
                    "purpose": "one canonical projection fully supporting two groups",
                    "expected_outcome": "ABSTAIN-multiple-groups",
                },
                {
                    "case_id": "unsupported-language",
                    "purpose": "valid canonical projection with language other than Python",
                    "expected_outcome": "ABSTAIN-unsupported-language",
                },
                {
                    "case_id": "malformed-or-extra-projection-field",
                    "purpose": "wrong type, noncanonical value, or unknown projection key",
                    "expected_outcome": "CONTRACT_ERROR",
                },
                {
                    "case_id": "forbidden-field-and-phase-invariance",
                    "purpose": (
                        "change task identity, tags, paths, split, and external phase without "
                        "changing the classifier projection"
                    ),
                    "expected_outcome": "projection-and-signal-byte-identical",
                },
                {
                    "case_id": "span-integrity-negative",
                    "purpose": (
                        "off-by-one offset or matched_text not equal to canonical field slice"
                    ),
                    "expected_outcome": "RESULT_VALIDATION_ERROR",
                },
            ],
        },
        "three_class_calibration_ready": False,
        "calibration_execution_ready": False,
        "blocking_reason": (
            "no-blind-independent-public-applicability-positive-for-any-admitted-group"
        ),
        "actual_classifier_execution_count": 0,
        "actual_calibration_result_count": 0,
    }


def _authority(*, candidate_ready: bool) -> dict[str, Any]:
    return {
        "exact_d115_candidate_user_approval_received": True,
        "public_failure_class_signal_contract_authorized": True,
        "public_applicability_signal_contract_prepared": True,
        "formal_matcher_grammar_complete": True,
        "matcher_evaluator_implementation_authorized": False,
        "matcher_evaluator_implemented": False,
        "matcher_evaluator_execution_count": 0,
        "prospective_calibration_candidate_ready": candidate_ready,
        "calibration_execution_candidate_ready": False,
        "actual_classifier_implementation_authorized": False,
        "actual_classifier_implemented": False,
        "classifier_execution_authorized": False,
        "classifier_execution_count": 0,
        "calibration_execution_authorized": False,
        "calibration_execution_count": 0,
        "calibration_results_present": False,
        "three_class_calibrated": False,
        "independent_generalization_validated": False,
        "runtime_classifier_observed": False,
        "true_relevance_established": False,
        "corrected_policy_selected": False,
        "score_policy_correction_authorized": False,
        "score_policy_correction_implemented": False,
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
        "core_campaign_unlocked": False,
        "analysis_ready": False,
        "memory_effect_established": False,
        "negative_transfer_established": False,
    }


def build_d116_approval_receipt(
    *,
    repository: str | Path | None = None,
    context: Mapping[str, Any] | None = None,
    protected_pre: Mapping[str, Any] | None = None,
    implementation_pre: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    repo = _repo_root(repository)
    current = dict(context) if context is not None else _load_exact_context(repo)
    protected = dict(protected_pre) if protected_pre is not None else _protected_input_state(repo)
    implementation = (
        dict(implementation_pre) if implementation_pre is not None else _implementation_state(repo)
    )
    body = {
        "milestone": MILESTONE,
        "evidence_kind": "exact-d115-public-signal-contract-approval-binding",
        "approval_recorded_at": APPROVAL_RECORDED_AT,
        "approval_action_id": EXPECTED_D115_ACTION_HASH,
        "approval_reference": {
            "candidate_id": EXPECTED_D115_CANDIDATE_ID,
            "semantic_body_hash": EXPECTED_D115_CANDIDATE_BODY_SHA,
            "file_sha256": EXPECTED_D115_CANDIDATE_FILE_SHA,
        },
        "approval_reference_mode": "exact-current-user-message-self-attested",
        "approval_statement_code": (
            "exact-d115-triple-d116-contract-calibration-candidate-only-no-runtime-v1"
        ),
        "d115_source_gate": _artifact_binding(
            d115.DEFAULT_SOURCE_GATE_PATH,
            repository=repo,
            payload=current["gate"],
            content=current["gate_content"],
            id_field="gate_id",
        ),
        "d115_candidate": _artifact_binding(
            d115.DEFAULT_CANDIDATE_PATH,
            repository=repo,
            payload=current["candidate"],
            content=current["candidate_content"],
            id_field="candidate_id",
        ),
        "authorized_action_hash": EXPECTED_D115_ACTION_HASH,
        "authorized_scope": current["authorized_scope"],
        "materialization_scope": {
            "new_module_script_test_only": True,
            "new_artifact_paths": [
                DEFAULT_RECEIPT_PATH.as_posix(),
                DEFAULT_PREFLIGHT_PATH.as_posix(),
                DEFAULT_CANDIDATE_PATH.as_posix(),
                DEFAULT_SOURCE_GATE_PATH.as_posix(),
            ],
            "existing_code_artifact_task_or_index_mutation_allowed": False,
            "classifier_implementation_or_execution_allowed": False,
            "calibration_execution_allowed": False,
            "score_retrieval_agent_or_core_allowed": False,
        },
        "protected_pre_state": protected,
        "implementation_pre_state": implementation,
        "claim_semantics": {
            "receipt_is_authorization_binding_not_execution_claim": True,
            "idempotent_exact_materialization_allowed": True,
            "one_use_classifier_execution_claim": False,
            "classifier_execution_consumed": False,
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
        "receipt_id": f"d116approval_{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": body,
    }


def build_d116_preflight(
    receipt: Mapping[str, Any],
    *,
    repository: str | Path | None = None,
    context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    repo = _repo_root(repository)
    current = dict(context) if context is not None else _load_exact_context(repo)
    inventory = current["public_inventory"]
    taxonomy_entries = current["taxonomy"]
    predicate_contract = _prospective_predicate_contract()
    _validate_matcher_grammar(predicate_contract)
    calibration_plan = _prospective_calibration_plan(inventory)
    body = {
        "milestone": MILESTONE,
        "evidence_kind": "public-applicability-signal-contract-and-prospective-calibration",
        "recorded_at": PREFLIGHT_RECORDED_AT,
        "approval_receipt": _output_binding(
            DEFAULT_RECEIPT_PATH,
            repository=repo,
            payload=receipt,
            id_field="receipt_id",
        ),
        "d115_source_gate": _artifact_binding(
            d115.DEFAULT_SOURCE_GATE_PATH,
            repository=repo,
            payload=current["gate"],
            content=current["gate_content"],
            id_field="gate_id",
        ),
        "d115_candidate": _artifact_binding(
            d115.DEFAULT_CANDIDATE_PATH,
            repository=repo,
            payload=current["candidate"],
            content=current["candidate_content"],
            id_field="candidate_id",
        ),
        "input_scope": {
            "public_yaml_inventory_count": 10,
            "prospective_calibration_eligible_count": 8,
            "bootstrap_excluded_count": 2,
            "allowed_splits": ["dev-train", "dev-validation"],
            "classifier_projection_fields": [
                "issue.title",
                "issue.description",
                "repository.language",
            ],
            "tags_used_for_classifier_projection": False,
            "task_id_repository_identity_phase_or_path_used_for_classifier_projection": False,
            "private_hidden_reference_known_bad_trace_patch_or_evaluator_read": False,
            "held_out_result_read": False,
        },
        "public_development_inventory": inventory,
        "taxonomy_contract": {
            "taxonomy_source": "exact-leak-scanned-d105-model-facing-render",
            "d105_gate": _artifact_binding(
                DEFAULT_D105_GATE_PATH,
                repository=repo,
                payload=current["d105_gate"],
                content=current["d105_content"],
                id_field="gate_id",
            ),
            "entry_count": len(taxonomy_entries),
            "entries": taxonomy_entries,
            "taxonomy_is_fallible_process_guidance": True,
            "taxonomy_is_failure_cause_ground_truth": False,
        },
        "signal_input_contract": _signal_input_contract(),
        "signal_result_contract": _signal_result_contract(),
        "deterministic_abstention_contract": _abstention_contract(),
        "prospective_predicate_contract": predicate_contract,
        "prospective_calibration_plan": calibration_plan,
        "conditional_tuple_boundary": {
            "d115_conditional_tuple": current["candidate"]["semantic_body"][
                "conditional_policy_hypothesis"
            ],
            "offline_evaluation_permitted_by_d115": True,
            "evaluated_in_d116": False,
            "reason_not_evaluated": (
                "no-classifier-execution-authority-and-no-three-class-independent-positive"
            ),
            "counterfactual_only": True,
            "runtime_classifier_observed": False,
            "acceptance_evidence": False,
            "corrected_policy_selected": False,
        },
        "protected_pre_state": receipt["semantic_body"]["protected_pre_state"],
        "evidence_boundary": {
            "contract_and_plan_materialized": True,
            "classifier_source_code_created": False,
            "classifier_execution_count": 0,
            "task_level_signal_result_count": 0,
            "calibration_result_count": 0,
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
        "preflight_id": f"d116preflight_{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": body,
    }


def build_d116_candidate(
    receipt: Mapping[str, Any],
    preflight: Mapping[str, Any],
    *,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    repo = _repo_root(repository)
    contract = {
        "taxonomy_contract_hash": sha256_text(
            canonical_json(preflight["semantic_body"]["taxonomy_contract"])
        ),
        "signal_input_contract_hash": sha256_text(
            canonical_json(preflight["semantic_body"]["signal_input_contract"])
        ),
        "signal_result_contract_hash": sha256_text(
            canonical_json(preflight["semantic_body"]["signal_result_contract"])
        ),
        "abstention_contract_hash": sha256_text(
            canonical_json(preflight["semantic_body"]["deterministic_abstention_contract"])
        ),
        "predicate_contract_hash": sha256_text(
            canonical_json(preflight["semantic_body"]["prospective_predicate_contract"])
        ),
    }
    plan = preflight["semantic_body"]["prospective_calibration_plan"]
    proposed_next_action = {
        "action_kind": (
            "prepare-grammar-blind-preexisting-public-applicability-control-acquisition-"
            "protocol-candidate"
        ),
        "future_milestone": "D-117",
        "public_development_inputs_only": True,
        "required_independent_positive_per_group": 1,
        "controls_must_be_acquired_after_exact_d116_matcher_contract_hash_is_sealed": True,
        "controls_must_be_blind_to_post_acquisition_grammar_changes": True,
        "control_selection_may_use_matcher_output": False,
        "control_label_adjudication_may_use_matcher_output": False,
        "control_acquisition_blinded_to_matcher_output": True,
        "source_pool_must_preexist_d116": True,
        "issue_prose_authoring_or_rewriting_after_d116_allowed": False,
        "source_pool_cutoff_must_precede": APPROVAL_RECORDED_AT,
        "pool_bytes_cutoff_and_provenance_hashes_required": True,
        "exact_pool_membership_manifest_or_exhaustive_inclusion_rule_must_predate_d116": True,
        "exact_pool_membership_manifest_bytes_and_hash_required": True,
        "pool_assembler_may_view_matcher_grammar_hash_or_output": False,
        "pool_assembler_isolation_from_grammar_observers_required": True,
        "selector_or_adjudicator_may_view_matcher_grammar_or_hash": False,
        "selector_and_adjudicator_receive_only_d105_applicability_rubric": True,
        "selector_and_adjudicator_isolation_from_grammar_observers_required": True,
        "current_process_or_agent_eligible_as_blind_selector": False,
        "failed_blinding_controls_must_be_marked_post_hoc_and_independent_false": True,
        "pool_assembler_selector_or_adjudicator_blinding_failure_triggers_fallback": True,
        "matcher_grammar_mutation_allowed": False,
        "source_anchor_reuse_as_independent_positive_allowed": False,
        "moto_d112_hypothesis_as_label_allowed": False,
        "tox_source_association_as_public_label_allowed": False,
        "ontology_weakening_allowed": False,
        "new_private_hidden_reference_patch_or_solution_content_allowed": False,
        "classifier_implementation_allowed": False,
        "classifier_execution_allowed": False,
        "calibration_execution_allowed": False,
        "conditional_tuple_evaluation_allowed": False,
        "score_policy_mutation_allowed": False,
        "retrieval_or_runtime_injection_allowed": False,
        "agent_provider_evaluator_or_network_allowed": False,
        "core_or_analysis_campaign_allowed": False,
    }
    body = {
        "milestone": MILESTONE,
        "evidence_kind": (
            "public-applicability-signal-contract-and-blind-control-protocol-candidate"
        ),
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
        "contract_binding": contract,
        "calibration_plan_binding": {
            "plan_version": plan["plan_version"],
            "plan_hash": sha256_text(canonical_json(plan)),
            "eligible_case_count": plan["eligible_case_count"],
            "independent_positive_count": plan["independent_positive_count"],
            "three_class_calibration_ready": plan["three_class_calibration_ready"],
            "calibration_execution_ready": plan["calibration_execution_ready"],
        },
        "candidate_status": (
            "formal-matcher-contract-sealed-calibration-blocked-on-grammar-blind-"
            "preexisting-control-protocol-and-public-applicability-positives"
        ),
        "unresolved_prerequisites": [
            "grammar-blind-preexisting-control-acquisition-protocol-not-yet-materialized",
            "no-blind-independent-public-applicability-positive-for-platform-emulation-matrix-gap",
            "no-blind-independent-public-applicability-positive-for-request-context-propagation-gap",
            "no-blind-independent-public-applicability-positive-for-exception-origin-state-conflation",
            "tox-public-prose-does-not-state-shared-error-boundary",
            "actual-matcher-evaluator-not-implemented-or-executed",
            "calibration-results-absent",
        ],
        "proposed_next_action": proposed_next_action,
        "proposed_next_action_hash": sha256_text(canonical_json(proposed_next_action)),
        "approval_contract": {
            "separate_user_message_required": True,
            "exact_candidate_id_required": True,
            "exact_semantic_body_hash_required": True,
            "exact_file_sha256_required": True,
            "generic_continue_message_is_approval": False,
            "approval_would_only_authorize_blind_control_acquisition_protocol_candidate": True,
            "approval_would_authorize_classifier_or_calibration_execution": False,
            "approval_would_authorize_score_retrieval_agent_or_core": False,
        },
        "authority": _authority(candidate_ready=True),
    }
    body_hash = sha256_text(canonical_json(body))
    return {
        "schema_version": CANDIDATE_SCHEMA_VERSION,
        "candidate_id": f"d116classsignalcandidate_{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": body,
    }


def build_d116_source_gate(
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
    _require(protected_pre == protected_post, "D-116 protected inputs changed during build")
    _require(
        implementation_pre == implementation_post,
        "D-116 implementation changed during build",
    )
    authority = candidate["semantic_body"]["authority"]
    _require(
        authority["actual_classifier_implementation_authorized"] is False
        and authority["matcher_evaluator_implementation_authorized"] is False
        and authority["matcher_evaluator_execution_count"] == 0
        and authority["classifier_execution_count"] == 0
        and authority["calibration_execution_count"] == 0
        and authority["score_policy_correction_authorized"] is False
        and authority["retrieval_ready"] is False
        and authority["core_campaign_unlocked"] is False,
        "D-116 candidate authority expanded",
    )
    body = {
        "milestone": MILESTONE,
        "evidence_kind": "public-applicability-signal-contract-source-gate",
        "recorded_at": GATE_RECORDED_AT,
        "approval_receipt": _output_binding(
            DEFAULT_RECEIPT_PATH,
            repository=repo,
            payload=receipt,
            id_field="receipt_id",
        ),
        "d115_source_gate": _artifact_binding(
            d115.DEFAULT_SOURCE_GATE_PATH,
            repository=repo,
            payload=current["gate"],
            content=current["gate_content"],
            id_field="gate_id",
        ),
        "d115_candidate": _artifact_binding(
            d115.DEFAULT_CANDIDATE_PATH,
            repository=repo,
            payload=current["candidate"],
            content=current["candidate_content"],
            id_field="candidate_id",
        ),
        "preflight": _output_binding(
            DEFAULT_PREFLIGHT_PATH,
            repository=repo,
            payload=preflight,
            id_field="preflight_id",
        ),
        "calibration_candidate": _output_binding(
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
            "exact_d115_candidate_user_approval_bound": True,
            "exact_d115_source_gate_validated": True,
            "exact_d105_taxonomy_renders_bound": True,
            "exact_ten_public_yaml_inventory_bound": True,
            "classifier_projection_excludes_identity_and_runtime_fields": True,
            "deterministic_abstention_contract_prepared": True,
            "formal_matcher_grammar_complete": True,
            "matcher_regex_grammar_compiles": True,
            "matcher_evaluator_implementation_or_execution_absent": True,
            "supported_language_exactly_python": True,
            "evidence_span_coordinates_defined": True,
            "invalid_projection_is_contract_error_not_abstention": True,
            "classifier_inputs_and_review_expectations_separated": True,
            "synthetic_conformance_plan_precommitted": True,
            "current_public_panel_is_not_blind_validation": True,
            "grammar_blind_control_acquisition_protocol_materialized": False,
            "current_process_or_agent_eligible_as_blind_selector": False,
            "candidate_expectations_labeled_non_authoritative": True,
            "source_anchor_overlap_not_counted_as_independent": True,
            "moto_hypothesis_not_promoted_to_label": True,
            "tox_missing_public_S3_recorded": True,
            "independent_positive_count": 0,
            "three_class_calibration_ready": False,
            "actual_classifier_or_calibration_executed": False,
            "protected_inputs_unchanged": True,
            "implementation_unchanged": True,
        },
        "evidence_boundary": dict(preflight["semantic_body"]["evidence_boundary"]),
        "authority": dict(authority),
        "next_gate": (
            "exact-d116-candidate-triple-grammar-blind-preexisting-public-control-"
            "acquisition-protocol-candidate-approval"
        ),
    }
    body_hash = sha256_text(canonical_json(body))
    return {
        "schema_version": SOURCE_GATE_SCHEMA_VERSION,
        "gate_id": f"d116_{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": body,
    }


def _write_exact(path: Path, content: bytes, *, repository: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _require(not _is_linklike(path.parent), "D-116 output parent cannot be linked")
    if path.exists():
        _require(
            _read_stable(path, label="existing D-116 output") == content,
            "D-116 existing output differs from deterministic rebuild",
        )
        return
    try:
        with path.open("xb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as exc:
        raise D116SignalContractError("D-116 output write failed") from exc
    _require(
        _read_stable(path, label="committed D-116 output") == content,
        "D-116 committed output read-back mismatch",
    )


def _parse_time(value: Any, *, label: str) -> datetime:
    _require(isinstance(value, str), f"D-116 {label} timestamp must be a string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise D116SignalContractError(f"D-116 {label} timestamp is invalid") from exc
    _require(parsed.tzinfo is not None, f"D-116 {label} timestamp must be timezone-aware")
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
    _require(times == sorted(times), "D-116 artifact chronology is invalid")


def validate_d116_receipt(
    path: str | Path = DEFAULT_RECEIPT_PATH,
    *,
    repository: str | Path | None = None,
    context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    repo = _repo_root(repository)
    selected = _resolved(path, repository=repo, label="D-116 approval receipt")
    content = _read_stable(selected, label="D-116 approval receipt")
    parsed = _parse_json(content, label="D-116 approval receipt")
    body = _validate_envelope(
        parsed,
        root_keys=RECEIPT_ROOT_KEYS,
        body_keys=RECEIPT_BODY_KEYS,
        id_field="receipt_id",
        id_prefix="d116approval_",
        label="D-116 approval receipt",
    )
    _require(
        body["execution_result_present"] is False
        and body["claim_semantics"]["one_use_classifier_execution_claim"] is False,
        "D-116 receipt overclaims classifier execution",
    )
    current = dict(context) if context is not None else _load_exact_context(repo)
    expected = build_d116_approval_receipt(
        repository=repo,
        context=current,
        protected_pre=_protected_input_state(repo),
        implementation_pre=_implementation_state(repo),
    )
    _require(parsed == expected, "D-116 approval receipt full expected payload mismatch")
    _require(content == _pretty_json(expected), "D-116 approval receipt exact bytes drifted")
    return parsed


def validate_d116_preflight(
    path: str | Path = DEFAULT_PREFLIGHT_PATH,
    *,
    repository: str | Path | None = None,
    context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    repo = _repo_root(repository)
    selected = _resolved(path, repository=repo, label="D-116 preflight")
    content = _read_stable(selected, label="D-116 preflight")
    parsed = _parse_json(content, label="D-116 preflight")
    _validate_envelope(
        parsed,
        root_keys=PREFLIGHT_ROOT_KEYS,
        body_keys=PREFLIGHT_BODY_KEYS,
        id_field="preflight_id",
        id_prefix="d116preflight_",
        label="D-116 preflight",
    )
    current = dict(context) if context is not None else _load_exact_context(repo)
    receipt = validate_d116_receipt(repository=repo, context=current)
    expected = build_d116_preflight(receipt, repository=repo, context=current)
    _require(parsed == expected, "D-116 preflight full expected payload mismatch")
    _require(content == _pretty_json(expected), "D-116 preflight exact bytes drifted")
    _validate_chronology(receipt, parsed)
    return parsed


def validate_d116_candidate(
    path: str | Path = DEFAULT_CANDIDATE_PATH,
    *,
    repository: str | Path | None = None,
    context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    repo = _repo_root(repository)
    selected = _resolved(path, repository=repo, label="D-116 candidate")
    content = _read_stable(selected, label="D-116 candidate")
    parsed = _parse_json(content, label="D-116 candidate")
    body = _validate_envelope(
        parsed,
        root_keys=CANDIDATE_ROOT_KEYS,
        body_keys=CANDIDATE_BODY_KEYS,
        id_field="candidate_id",
        id_prefix="d116classsignalcandidate_",
        label="D-116 candidate",
    )
    _require_exact_keys(
        body["authority"],
        tuple(_authority(candidate_ready=True)),
        label="authority",
    )
    current = dict(context) if context is not None else _load_exact_context(repo)
    receipt = validate_d116_receipt(repository=repo, context=current)
    preflight = validate_d116_preflight(repository=repo, context=current)
    expected = build_d116_candidate(receipt, preflight, repository=repo)
    _require(parsed == expected, "D-116 candidate full expected payload mismatch")
    _require(content == _pretty_json(expected), "D-116 candidate exact bytes drifted")
    _validate_chronology(receipt, preflight, parsed)
    return parsed


def validate_d116_source_gate(
    path: str | Path = DEFAULT_SOURCE_GATE_PATH,
    *,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    repo = _repo_root(repository)
    selected = _resolved(path, repository=repo, label="D-116 source gate")
    content = _read_stable(selected, label="D-116 source gate")
    parsed = _parse_json(content, label="D-116 source gate")
    body = _validate_envelope(
        parsed,
        root_keys=GATE_ROOT_KEYS,
        body_keys=GATE_BODY_KEYS,
        id_field="gate_id",
        id_prefix="d116_",
        label="D-116 source gate",
    )
    current = _load_exact_context(repo)
    receipt = validate_d116_receipt(repository=repo, context=current)
    preflight = validate_d116_preflight(repository=repo, context=current)
    candidate = validate_d116_candidate(repository=repo, context=current)
    protected = _protected_input_state(repo)
    implementation = _implementation_state(repo)
    expected = build_d116_source_gate(
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
    _require(parsed == expected, "D-116 source gate full expected payload mismatch")
    _require(content == _pretty_json(expected), "D-116 source gate exact bytes drifted")
    _validate_chronology(receipt, preflight, candidate, parsed)
    _require(
        body["authority"]["classifier_execution_count"] == 0
        and body["authority"]["calibration_execution_count"] == 0
        and body["authority"]["retrieval_ready"] is False,
        "D-116 source gate authority expanded",
    )
    return parsed


def run_d116_contract_candidate(*, repository: str | Path | None = None) -> dict[str, Any]:
    repo = _repo_root(repository)
    context = _load_exact_context(repo)
    protected_pre = _protected_input_state(repo)
    implementation_pre = _implementation_state(repo)
    receipt = build_d116_approval_receipt(
        repository=repo,
        context=context,
        protected_pre=protected_pre,
        implementation_pre=implementation_pre,
    )
    preflight = build_d116_preflight(receipt, repository=repo, context=context)
    candidate = build_d116_candidate(receipt, preflight, repository=repo)
    outputs = (
        (DEFAULT_RECEIPT_PATH, receipt),
        (DEFAULT_PREFLIGHT_PATH, preflight),
        (DEFAULT_CANDIDATE_PATH, candidate),
    )
    for relative, payload in outputs:
        selected = _resolved(relative, repository=repo, label="D-116 output", must_exist=False)
        _write_exact(selected, _pretty_json(payload), repository=repo)
    validate_d116_receipt(repository=repo, context=context)
    validate_d116_preflight(repository=repo, context=context)
    validate_d116_candidate(repository=repo, context=context)
    protected_post = _protected_input_state(repo)
    implementation_post = _implementation_state(repo)
    gate = build_d116_source_gate(
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
    gate_path = _resolved(
        DEFAULT_SOURCE_GATE_PATH,
        repository=repo,
        label="D-116 source gate",
        must_exist=False,
    )
    _write_exact(gate_path, _pretty_json(gate), repository=repo)
    validate_d116_source_gate(repository=repo)
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
        "classifier_execution_count": 0,
        "calibration_execution_count": 0,
        "three_class_calibrated": False,
        "score_policy_correction_authorized": False,
        "retrieval_ready": False,
        "runtime_memory_injection_count": 0,
        "agent_runs": 0,
        "core_campaign_unlocked": False,
    }
