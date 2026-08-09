"""Approved D-128 successor remediation and repeated no-call preflight.

The approval receipt is created without external activity and binds the sealed
D-128 offline gate, its evidence commit, and a clean source commit.  External
work is permitted only from a receipt-only child commit.  Every external phase
writes durable intent first; an orphaned intent or blocked terminal consumes the
receipt and fails closed.

This module never starts Docker Desktop or a daemon, creates or runs a
container, calls a provider/evaluator/agent, injects or retrieves memory,
creates an execution hash/candidate, or reserves/spends cost.
"""

from __future__ import annotations

import importlib.metadata
import json
import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from patchloop.errors import ContractError
from patchloop.evals import d127_d126_successor_no_call_preflight as d127
from patchloop.evals import d127_pricing_capture as pricing_capture
from patchloop.evals import d128_d127_terminal_successor_offline as offline
from patchloop.evals import d128_docker_no_start_remediation as docker_remediation
from patchloop.runtime import repository_root
from patchloop.util import canonical_json, sha256_bytes, sha256_text

MILESTONE = "D-128"

D128_GATE_ID = "d128_9edb9d1396b2f572c3b1ade623c7c5f6fb3fdf083d17a71680e7f1041bfba7de"
D128_BODY_SHA256 = "sha256:9edb9d1396b2f572c3b1ade623c7c5f6fb3fdf083d17a71680e7f1041bfba7de"
D128_FILE_SHA256 = "sha256:2528aa018908958bdd35b4b6202c75be2b4ca72521d64bfed800284a015a739c"
D128_FILE_BYTES = 12_557
D128_EVIDENCE_COMMIT = "aeac01a04447c731ee5eac4c56e599eb74532a60"
D128_EVIDENCE_TREE = "ded3a8dbbf4612549d3712404cd229ca405458cf"
D128_EVIDENCE_PARENTS = ("3b192e177b2da1302a030eb457ca96f7dae86611",)
D128_GATE_BLOB_OID = "c871908f61bcdf0e012f193479e8644246e0e0bd"

RECEIPT_SCHEMA = "d127-terminal-successor-external-no-call-approval-receipt-d128-v1"
ATTEMPT_SCHEMA = "d127-terminal-successor-external-phase-attempt-intent-d128-v1"
DOCKER_SCHEMA = "d127-terminal-successor-docker-image-remediation-d128-v1"
PRICING_SCHEMA = "d127-terminal-successor-replayable-official-pricing-d128-v1"
PREFLIGHT_SCHEMA = "d127-terminal-successor-repeated-no-call-preflight-d128-v1"
GATE_SCHEMA = "d127-terminal-successor-external-no-call-gate-d128-v1"

RECEIPT_STATUS = "D128_D127_TERMINAL_SUCCESSOR_EXTERNAL_NO_CALL_APPROVAL_RECORDED"
STATIC_READY_STATUS = "D128_STATIC_PREREQUISITES_READY_EXTERNAL_ACTION_NOT_STARTED"
DOCKER_READY_STATUS = "D128_EXACT_DOCKER_IMAGE_READINESS_REMEDIATION_READY"
DOCKER_BLOCKED_STATUS = "D128_EXACT_DOCKER_IMAGE_READINESS_REMEDIATION_OBSERVED_BLOCKED"
PRICING_CAPTURED_STATUS = "D128_REPLAYABLE_OFFICIAL_PRICING_CAPTURED"
PREFLIGHT_READY_STATUS = "D128_REPEATED_NO_CALL_PREFLIGHT_READY_EXECUTION_HASH_BLOCKED"
PREFLIGHT_BLOCKED_STATUS = "D128_REPEATED_NO_CALL_PREFLIGHT_OBSERVED_BLOCKED"
GATE_READY_STATUS = "D128_TERMINAL_SUCCESSOR_EXTERNAL_NO_CALL_GATE_READY_EXECUTION_HASH_BLOCKED"
GATE_BLOCKED_STATUS = "D128_TERMINAL_SUCCESSOR_EXTERNAL_NO_CALL_GATE_OBSERVED_BLOCKED"

OFFLINE_GATE_PATH = offline.OUTPUT_PATH
RECEIPT_PATH = Path(
    "reports/live-pilot/artifacts/"
    "d128-d127-terminal-successor-external-no-call-preflight-approval-receipt.json"
)
DOCKER_ATTEMPT_PATH = Path(
    "reports/live-pilot/artifacts/d128-docker-image-readiness-remediation-attempt-intent.json"
)
DOCKER_PATH = Path(
    "reports/live-pilot/artifacts/d128-exact-docker-image-readiness-remediation-observation.json"
)
REMEDIATION_ATTEMPT_PATH = DOCKER_ATTEMPT_PATH
REMEDIATION_PATH = DOCKER_PATH
PRICING_ATTEMPT_PATH = Path(
    "reports/live-pilot/artifacts/d128-official-pricing-capture-attempt-intent.json"
)
PRICING_PATH = Path("reports/live-pilot/artifacts/d128-replayable-official-pricing-evidence.json")
PREFLIGHT_ATTEMPT_PATH = Path(
    "reports/live-pilot/artifacts/d128-read-only-preflight-attempt-intent.json"
)
PREFLIGHT_PATH = Path("reports/live-pilot/artifacts/d128-repeated-no-call-readiness-preflight.json")
GATE_PATH = Path(
    "reports/live-pilot/artifacts/d128-terminal-successor-external-no-call-preflight-gate.json"
)

APPROVED_SCOPE = tuple(offline.FUTURE_APPROVED_SCOPE)
NOT_AUTHORIZED = tuple(offline.FUTURE_NOT_AUTHORIZED)
DOCKER_CLI_VERSION = offline.DOCKER_CLI_VERSION
DOCKER_CLI_BYTES = offline.DOCKER_CLI_FILE_BYTES
DOCKER_CLI_SHA256 = offline.DOCKER_CLI_FILE_SHA256
DOCKER_IMAGE_REFS = tuple(offline.DOCKER_IMAGE_REFS)
OFFICIAL_API_BASE_URL = d127.OFFICIAL_API_BASE_URL
FRESHNESS_SECONDS = 72 * 60 * 60

FORBIDDEN_ROUTING_ENV_NAMES = d127.FORBIDDEN_ROUTING_ENV_NAMES
FORBIDDEN_PYTHON_ROUTING_ENV_NAMES = d127.FORBIDDEN_PYTHON_ROUTING_ENV_NAMES

_SOURCE_REQUIRED_PATHS = (
    Path("patchloop/evals/d128_terminal_successor_no_call_preflight.py"),
    Path("patchloop/evals/d128_docker_no_start_remediation.py"),
    Path("scripts/build_d128_terminal_successor_no_call_preflight.py"),
    Path("tests/test_d128_terminal_successor_no_call_preflight.py"),
    Path("tests/test_d128_docker_no_start_remediation.py"),
)
_SOURCE_ALLOWED_PATHS = {
    *(path.as_posix() for path in _SOURCE_REQUIRED_PATHS),
    "AGENTS.md",
    "README.md",
    "docs/current-status.md",
    "docs/03-contracts.md",
    "docs/04-evaluation-protocol.md",
    "docs/05-implementation-plan.md",
    "docs/06-decisions.md",
    "docs/07-reproduction.md",
    "docs/08-limitations.md",
    "docs/09-evidence.md",
}
_EVIDENCE_DOC_PATHS = {
    "AGENTS.md",
    "README.md",
    "docs/current-status.md",
    "docs/03-contracts.md",
    "docs/04-evaluation-protocol.md",
    "docs/05-implementation-plan.md",
    "docs/06-decisions.md",
    "docs/07-reproduction.md",
    "docs/08-limitations.md",
    "docs/09-evidence.md",
}

_PHASE_PATHS = {
    "docker-image-readiness-remediation": (DOCKER_ATTEMPT_PATH, DOCKER_PATH),
    "official-pricing-capture": (PRICING_ATTEMPT_PATH, PRICING_PATH),
    "read-only-no-call-preflight": (PREFLIGHT_ATTEMPT_PATH, PREFLIGHT_PATH),
}
_PHASE_ACTIONS = {
    "docker-image-readiness-remediation": [
        "observe-already-running-docker-desktop-linux-daemon-and-exact-images-read-only",
        "pull-only-moto-and-babel-exact-digest-images-when-confirmed-absent",
        "never-start-docker-desktop-or-daemon",
    ],
    "official-pricing-capture": [
        "perform-at-most-four-unauthenticated-official-doc-get-requests",
        "retain-at-most-128000-decoded-entity-bytes-for-replay",
    ],
    "read-only-no-call-preflight": [
        "perform-exactly-two-three-command-read-only-local-docker-snapshots",
        "construct-local-sdk-client-against-rejecting-mock-transport",
    ],
}
_EXTERNAL_OUTPUT_PATHS = (
    DOCKER_ATTEMPT_PATH,
    DOCKER_PATH,
    PRICING_ATTEMPT_PATH,
    PRICING_PATH,
    PREFLIGHT_ATTEMPT_PATH,
    PREFLIGHT_PATH,
    GATE_PATH,
)

_LOADED_MODULE_PATHS = (
    ("d128-orchestrator", Path("patchloop/evals/d128_terminal_successor_no_call_preflight.py")),
    (
        "d128-docker-no-start-remediation",
        Path("patchloop/evals/d128_docker_no_start_remediation.py"),
    ),
    ("d127-pricing-capture", Path("patchloop/evals/d127_pricing_capture.py")),
    ("d127-source-sdk-support", Path("patchloop/evals/d127_d126_successor_no_call_preflight.py")),
    ("d128-offline-predecessor", Path("patchloop/evals/d128_d127_terminal_successor_offline.py")),
)

ROOT_KEYS = ("schema_version", "artifact_id", "semantic_body_hash", "semantic_body")
RECEIPT_BODY_KEYS = (
    "milestone",
    "evidence_kind",
    "recorded_at",
    "status",
    "predecessor_binding",
    "manual_prerequisite_attestation",
    "approval",
    "source_identity",
    "loaded_module_bindings",
    "authority",
    "evidence_boundary",
)
ATTEMPT_BODY_KEYS = (
    "milestone",
    "evidence_kind",
    "recorded_at",
    "status",
    "phase",
    "receipt_binding",
    "source_identity",
    "receipt_commit_identity",
    "loaded_module_bindings",
    "authority",
    "failure_boundary",
)
DOCKER_BODY_KEYS = (
    "milestone",
    "evidence_kind",
    "recorded_at",
    "status",
    "receipt_binding",
    "attempt_binding",
    "source_identity",
    "receipt_commit_identity",
    "manual_prerequisite_attestation",
    "observation",
    "authority",
)
PRICING_BODY_KEYS = (
    "milestone",
    "evidence_kind",
    "recorded_at",
    "status",
    "receipt_binding",
    "attempt_binding",
    "source_identity",
    "receipt_commit_identity",
    "docker_binding",
    "official_pricing_evidence",
    "authority",
)
PREFLIGHT_BODY_KEYS = (
    "milestone",
    "evidence_kind",
    "recorded_at",
    "status",
    "receipt_binding",
    "attempt_binding",
    "source_identity",
    "receipt_commit_identity",
    "docker_binding",
    "pricing_binding",
    "pricing_observed_at",
    "pricing_age_microseconds",
    "approved_docker_cli_bindings",
    "docker_readiness_snapshots",
    "docker_snapshots_stable",
    "sdk_credential_factory_observation",
    "observed_blockers",
    "authority",
)
GATE_BODY_KEYS = (
    "milestone",
    "evidence_kind",
    "recorded_at",
    "status",
    "receipt_binding",
    "source_identity",
    "receipt_commit_identity",
    "docker_binding",
    "pricing_binding",
    "preflight_binding",
    "qualification",
    "authority",
    "next_gate",
)


class D128PreflightError(ContractError):
    """Raised when the D-128 successor contract fails closed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise D128PreflightError(message)


def _repo_root(repository: str | Path | None) -> Path:
    selected = Path(repository) if repository is not None else repository_root()
    try:
        root = selected.resolve(strict=True)
    except OSError as exc:
        raise D128PreflightError("D-128 repository root is unavailable") from exc
    _require(root.is_dir(), "D-128 repository root is not a directory")
    return root


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _parse_time(value: Any, *, label: str = "recorded_at") -> datetime:
    _require(isinstance(value, str) and value.endswith("Z"), f"D-128 {label} differs")
    try:
        parsed = datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except ValueError as exc:
        raise D128PreflightError(f"D-128 {label} differs") from exc
    _require(parsed.tzinfo is not None, f"D-128 {label} differs")
    return parsed.astimezone(UTC)


def _pretty_bytes(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, ensure_ascii=True, indent=2) + "\n").encode("utf-8")


def _artifact_envelope(schema: str, prefix: str, body: dict[str, Any]) -> dict[str, Any]:
    body_hash = sha256_text(canonical_json(body))
    payload = {
        "schema_version": schema,
        "artifact_id": f"{prefix}{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": body,
    }
    _require(tuple(payload) == ROOT_KEYS, "D-128 artifact root fields differ")
    return payload


def _stable_read(root: Path, path: Path) -> bytes:
    try:
        return d127._stable_read(root, path)
    except ContractError as exc:
        raise D128PreflightError(f"D-128 cannot stably read {path.as_posix()}") from exc


def _write_new(root: Path, path: Path, content: bytes) -> None:
    try:
        d127._write_new(root, path, content)
    except ContractError as exc:
        raise D128PreflightError(f"D-128 append-only write failed: {path.as_posix()}") from exc


def _load_artifact(root: Path, path: Path, *, schema: str, prefix: str) -> dict[str, Any]:
    try:
        return d127._load_artifact(root, path, schema=schema, prefix=prefix)
    except ContractError as exc:
        raise D128PreflightError(f"D-128 artifact validation failed: {path.as_posix()}") from exc


def _artifact_binding(root: Path, path: Path) -> dict[str, Any]:
    try:
        return d127._artifact_binding(root, path)
    except ContractError as exc:
        raise D128PreflightError(f"D-128 artifact binding failed: {path.as_posix()}") from exc


def _source_identity(root: Path, *, allowed_outputs: tuple[Path, ...] = ()) -> dict[str, Any]:
    try:
        return d127._source_identity(root, allowed_outputs=allowed_outputs)
    except ContractError as exc:
        raise D128PreflightError("D-128 clean source identity failed") from exc


def _sdk_observation(
    root: Path, source: dict[str, Any], factory_checks: dict[str, bool]
) -> dict[str, Any]:
    try:
        return d127._sdk_observation(root, source, factory_checks)
    except ContractError as exc:
        raise D128PreflightError("D-128 SDK no-call observation failed") from exc


def _authority_zero_boundary() -> dict[str, Any]:
    return {
        "provider_calls_made": 0,
        "evaluator_calls_made": 0,
        "agent_runs_started": 0,
        "runtime_memory_injection_count": 0,
        "retrieval_call_count": 0,
        "container_create_start_run_exec_count": 0,
        "execution_hash_created": False,
        "execution_candidate_created": False,
        "cost_reserved_or_spent_usd": "0",
    }


def _offline_gate_binding(root: Path) -> dict[str, Any]:
    result = offline.validate_d128_offline_source_gate(repository=root)
    _require(result["gate_id"] == D128_GATE_ID, "D-128 offline gate ID differs")
    _require(result["semantic_body_hash"] == D128_BODY_SHA256, "D-128 offline body SHA differs")
    _require(result["file_sha256"] == D128_FILE_SHA256, "D-128 offline file SHA differs")
    _require(result["file_bytes"] == D128_FILE_BYTES, "D-128 offline file bytes differ")
    raw = _stable_read(root, OFFLINE_GATE_PATH)
    _require(len(raw) == D128_FILE_BYTES, "D-128 offline gate byte count differs")
    _require(sha256_bytes(raw) == D128_FILE_SHA256, "D-128 offline gate file SHA differs")
    commit_tree = d127._run_git(root, "rev-parse", f"{D128_EVIDENCE_COMMIT}^{{tree}}")
    ancestry = d127._run_git(root, "rev-list", "--parents", "-n", "1", D128_EVIDENCE_COMMIT).split()
    _require(commit_tree == D128_EVIDENCE_TREE, "D-128 approved evidence tree differs")
    _require(
        ancestry == [D128_EVIDENCE_COMMIT, *D128_EVIDENCE_PARENTS],
        "D-128 approved evidence ancestry differs",
    )
    committed = d127._run_git_bytes(
        root,
        "cat-file",
        "blob",
        f"{D128_EVIDENCE_COMMIT}:{OFFLINE_GATE_PATH.as_posix()}",
    )
    blob_oid = d127._run_git(
        root, "rev-parse", f"{D128_EVIDENCE_COMMIT}:{OFFLINE_GATE_PATH.as_posix()}"
    )
    _require(committed == raw, "D-128 offline gate differs from approved evidence commit")
    _require(blob_oid == D128_GATE_BLOB_OID, "D-128 offline gate blob differs")
    payload = json.loads(raw.decode("utf-8"))
    return {
        "path": OFFLINE_GATE_PATH.as_posix(),
        "schema_version": offline.SCHEMA_VERSION,
        "gate_id": D128_GATE_ID,
        "semantic_body_hash": D128_BODY_SHA256,
        "file_bytes": D128_FILE_BYTES,
        "file_sha256": D128_FILE_SHA256,
        "status": offline.STATUS,
        "recorded_at": payload["semantic_body"]["recorded_at"],
        "evidence_commit": {
            "commit": D128_EVIDENCE_COMMIT,
            "tree": D128_EVIDENCE_TREE,
            "parents": list(D128_EVIDENCE_PARENTS),
            "gate_blob_oid": D128_GATE_BLOB_OID,
            "gate_bytes_match_commit": True,
        },
        "artifact_mutated": False,
    }


def _source_commit_changes(root: Path, commit: str) -> list[list[str]]:
    rows = [
        line.split("\t")
        for line in d127._run_git(
            root,
            "diff",
            "--name-status",
            "--no-renames",
            f"{D128_EVIDENCE_COMMIT}..{commit}",
        ).splitlines()
        if line
    ]
    _require(
        all(len(row) == 2 and row[0] in {"A", "M"} for row in rows),
        "D-128 source commit contains a non-add-or-modify change",
    )
    return rows


def _validate_source_commit_topology(root: Path, source: dict[str, Any]) -> None:
    try:
        d127._validate_source_identity(source, root=root)
    except ContractError as exc:
        raise D128PreflightError("D-128 approved source identity differs") from exc
    _require(
        source["parents"] == [D128_EVIDENCE_COMMIT],
        "D-128 source commit must be a sole child of the approved evidence commit",
    )
    rows = _source_commit_changes(root, source["commit"])
    paths = {row[1] for row in rows}
    _require(paths.issubset(_SOURCE_ALLOWED_PATHS), "D-128 source commit changed unrelated paths")
    _require(
        {path.as_posix() for path in _SOURCE_REQUIRED_PATHS}.issubset(paths),
        "D-128 source commit is missing required source/test paths",
    )


def _loaded_module_files() -> dict[str, Path]:
    return {
        "d128-orchestrator": Path(__file__),
        "d128-docker-no-start-remediation": Path(str(docker_remediation.__file__)),
        "d127-pricing-capture": Path(str(pricing_capture.__file__)),
        "d127-source-sdk-support": Path(str(d127.__file__)),
        "d128-offline-predecessor": Path(str(offline.__file__)),
    }


def _loaded_module_bindings(root: Path, *, source_commit: str) -> list[dict[str, Any]]:
    actual = _loaded_module_files()
    bindings: list[dict[str, Any]] = []
    for role, relative in _LOADED_MODULE_PATHS:
        _require(
            actual[role].resolve(strict=True) == (root / relative).resolve(strict=True),
            f"D-128 loaded module path differs: {role}",
        )
        try:
            binding = d127._committed_file_binding(
                root, source_commit=source_commit, relative=relative
            )
        except ContractError as exc:
            raise D128PreflightError(f"D-128 committed module differs: {role}") from exc
        bindings.append({"role": role, **binding})
    return bindings


def _validate_loaded_module_bindings(root: Path, value: Any, *, source_commit: str) -> None:
    _require(isinstance(value, list), "D-128 module bindings are not a list")
    expected = _loaded_module_bindings(root, source_commit=source_commit)
    _require(canonical_json(value) == canonical_json(expected), "D-128 loaded modules differ")


def _manual_attestation() -> dict[str, Any]:
    return {
        "docker_desktop_linux_daemon_started_manually_by_user": True,
        "user_confirmed_no_preexisting_container_auto_started": True,
        "agent_must_not_start_docker_desktop_or_daemon": True,
        "manual_state_change_does_not_reopen_d127": True,
        "attestation_is_user_self_attested": True,
        "attestation_is_authenticated_or_signed": False,
        "container_auto_start_state_independently_observed_by_agent": False,
    }


def _receipt_body(
    root: Path,
    *,
    recorded_at: str,
    source: dict[str, Any],
    module_bindings: list[dict[str, Any]],
) -> dict[str, Any]:
    _parse_time(recorded_at)
    _validate_source_commit_topology(root, source)
    _validate_loaded_module_bindings(root, module_bindings, source_commit=source["commit"])
    predecessor = _offline_gate_binding(root)
    _require(
        _parse_time(predecessor["recorded_at"], label="offline gate recorded_at")
        <= _parse_time(recorded_at),
        "D-128 receipt predates the offline gate",
    )
    return {
        "milestone": MILESTONE,
        "evidence_kind": "exact-d127-terminal-successor-external-no-call-user-approval-receipt",
        "recorded_at": recorded_at,
        "status": RECEIPT_STATUS,
        "predecessor_binding": predecessor,
        "manual_prerequisite_attestation": _manual_attestation(),
        "approval": {
            "statement_code": (
                "D128_D127_TERMINAL_SUCCESSOR_EXTERNAL_NO_CALL_APPROVAL_KO_20260809_V1"
            ),
            "approved_scope": list(APPROVED_SCOPE),
            "explicitly_not_authorized": list(NOT_AUTHORIZED),
            "approved_docker_cli": {
                "version": DOCKER_CLI_VERSION,
                "file_bytes": DOCKER_CLI_BYTES,
                "file_sha256": DOCKER_CLI_SHA256,
            },
            "approved_exact_image_refs": list(DOCKER_IMAGE_REFS),
            "approval_is_self_attested": True,
            "approval_is_authenticated_or_signed": False,
        },
        "source_identity": source,
        "loaded_module_bindings": module_bindings,
        "authority": {
            "receipt_creation_authorized": True,
            "already_running_daemon_readiness_authorized": True,
            "exact_missing_image_pull_authorized": True,
            "official_pricing_lookup_authorized": True,
            "sdk_credential_endpoint_no_call_preflight_authorized": True,
            "local_source_test_doc_commit_authorized": True,
            "docker_desktop_or_daemon_start_authorized": False,
            "provider_evaluator_agent_execution_authorized": False,
            "runtime_memory_injection_or_retrieval_authorized": False,
            "container_create_start_run_exec_authorized": False,
            "execution_hash_or_candidate_authorized": False,
            "cost_reservation_or_spend_authorized": False,
            "four_row_ac_execution_authorized": False,
        },
        "evidence_boundary": {
            "receipt_does_not_prove_environment_readiness": True,
            "receipt_creation_makes_no_external_call": True,
            "receipt_must_be_committed_as_the_only_change_before_external_action": True,
            "source_commit_and_receipt_commit_are_distinct_to_avoid_self_reference": True,
            "manual_no_auto_start_fact_is_not_independently_observed": True,
            "receipt_output_is_append_only_new_or_exact_idempotent": True,
        },
    }


def _load_receipt(root: Path) -> dict[str, Any]:
    payload = _load_artifact(root, RECEIPT_PATH, schema=RECEIPT_SCHEMA, prefix="d128approval_")
    body = payload["semantic_body"]
    _require(tuple(body) == RECEIPT_BODY_KEYS, "D-128 receipt body fields differ")
    expected = _receipt_body(
        root,
        recorded_at=body["recorded_at"],
        source=body["source_identity"],
        module_bindings=body["loaded_module_bindings"],
    )
    _require(canonical_json(body) == canonical_json(expected), "D-128 receipt body differs")
    return payload


def create_d128_approval_receipt(*, repository: str | Path | None = None) -> dict[str, Any]:
    """Create the exact D-128 approval receipt without external calls."""

    root = _repo_root(repository)
    if (root / RECEIPT_PATH).exists():
        payload = _load_receipt(root)
    else:
        _require(
            not any((root / path).exists() for path in _EXTERNAL_OUTPUT_PATHS),
            "D-128 downstream evidence exists without approval receipt",
        )
        source = _source_identity(root)
        _validate_source_commit_topology(root, source)
        modules = _loaded_module_bindings(root, source_commit=source["commit"])
        payload = _artifact_envelope(
            RECEIPT_SCHEMA,
            "d128approval_",
            _receipt_body(root, recorded_at=_now(), source=source, module_bindings=modules),
        )
        _write_new(root, RECEIPT_PATH, _pretty_bytes(payload))
        payload = _load_receipt(root)
    raw = _stable_read(root, RECEIPT_PATH)
    return {
        "status": RECEIPT_STATUS,
        "artifact_id": payload["artifact_id"],
        "semantic_body_hash": payload["semantic_body_hash"],
        "file_bytes": len(raw),
        "file_sha256": sha256_bytes(raw),
        "source_commit": payload["semantic_body"]["source_identity"]["commit"],
        "external_activity_started": False,
    }


def _validate_receipt_commit_identity(
    root: Path,
    value: Any,
    *,
    source: dict[str, Any],
) -> None:
    _require(
        isinstance(value, dict)
        and tuple(value)
        == (
            "commit",
            "tree",
            "parents",
            "branch",
            "receipt_binding",
            "receipt_only_child_of_source",
            "source_module_bytes_unchanged",
        ),
        "D-128 receipt commit identity fields differ",
    )
    _require(
        re.fullmatch(r"[0-9a-f]{40}", value["commit"]) is not None
        and re.fullmatch(r"[0-9a-f]{40}", value["tree"]) is not None,
        "D-128 receipt commit identity differs",
    )
    ancestry = d127._run_git(root, "rev-list", "--parents", "-n", "1", value["commit"]).split()
    _require(
        ancestry == [value["commit"], source["commit"]],
        "D-128 receipt commit is not a sole child of the source commit",
    )
    _require(
        d127._run_git(root, "rev-parse", f"{value['commit']}^{{tree}}") == value["tree"],
        "D-128 receipt commit tree differs",
    )
    rows = [
        line.split("\t")
        for line in d127._run_git(
            root,
            "diff",
            "--name-status",
            "--no-renames",
            f"{source['commit']}..{value['commit']}",
        ).splitlines()
        if line
    ]
    _require(
        rows == [["A", RECEIPT_PATH.as_posix()]],
        "D-128 receipt commit must add only the approval receipt",
    )
    committed = d127._run_git_bytes(
        root, "cat-file", "blob", f"{value['commit']}:{RECEIPT_PATH.as_posix()}"
    )
    _require(committed == _stable_read(root, RECEIPT_PATH), "D-128 committed receipt differs")
    _require(
        value["receipt_binding"] == _artifact_binding(root, RECEIPT_PATH),
        "D-128 receipt commit artifact binding differs",
    )
    _require(value["receipt_only_child_of_source"] is True, "D-128 receipt-only claim differs")
    _require(value["source_module_bytes_unchanged"] is True, "D-128 module claim differs")


def _current_receipt_commit_identity(
    root: Path,
    *,
    source: dict[str, Any],
    allowed_outputs: tuple[Path, ...],
) -> dict[str, Any]:
    current = _source_identity(root, allowed_outputs=allowed_outputs)
    _require(
        current["parents"] == [source["commit"]],
        "D-128 current HEAD is not the receipt-only child of source",
    )
    value = {
        "commit": current["commit"],
        "tree": current["tree"],
        "parents": current["parents"],
        "branch": current["branch"],
        "receipt_binding": _artifact_binding(root, RECEIPT_PATH),
        "receipt_only_child_of_source": True,
        "source_module_bytes_unchanged": True,
    }
    _validate_receipt_commit_identity(root, value, source=source)
    receipt = _load_receipt(root)["semantic_body"]
    _require(
        _loaded_module_bindings(root, source_commit=source["commit"])
        == receipt["loaded_module_bindings"],
        "D-128 source module bytes changed after receipt",
    )
    return value


def _require_external_helper_contracts() -> None:
    _require(
        docker_remediation.APPROVED_CLI_VERSION == DOCKER_CLI_VERSION
        and docker_remediation.APPROVED_CLI_BYTES == DOCKER_CLI_BYTES
        and docker_remediation.APPROVED_CLI_SHA256 == DOCKER_CLI_SHA256
        and tuple(docker_remediation.EXACT_DOCKER_IMAGES) == DOCKER_IMAGE_REFS,
        "D-128 Docker helper constants differ from exact approval",
    )
    _require(
        not hasattr(docker_remediation, "ALLOW_DAEMON_START_WITH_UNVERIFIED_RESTART_STATE")
        or docker_remediation.ALLOW_DAEMON_START_WITH_UNVERIFIED_RESTART_STATE is False,
        "D-128 Docker helper permits daemon start",
    )
    _require(
        pricing_capture.OFFICIAL_MODEL_PAGE_URL
        == "https://developers.openai.com/api/docs/models/gpt-5.4-mini.md"
        and pricing_capture.MODEL_ID == "gpt-5.4-mini-2026-03-17"
        and str(pricing_capture.INPUT_RATE) == "0.75"
        and str(pricing_capture.CACHED_INPUT_RATE) == "0.075"
        and str(pricing_capture.OUTPUT_RATE) == "4.5"
        and pricing_capture.MAX_DECODED_ENTITY_BYTES == 128_000,
        "D-128 pricing helper constants differ",
    )


def _check_static_prerequisites(root: Path, *, allowed_outputs: tuple[Path, ...]) -> dict[str, Any]:
    receipt = _load_receipt(root)
    source = receipt["semantic_body"]["source_identity"]
    receipt_commit = _current_receipt_commit_identity(
        root, source=source, allowed_outputs=allowed_outputs
    )
    _require_external_helper_contracts()
    api_key_present = bool(os.environ.get("OPENAI_API_KEY"))
    _require(api_key_present, "D-128 OPENAI_API_KEY presence is required")
    routing = {name: bool(os.environ.get(name)) for name in FORBIDDEN_ROUTING_ENV_NAMES}
    _require(not any(routing.values()), "D-128 alternate routing environment is present")
    python_routing = {
        name: bool(os.environ.get(name)) for name in FORBIDDEN_PYTHON_ROUTING_ENV_NAMES
    }
    _require(not any(python_routing.values()), "D-128 Python routing environment is present")
    try:
        docker_cli = d127._approved_docker_cli_identity()
        factory = d127._model_factory_contract(root)
    except ContractError as exc:
        raise D128PreflightError("D-128 static client or Docker CLI contract failed") from exc
    try:
        installed_openai = importlib.metadata.version("openai")
    except importlib.metadata.PackageNotFoundError:
        installed_openai = None
    locked_openai = d127._locked_openai_version(root)
    metadata_checks = {
        "python_is_repository_venv": Path(sys.executable).resolve().is_relative_to(root / ".venv"),
        "openai_sdk_installed": installed_openai is not None,
        "openai_sdk_matches_lock": installed_openai is not None
        and installed_openai == locked_openai,
    }
    _require(all(metadata_checks.values()), "D-128 static SDK metadata is not ready")
    return {
        "status": STATIC_READY_STATUS,
        "receipt": {
            "artifact_id": receipt["artifact_id"],
            "semantic_body_hash": receipt["semantic_body_hash"],
        },
        "source": source,
        "receipt_commit": receipt_commit,
        "loaded_module_bindings": receipt["semantic_body"]["loaded_module_bindings"],
        "manual_prerequisite_attestation": _manual_attestation(),
        "credential": {
            "name": "OPENAI_API_KEY",
            "present": True,
            "value_hash_length_or_prefix_persisted": False,
        },
        "alternate_routing_environment_presence": routing,
        "alternate_routing_environment_values_persisted": False,
        "python_routing_environment_presence": python_routing,
        "python_routing_environment_values_persisted": False,
        "docker_cli": docker_cli,
        "approved_exact_image_refs": list(DOCKER_IMAGE_REFS),
        "production_model_factory_checks": factory,
        "sdk_metadata_checks_without_client_construction": metadata_checks,
        "openai_sdk_installed_version": installed_openai,
        "openai_sdk_locked_version": locked_openai,
        "sdk_client_constructed": False,
        "external_activity": {
            "network_call_count": 0,
            "docker_cli_invocation_count": 0,
            "docker_daemon_call_count": 0,
            "docker_workload_or_mutating_call_count": 0,
            "provider_evaluator_agent_call_count": 0,
        },
        "external_activity_started": False,
        "artifact_created_by_static_check": False,
    }


def check_d128_static_prerequisites(*, repository: str | Path | None = None) -> dict[str, Any]:
    """Validate receipt/source/key/SDK prerequisites without external calls."""

    return _check_static_prerequisites(_repo_root(repository), allowed_outputs=())


def _write_artifact(
    root: Path,
    path: Path,
    *,
    schema: str,
    prefix: str,
    body: dict[str, Any],
) -> None:
    _write_new(root, path, _pretty_bytes(_artifact_envelope(schema, prefix, body)))


def _attempt_body(
    *,
    phase: str,
    receipt_binding: dict[str, Any],
    source: dict[str, Any],
    receipt_commit: dict[str, Any],
    module_bindings: list[dict[str, Any]],
    recorded_at: str,
) -> dict[str, Any]:
    _require(phase in _PHASE_PATHS, "D-128 external phase differs")
    _parse_time(recorded_at, label=f"{phase} attempt recorded_at")
    return {
        "milestone": MILESTONE,
        "evidence_kind": "append-only-external-phase-attempt-intent",
        "recorded_at": recorded_at,
        "status": f"D128_{phase.replace('-', '_').upper()}_ATTEMPT_INTENT_RECORDED",
        "phase": phase,
        "receipt_binding": receipt_binding,
        "source_identity": source,
        "receipt_commit_identity": receipt_commit,
        "loaded_module_bindings": module_bindings,
        "authority": {
            "authorized_actions": _PHASE_ACTIONS[phase],
            "docker_desktop_or_daemon_start_authorized": False,
            "provider_evaluator_agent_execution_authorized": False,
            "runtime_memory_injection_or_retrieval_authorized": False,
            "container_create_start_run_exec_authorized": False,
            "execution_hash_or_candidate_authorized": False,
            "cost_reservation_or_spend_authorized": False,
        },
        "failure_boundary": {
            "intent_is_written_before_first_phase_external_action": True,
            "missing_terminal_artifact_does_not_imply_zero_activity": True,
            "orphaned_attempt_must_not_be_retried_without_separate_exact_approval": True,
            "actual_counts_are_recorded_only_in_the_bound_terminal_artifact": True,
        },
    }


def _validate_attempt_artifact(root: Path, phase: str) -> dict[str, Any]:
    receipt = _load_receipt(root)
    path, _terminal = _PHASE_PATHS[phase]
    prefix = f"d128{phase.replace('-', '')}attempt_"
    payload = _load_artifact(root, path, schema=ATTEMPT_SCHEMA, prefix=prefix)
    body = payload["semantic_body"]
    _require(tuple(body) == ATTEMPT_BODY_KEYS, "D-128 attempt body fields differ")
    _require(
        body["receipt_binding"] == _artifact_binding(root, RECEIPT_PATH)
        and body["receipt_binding"]["artifact_id"] == receipt["artifact_id"],
        "D-128 attempt receipt binding differs",
    )
    source = receipt["semantic_body"]["source_identity"]
    _require(
        canonical_json(body["source_identity"]) == canonical_json(source),
        "D-128 attempt source differs",
    )
    _validate_receipt_commit_identity(root, body["receipt_commit_identity"], source=source)
    _validate_loaded_module_bindings(
        root, body["loaded_module_bindings"], source_commit=source["commit"]
    )
    expected = _attempt_body(
        phase=phase,
        receipt_binding=body["receipt_binding"],
        source=source,
        receipt_commit=body["receipt_commit_identity"],
        module_bindings=body["loaded_module_bindings"],
        recorded_at=body["recorded_at"],
    )
    _require(canonical_json(body) == canonical_json(expected), "D-128 attempt body differs")
    _require(
        _parse_time(receipt["semantic_body"]["recorded_at"], label="receipt recorded_at")
        <= _parse_time(body["recorded_at"], label="attempt recorded_at"),
        "D-128 attempt predates receipt",
    )
    return payload


def _create_attempt_artifact(
    root: Path,
    *,
    phase: str,
    source: dict[str, Any],
    receipt_commit: dict[str, Any],
    module_bindings: list[dict[str, Any]],
) -> dict[str, Any]:
    path, terminal = _PHASE_PATHS[phase]
    _require(not (root / path).exists(), f"D-128 {phase} attempt already exists")
    _require(not (root / terminal).exists(), f"D-128 {phase} terminal exists without attempt")
    body = _attempt_body(
        phase=phase,
        receipt_binding=_artifact_binding(root, RECEIPT_PATH),
        source=source,
        receipt_commit=receipt_commit,
        module_bindings=module_bindings,
        recorded_at=_now(),
    )
    _write_artifact(
        root,
        path,
        schema=ATTEMPT_SCHEMA,
        prefix=f"d128{phase.replace('-', '')}attempt_",
        body=body,
    )
    return _validate_attempt_artifact(root, phase)


def _require_attempt_unchanged(
    root: Path, *, phase: str, expected: dict[str, Any]
) -> dict[str, Any]:
    current = _validate_attempt_artifact(root, phase)
    _require(
        canonical_json(current) == canonical_json(expected),
        f"D-128 {phase} attempt changed after intent persistence",
    )
    return current


def _docker_body(
    *,
    receipt_binding: dict[str, Any],
    attempt_binding: dict[str, Any],
    source: dict[str, Any],
    receipt_commit: dict[str, Any],
    observation: dict[str, Any],
    recorded_at: str,
) -> dict[str, Any]:
    _parse_time(recorded_at, label="Docker terminal recorded_at")
    docker_remediation.validate_docker_no_start_remediation_observation(observation)
    _require(
        observation["daemon_start_attempted"] is False and observation["daemon_start_count"] == 0,
        "D-128 Docker phase crossed the no-daemon-start boundary",
    )
    _require(
        observation["container_create_start_run_exec_count"] == 0
        and observation["docker_workload_call_count"] == 0,
        "D-128 Docker phase crossed the no-container-workload boundary",
    )
    status = DOCKER_READY_STATUS if observation["passed"] else DOCKER_BLOCKED_STATUS
    return {
        "milestone": MILESTONE,
        "evidence_kind": "exact-authorized-already-running-docker-image-remediation-observation",
        "recorded_at": recorded_at,
        "status": status,
        "receipt_binding": receipt_binding,
        "attempt_binding": attempt_binding,
        "source_identity": source,
        "receipt_commit_identity": receipt_commit,
        "manual_prerequisite_attestation": _manual_attestation(),
        "observation": observation,
        "authority": {
            "docker_desktop_or_daemon_start_count": 0,
            "docker_cli_command_count": observation["docker_cli_command_count"],
            "read_only_daemon_or_image_call_count": observation[
                "read_only_daemon_or_image_call_count"
            ],
            "docker_image_pull_call_count": observation["image_pull_call_count"],
            "docker_image_store_mutation_count": observation["image_store_mutation_count"],
            "exact_authorized_images_only": observation["exact_authorized_images"]
            == list(DOCKER_IMAGE_REFS),
            "manual_no_auto_start_attestation_recorded": True,
            "container_auto_start_state_independently_observed": False,
            **_authority_zero_boundary(),
        },
    }


def _validate_docker_artifact(root: Path) -> dict[str, Any]:
    receipt = _load_receipt(root)
    attempt = _validate_attempt_artifact(root, "docker-image-readiness-remediation")
    payload = _load_artifact(
        root, DOCKER_PATH, schema=DOCKER_SCHEMA, prefix="d128dockerremediation_"
    )
    body = payload["semantic_body"]
    _require(tuple(body) == DOCKER_BODY_KEYS, "D-128 Docker body fields differ")
    _require(
        body["receipt_binding"] == _artifact_binding(root, RECEIPT_PATH)
        and body["receipt_binding"]["artifact_id"] == receipt["artifact_id"],
        "D-128 Docker receipt binding differs",
    )
    _require(
        body["attempt_binding"] == _artifact_binding(root, DOCKER_ATTEMPT_PATH)
        and body["attempt_binding"]["artifact_id"] == attempt["artifact_id"],
        "D-128 Docker attempt binding differs",
    )
    _require(
        canonical_json(body["source_identity"])
        == canonical_json(receipt["semantic_body"]["source_identity"])
        == canonical_json(attempt["semantic_body"]["source_identity"]),
        "D-128 Docker source binding differs",
    )
    _require(
        canonical_json(body["receipt_commit_identity"])
        == canonical_json(attempt["semantic_body"]["receipt_commit_identity"]),
        "D-128 Docker receipt commit binding differs",
    )
    _require(
        _parse_time(attempt["semantic_body"]["recorded_at"], label="Docker attempt")
        <= _parse_time(body["recorded_at"], label="Docker terminal"),
        "D-128 Docker chronology differs",
    )
    expected = _docker_body(
        receipt_binding=body["receipt_binding"],
        attempt_binding=body["attempt_binding"],
        source=body["source_identity"],
        receipt_commit=body["receipt_commit_identity"],
        observation=body["observation"],
        recorded_at=body["recorded_at"],
    )
    _require(canonical_json(body) == canonical_json(expected), "D-128 Docker body differs")
    return payload


def _write_docker_terminal(
    root: Path,
    *,
    source: dict[str, Any],
    receipt_commit: dict[str, Any],
    observation: dict[str, Any],
    expected_attempt: dict[str, Any],
) -> dict[str, Any]:
    _require_attempt_unchanged(
        root, phase="docker-image-readiness-remediation", expected=expected_attempt
    )
    body = _docker_body(
        receipt_binding=_artifact_binding(root, RECEIPT_PATH),
        attempt_binding=_artifact_binding(root, DOCKER_ATTEMPT_PATH),
        source=source,
        receipt_commit=receipt_commit,
        observation=observation,
        recorded_at=_now(),
    )
    _write_artifact(
        root,
        DOCKER_PATH,
        schema=DOCKER_SCHEMA,
        prefix="d128dockerremediation_",
        body=body,
    )
    return _validate_docker_artifact(root)


def _pricing_body(
    *,
    receipt_binding: dict[str, Any],
    attempt_binding: dict[str, Any],
    source: dict[str, Any],
    receipt_commit: dict[str, Any],
    docker_binding: dict[str, Any],
    evidence: dict[str, Any],
) -> dict[str, Any]:
    pricing_capture.validate_official_pricing_evidence(evidence)
    observed_at = evidence["observed_at"]
    _parse_time(observed_at, label="pricing observed_at")
    return {
        "milestone": MILESTONE,
        "evidence_kind": "bounded-replayable-official-pricing-decoded-entity",
        "recorded_at": observed_at,
        "status": PRICING_CAPTURED_STATUS,
        "receipt_binding": receipt_binding,
        "attempt_binding": attempt_binding,
        "source_identity": source,
        "receipt_commit_identity": receipt_commit,
        "docker_binding": docker_binding,
        "official_pricing_evidence": evidence,
        "authority": {
            "official_public_get_request_count": evidence["public_get_request_count"],
            "decoded_entity_retained_for_replay": True,
            "decoded_entity_max_bytes": pricing_capture.MAX_DECODED_ENTITY_BYTES,
            "wire_bytes_retained": False,
            "request_auth_or_cookie_sent": False,
            "proxy_use_disabled": True,
            "docker_desktop_or_daemon_start_count": 0,
            **_authority_zero_boundary(),
        },
    }


def _validate_pricing_artifact(root: Path) -> dict[str, Any]:
    receipt = _load_receipt(root)
    attempt = _validate_attempt_artifact(root, "official-pricing-capture")
    docker = _validate_docker_artifact(root)
    _require(
        docker["semantic_body"]["status"] == DOCKER_READY_STATUS,
        "D-128 pricing exists after blocked Docker terminal",
    )
    payload = _load_artifact(root, PRICING_PATH, schema=PRICING_SCHEMA, prefix="d128pricing_")
    body = payload["semantic_body"]
    _require(tuple(body) == PRICING_BODY_KEYS, "D-128 pricing body fields differ")
    _require(
        body["receipt_binding"] == _artifact_binding(root, RECEIPT_PATH),
        "D-128 pricing receipt differs",
    )
    _require(
        body["attempt_binding"] == _artifact_binding(root, PRICING_ATTEMPT_PATH),
        "D-128 pricing attempt differs",
    )
    _require(
        body["docker_binding"] == _artifact_binding(root, DOCKER_PATH),
        "D-128 pricing Docker differs",
    )
    _require(
        body["receipt_binding"]["artifact_id"] == receipt["artifact_id"]
        and body["attempt_binding"]["artifact_id"] == attempt["artifact_id"],
        "D-128 pricing artifact IDs differ",
    )
    _require(
        canonical_json(body["source_identity"])
        == canonical_json(docker["semantic_body"]["source_identity"])
        == canonical_json(attempt["semantic_body"]["source_identity"]),
        "D-128 pricing source differs",
    )
    _require(
        canonical_json(body["receipt_commit_identity"])
        == canonical_json(attempt["semantic_body"]["receipt_commit_identity"]),
        "D-128 pricing receipt commit differs",
    )
    _require(
        _parse_time(docker["semantic_body"]["recorded_at"], label="Docker terminal")
        <= _parse_time(attempt["semantic_body"]["recorded_at"], label="pricing attempt")
        <= _parse_time(body["recorded_at"], label="pricing terminal"),
        "D-128 pricing chronology differs",
    )
    expected = _pricing_body(
        receipt_binding=body["receipt_binding"],
        attempt_binding=body["attempt_binding"],
        source=body["source_identity"],
        receipt_commit=body["receipt_commit_identity"],
        docker_binding=body["docker_binding"],
        evidence=body["official_pricing_evidence"],
    )
    _require(canonical_json(body) == canonical_json(expected), "D-128 pricing body differs")
    return payload


def _write_pricing_terminal(
    root: Path,
    *,
    source: dict[str, Any],
    receipt_commit: dict[str, Any],
    evidence: dict[str, Any],
    expected_attempt: dict[str, Any],
) -> dict[str, Any]:
    _require_attempt_unchanged(root, phase="official-pricing-capture", expected=expected_attempt)
    body = _pricing_body(
        receipt_binding=_artifact_binding(root, RECEIPT_PATH),
        attempt_binding=_artifact_binding(root, PRICING_ATTEMPT_PATH),
        source=source,
        receipt_commit=receipt_commit,
        docker_binding=_artifact_binding(root, DOCKER_PATH),
        evidence=evidence,
    )
    _write_artifact(root, PRICING_PATH, schema=PRICING_SCHEMA, prefix="d128pricing_", body=body)
    return _validate_pricing_artifact(root)


def _pricing_age_microseconds(observed_at: str, recorded_at: str) -> int:
    delta = _parse_time(recorded_at, label="later recorded_at") - _parse_time(
        observed_at, label="pricing observed_at"
    )
    return delta.days * 86_400 * 1_000_000 + delta.seconds * 1_000_000 + delta.microseconds


def _preflight_blockers(
    *,
    docker_observation: dict[str, Any],
    pricing_age_microseconds: int,
    snapshots: list[dict[str, Any]],
    snapshots_stable: bool,
    sdk: dict[str, Any],
    cli_stable: bool,
) -> list[str]:
    blockers: list[str] = []
    if not docker_observation["passed"]:
        blockers.append("exact-docker-image-readiness-remediation-did-not-pass")
    if not 0 <= pricing_age_microseconds <= FRESHNESS_SECONDS * 1_000_000:
        blockers.append("replayable-official-pricing-is-not-fresh-within-72-hours")
    if not all(snapshot["observation"]["passed"] for snapshot in snapshots):
        blockers.append("read-only-docker-readiness-snapshot-failed")
    if not snapshots_stable:
        blockers.append("read-only-docker-readiness-snapshots-are-not-stable")
    if not sdk["passed"]:
        blockers.append("sdk-credential-endpoint-or-production-factory-check-failed")
    if not cli_stable:
        blockers.append("approved-docker-cli-identity-changed")
    return sorted(blockers)


def _preflight_body(
    *,
    receipt_binding: dict[str, Any],
    attempt_binding: dict[str, Any],
    source: dict[str, Any],
    receipt_commit: dict[str, Any],
    docker_binding: dict[str, Any],
    pricing_binding: dict[str, Any],
    docker_observation: dict[str, Any],
    pricing_evidence: dict[str, Any],
    cli_bindings: dict[str, Any],
    snapshots: list[dict[str, Any]],
    sdk: dict[str, Any],
    recorded_at: str,
) -> dict[str, Any]:
    _parse_time(recorded_at, label="preflight recorded_at")
    docker_remediation.validate_docker_no_start_remediation_observation(docker_observation)
    pricing_capture.validate_official_pricing_evidence(pricing_evidence)
    _require(
        isinstance(cli_bindings, dict) and tuple(cli_bindings) == ("before", "after"),
        "D-128 preflight CLI bindings differ",
    )
    _require(
        isinstance(snapshots, list) and len(snapshots) == 2,
        "D-128 preflight requires two Docker snapshots",
    )
    for snapshot in snapshots:
        docker_remediation.validate_docker_readiness_snapshot(snapshot)
    _require(
        isinstance(sdk, dict)
        and type(sdk.get("passed")) is bool
        and sdk.get("network_call_count") == 0,
        "D-128 preflight SDK boundary differs",
    )
    age = _pricing_age_microseconds(pricing_evidence["observed_at"], recorded_at)
    stable = canonical_json(snapshots[0]) == canonical_json(snapshots[1])
    cli_stable = canonical_json(cli_bindings["before"]) == canonical_json(cli_bindings["after"])
    blockers = _preflight_blockers(
        docker_observation=docker_observation,
        pricing_age_microseconds=age,
        snapshots=snapshots,
        snapshots_stable=stable,
        sdk=sdk,
        cli_stable=cli_stable,
    )
    status = PREFLIGHT_READY_STATUS if not blockers else PREFLIGHT_BLOCKED_STATUS
    return {
        "milestone": MILESTONE,
        "evidence_kind": "repeated-read-only-docker-sdk-credential-endpoint-no-call-preflight",
        "recorded_at": recorded_at,
        "status": status,
        "receipt_binding": receipt_binding,
        "attempt_binding": attempt_binding,
        "source_identity": source,
        "receipt_commit_identity": receipt_commit,
        "docker_binding": docker_binding,
        "pricing_binding": pricing_binding,
        "pricing_observed_at": pricing_evidence["observed_at"],
        "pricing_age_microseconds": age,
        "approved_docker_cli_bindings": cli_bindings,
        "docker_readiness_snapshots": snapshots,
        "docker_snapshots_stable": stable,
        "sdk_credential_factory_observation": sdk,
        "observed_blockers": blockers,
        "authority": {
            "official_public_get_request_count": pricing_evidence["public_get_request_count"],
            "docker_desktop_or_daemon_start_count": 0,
            "docker_image_store_mutation_count": docker_observation["image_store_mutation_count"],
            "remediation_docker_cli_command_count": docker_observation["docker_cli_command_count"],
            "read_only_snapshot_docker_cli_command_count": sum(
                snapshot["docker_cli_command_count"] for snapshot in snapshots
            ),
            "sdk_network_call_count": sdk["network_call_count"],
            "sdk_transport_attempt_count": sdk["synthetic_endpoint_probe"][
                "transport_attempt_count"
            ],
            "system_wide_socket_denial_claimed": False,
            "import_side_effect_absence_claimed": False,
            **_authority_zero_boundary(),
        },
    }


def _validate_preflight_artifact(root: Path) -> dict[str, Any]:
    receipt = _load_receipt(root)
    attempt = _validate_attempt_artifact(root, "read-only-no-call-preflight")
    docker = _validate_docker_artifact(root)
    pricing = _validate_pricing_artifact(root)
    payload = _load_artifact(root, PREFLIGHT_PATH, schema=PREFLIGHT_SCHEMA, prefix="d128preflight_")
    body = payload["semantic_body"]
    _require(tuple(body) == PREFLIGHT_BODY_KEYS, "D-128 preflight body fields differ")
    expected_bindings = {
        "receipt_binding": _artifact_binding(root, RECEIPT_PATH),
        "attempt_binding": _artifact_binding(root, PREFLIGHT_ATTEMPT_PATH),
        "docker_binding": _artifact_binding(root, DOCKER_PATH),
        "pricing_binding": _artifact_binding(root, PRICING_PATH),
    }
    for field, binding in expected_bindings.items():
        _require(body[field] == binding, f"D-128 preflight {field} differs")
    _require(
        body["receipt_binding"]["artifact_id"] == receipt["artifact_id"]
        and body["attempt_binding"]["artifact_id"] == attempt["artifact_id"]
        and body["docker_binding"]["artifact_id"] == docker["artifact_id"]
        and body["pricing_binding"]["artifact_id"] == pricing["artifact_id"],
        "D-128 preflight artifact IDs differ",
    )
    _require(
        canonical_json(body["source_identity"])
        == canonical_json(attempt["semantic_body"]["source_identity"])
        == canonical_json(pricing["semantic_body"]["source_identity"]),
        "D-128 preflight source differs",
    )
    _require(
        canonical_json(body["receipt_commit_identity"])
        == canonical_json(attempt["semantic_body"]["receipt_commit_identity"]),
        "D-128 preflight receipt commit differs",
    )
    _require(
        _parse_time(pricing["semantic_body"]["recorded_at"], label="pricing terminal")
        <= _parse_time(attempt["semantic_body"]["recorded_at"], label="preflight attempt")
        <= _parse_time(body["recorded_at"], label="preflight terminal"),
        "D-128 preflight chronology differs",
    )
    try:
        d127._validate_sdk_observation(
            root,
            body["sdk_credential_factory_observation"],
            source=body["source_identity"],
        )
    except ContractError as exc:
        raise D128PreflightError("D-128 preflight SDK observation differs") from exc
    expected = _preflight_body(
        receipt_binding=body["receipt_binding"],
        attempt_binding=body["attempt_binding"],
        source=body["source_identity"],
        receipt_commit=body["receipt_commit_identity"],
        docker_binding=body["docker_binding"],
        pricing_binding=body["pricing_binding"],
        docker_observation=docker["semantic_body"]["observation"],
        pricing_evidence=pricing["semantic_body"]["official_pricing_evidence"],
        cli_bindings=body["approved_docker_cli_bindings"],
        snapshots=body["docker_readiness_snapshots"],
        sdk=body["sdk_credential_factory_observation"],
        recorded_at=body["recorded_at"],
    )
    _require(canonical_json(body) == canonical_json(expected), "D-128 preflight body differs")
    return payload


def _write_preflight_terminal(
    root: Path,
    *,
    source: dict[str, Any],
    receipt_commit: dict[str, Any],
    cli_before: dict[str, Any],
    cli_after: dict[str, Any],
    snapshots: list[dict[str, Any]],
    sdk: dict[str, Any],
    expected_attempt: dict[str, Any],
) -> dict[str, Any]:
    _require_attempt_unchanged(root, phase="read-only-no-call-preflight", expected=expected_attempt)
    docker = _validate_docker_artifact(root)
    pricing = _validate_pricing_artifact(root)
    body = _preflight_body(
        receipt_binding=_artifact_binding(root, RECEIPT_PATH),
        attempt_binding=_artifact_binding(root, PREFLIGHT_ATTEMPT_PATH),
        source=source,
        receipt_commit=receipt_commit,
        docker_binding=_artifact_binding(root, DOCKER_PATH),
        pricing_binding=_artifact_binding(root, PRICING_PATH),
        docker_observation=docker["semantic_body"]["observation"],
        pricing_evidence=pricing["semantic_body"]["official_pricing_evidence"],
        cli_bindings={"before": cli_before, "after": cli_after},
        snapshots=snapshots,
        sdk=sdk,
        recorded_at=_now(),
    )
    _write_artifact(
        root,
        PREFLIGHT_PATH,
        schema=PREFLIGHT_SCHEMA,
        prefix="d128preflight_",
        body=body,
    )
    return _validate_preflight_artifact(root)


def _gate_body(
    *,
    receipt_binding: dict[str, Any],
    source: dict[str, Any],
    receipt_commit: dict[str, Any],
    docker_binding: dict[str, Any],
    pricing_binding: dict[str, Any],
    preflight_binding: dict[str, Any],
    docker_observation: dict[str, Any],
    pricing_evidence: dict[str, Any],
    preflight_body: dict[str, Any],
    recorded_at: str,
) -> dict[str, Any]:
    gate_age = _pricing_age_microseconds(pricing_evidence["observed_at"], recorded_at)
    pricing_fresh = 0 <= gate_age <= FRESHNESS_SECONDS * 1_000_000
    snapshots = preflight_body["docker_readiness_snapshots"]
    sdk = preflight_body["sdk_credential_factory_observation"]
    blockers = list(preflight_body["observed_blockers"])
    if not pricing_fresh:
        blockers.append("replayable-official-pricing-is-not-fresh-at-gate-creation")
    if docker_observation["daemon_start_count"] != 0:
        blockers.append("agent-daemon-start-boundary-not-preserved")
    blockers = sorted(set(blockers))
    ready = not blockers
    status = GATE_READY_STATUS if ready else GATE_BLOCKED_STATUS
    return {
        "milestone": MILESTONE,
        "evidence_kind": "d127-terminal-successor-external-repeated-no-call-gate",
        "recorded_at": recorded_at,
        "status": status,
        "receipt_binding": receipt_binding,
        "source_identity": source,
        "receipt_commit_identity": receipt_commit,
        "docker_binding": docker_binding,
        "pricing_binding": pricing_binding,
        "preflight_binding": preflight_binding,
        "qualification": {
            "manual_daemon_and_no_auto_start_attestation_recorded": True,
            "manual_no_auto_start_fact_independently_observed": False,
            "agent_docker_desktop_or_daemon_start_count": 0,
            "docker_image_readiness_remediation_passed": docker_observation["passed"],
            "official_pricing_decoded_entity_replay_valid": True,
            "official_pricing_wire_bytes_retained": False,
            "official_pricing_origin_signature_present": False,
            "official_pricing_fresh_within_72_hours_at_gate": pricing_fresh,
            "official_pricing_age_microseconds_at_gate": gate_age,
            "two_read_only_docker_snapshots_passed": all(
                snapshot["observation"]["passed"] for snapshot in snapshots
            ),
            "read_only_docker_snapshots_stable": preflight_body["docker_snapshots_stable"],
            "sdk_credential_endpoint_factory_checks_passed": sdk["passed"],
            "sdk_transport_attempt_count": sdk["synthetic_endpoint_probe"][
                "transport_attempt_count"
            ],
            "system_wide_socket_denial_or_import_side_effect_absence_claimed": False,
            "approval_is_self_attested": True,
            "approval_is_authenticated_or_signed": False,
            "observed_blockers": blockers,
            "environment_ready_for_execution_hash": ready,
        },
        "authority": {
            "approved_successor_observations_completed": True,
            "docker_desktop_or_daemon_start_authorized_or_performed": False,
            "provider_evaluator_agent_execution_authorized_or_performed": False,
            "runtime_memory_injection_or_retrieval_authorized_or_performed": False,
            "container_create_start_run_exec_authorized_or_performed": False,
            "execution_hash_authorized_or_created": False,
            "execution_candidate_authorized_or_created": False,
            "cost_reservation_or_spend_authorized_or_performed": False,
            "cost_reserved_or_spent_usd": "0",
        },
        "next_gate": {
            "separate_exact_gate_approval_required": True,
            "execution_hash_or_candidate_must_not_be_created_from_this_approval": True,
            "live_execution_remains_separately_gated": True,
        },
    }


def _validate_gate_artifact(root: Path) -> dict[str, Any]:
    _require_external_helper_contracts()
    receipt = _load_receipt(root)
    docker = _validate_docker_artifact(root)
    pricing = _validate_pricing_artifact(root)
    preflight = _validate_preflight_artifact(root)
    payload = _load_artifact(root, GATE_PATH, schema=GATE_SCHEMA, prefix="d128_")
    body = payload["semantic_body"]
    _require(tuple(body) == GATE_BODY_KEYS, "D-128 gate body fields differ")
    expected_bindings = {
        "receipt_binding": _artifact_binding(root, RECEIPT_PATH),
        "docker_binding": _artifact_binding(root, DOCKER_PATH),
        "pricing_binding": _artifact_binding(root, PRICING_PATH),
        "preflight_binding": _artifact_binding(root, PREFLIGHT_PATH),
    }
    for field, binding in expected_bindings.items():
        _require(body[field] == binding, f"D-128 gate {field} differs")
    _require(
        body["receipt_binding"]["artifact_id"] == receipt["artifact_id"],
        "D-128 gate receipt ID differs",
    )
    _require(
        canonical_json(body["source_identity"])
        == canonical_json(preflight["semantic_body"]["source_identity"]),
        "D-128 gate source differs",
    )
    _require(
        canonical_json(body["receipt_commit_identity"])
        == canonical_json(preflight["semantic_body"]["receipt_commit_identity"]),
        "D-128 gate receipt commit differs",
    )
    _require(
        _parse_time(preflight["semantic_body"]["recorded_at"], label="preflight terminal")
        <= _parse_time(body["recorded_at"], label="gate recorded_at"),
        "D-128 gate chronology differs",
    )
    expected = _gate_body(
        receipt_binding=body["receipt_binding"],
        source=body["source_identity"],
        receipt_commit=body["receipt_commit_identity"],
        docker_binding=body["docker_binding"],
        pricing_binding=body["pricing_binding"],
        preflight_binding=body["preflight_binding"],
        docker_observation=docker["semantic_body"]["observation"],
        pricing_evidence=pricing["semantic_body"]["official_pricing_evidence"],
        preflight_body=preflight["semantic_body"],
        recorded_at=body["recorded_at"],
    )
    _require(canonical_json(body) == canonical_json(expected), "D-128 gate body differs")
    return payload


def _write_gate(root: Path) -> dict[str, Any]:
    receipt = _load_receipt(root)
    docker = _validate_docker_artifact(root)
    pricing = _validate_pricing_artifact(root)
    preflight = _validate_preflight_artifact(root)
    body = _gate_body(
        receipt_binding=_artifact_binding(root, RECEIPT_PATH),
        source=receipt["semantic_body"]["source_identity"],
        receipt_commit=preflight["semantic_body"]["receipt_commit_identity"],
        docker_binding=_artifact_binding(root, DOCKER_PATH),
        pricing_binding=_artifact_binding(root, PRICING_PATH),
        preflight_binding=_artifact_binding(root, PREFLIGHT_PATH),
        docker_observation=docker["semantic_body"]["observation"],
        pricing_evidence=pricing["semantic_body"]["official_pricing_evidence"],
        preflight_body=preflight["semantic_body"],
        recorded_at=_now(),
    )
    _write_artifact(root, GATE_PATH, schema=GATE_SCHEMA, prefix="d128_", body=body)
    return _validate_gate_artifact(root)


def _validated_existing_outputs(root: Path) -> tuple[Path, ...]:
    allowed: list[Path] = []
    validators = {
        "docker-image-readiness-remediation": _validate_docker_artifact,
        "official-pricing-capture": _validate_pricing_artifact,
        "read-only-no-call-preflight": _validate_preflight_artifact,
    }
    prior_complete = True
    for phase, (attempt_path, terminal_path) in _PHASE_PATHS.items():
        terminal_payload: dict[str, Any] | None = None
        attempt_exists = (root / attempt_path).exists()
        terminal_exists = (root / terminal_path).exists()
        _require(
            not (attempt_exists or terminal_exists) or prior_complete,
            f"D-128 {phase} exists before its predecessor phase completed",
        )
        _require(
            not terminal_exists or attempt_exists,
            f"D-128 {phase} terminal exists without attempt intent",
        )
        if attempt_exists:
            _validate_attempt_artifact(root, phase)
            allowed.append(attempt_path)
            _require(
                terminal_exists,
                f"D-128 orphaned {phase} attempt cannot be retried without separate approval",
            )
            terminal_payload = validators[phase](root)
            allowed.append(terminal_path)
        prior_complete = attempt_exists and terminal_exists
        if phase == "docker-image-readiness-remediation" and terminal_payload is not None:
            prior_complete = (
                prior_complete
                and terminal_payload["semantic_body"]["observation"]["passed"] is True
            )
    if (root / GATE_PATH).exists():
        _require(prior_complete, "D-128 gate exists before preflight completion")
        _validate_gate_artifact(root)
        allowed.append(GATE_PATH)
    return tuple(allowed)


def _require_runtime_identity(
    root: Path,
    *,
    source: dict[str, Any],
    receipt_commit: dict[str, Any],
    module_bindings: list[dict[str, Any]],
    allowed_outputs: tuple[Path, ...],
) -> None:
    receipt = _load_receipt(root)
    _require(
        canonical_json(receipt["semantic_body"]["source_identity"]) == canonical_json(source),
        "D-128 receipt source changed",
    )
    current_receipt_commit = _current_receipt_commit_identity(
        root, source=source, allowed_outputs=allowed_outputs
    )
    _require(
        canonical_json(current_receipt_commit) == canonical_json(receipt_commit),
        "D-128 receipt commit identity drifted",
    )
    current_modules = _loaded_module_bindings(root, source_commit=source["commit"])
    _require(
        canonical_json(current_modules) == canonical_json(module_bindings),
        "D-128 loaded modules changed",
    )


def _blocked_docker_result(root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    body = payload["semantic_body"]
    observation = body["observation"]
    raw = _stable_read(root, DOCKER_PATH)
    return {
        "status": body["status"],
        "phase": "docker-image-readiness-remediation",
        "artifact_id": payload["artifact_id"],
        "semantic_body_hash": payload["semantic_body_hash"],
        "file_bytes": len(raw),
        "file_sha256": sha256_bytes(raw),
        "source_commit": body["source_identity"]["commit"],
        "receipt_commit": body["receipt_commit_identity"]["commit"],
        "observed_blockers": observation["observed_blockers"],
        "official_public_get_request_count": 0,
        "pricing_attempt_created": False,
        "read_only_preflight_attempt_created": False,
        "gate_created": False,
        "docker_cli_command_count": observation["docker_cli_command_count"],
        "docker_image_store_mutation_count": observation["image_store_mutation_count"],
        "docker_desktop_or_daemon_start_count": 0,
        "provider_evaluator_agent_calls_made": 0,
        "container_create_start_run_exec_count": 0,
        "execution_hash_created": False,
        "execution_candidate_created": False,
        "cost_reserved_or_spent_usd": "0",
    }


def run_d128_external_no_call_preflight(*, repository: str | Path | None = None) -> dict[str, Any]:
    """Run only the exactly approved D-128 Docker/pricing/no-call phases."""

    root = _repo_root(repository)
    _load_receipt(root)
    _require_external_helper_contracts()
    existing = _validated_existing_outputs(root)
    if GATE_PATH in existing:
        return validate_d128_no_call_gate(repository=root, mode="current-source")
    if DOCKER_PATH in existing:
        docker = _validate_docker_artifact(root)
        if docker["semantic_body"]["observation"]["passed"] is False:
            return _blocked_docker_result(root, docker)

    static = _check_static_prerequisites(root, allowed_outputs=existing)
    source = static["source"]
    receipt_commit = static["receipt_commit"]
    modules = static["loaded_module_bindings"]

    if DOCKER_PATH not in existing:
        docker_attempt = _create_attempt_artifact(
            root,
            phase="docker-image-readiness-remediation",
            source=source,
            receipt_commit=receipt_commit,
            module_bindings=modules,
        )
        existing = (*existing, DOCKER_ATTEMPT_PATH)
        _require_runtime_identity(
            root,
            source=source,
            receipt_commit=receipt_commit,
            module_bindings=modules,
            allowed_outputs=existing,
        )
        _require_attempt_unchanged(
            root,
            phase="docker-image-readiness-remediation",
            expected=docker_attempt,
        )
        observation = docker_remediation.remediate_already_running_docker_environment()
        docker_remediation.validate_docker_no_start_remediation_observation(observation)
        _require_runtime_identity(
            root,
            source=source,
            receipt_commit=receipt_commit,
            module_bindings=modules,
            allowed_outputs=existing,
        )
        docker = _write_docker_terminal(
            root,
            source=source,
            receipt_commit=receipt_commit,
            observation=observation,
            expected_attempt=docker_attempt,
        )
        existing = (*existing, DOCKER_PATH)
        if observation["passed"] is False:
            return _blocked_docker_result(root, docker)

    if PRICING_PATH not in existing:
        _require_runtime_identity(
            root,
            source=source,
            receipt_commit=receipt_commit,
            module_bindings=modules,
            allowed_outputs=existing,
        )
        pricing_attempt = _create_attempt_artifact(
            root,
            phase="official-pricing-capture",
            source=source,
            receipt_commit=receipt_commit,
            module_bindings=modules,
        )
        existing = (*existing, PRICING_ATTEMPT_PATH)
        _require_runtime_identity(
            root,
            source=source,
            receipt_commit=receipt_commit,
            module_bindings=modules,
            allowed_outputs=existing,
        )
        _require_attempt_unchanged(root, phase="official-pricing-capture", expected=pricing_attempt)
        evidence = pricing_capture.capture_official_pricing_evidence()
        pricing_capture.validate_official_pricing_evidence(evidence)
        _require_runtime_identity(
            root,
            source=source,
            receipt_commit=receipt_commit,
            module_bindings=modules,
            allowed_outputs=existing,
        )
        _write_pricing_terminal(
            root,
            source=source,
            receipt_commit=receipt_commit,
            evidence=evidence,
            expected_attempt=pricing_attempt,
        )
        existing = (*existing, PRICING_PATH)

    if PREFLIGHT_PATH not in existing:
        _validate_pricing_artifact(root)
        _require_runtime_identity(
            root,
            source=source,
            receipt_commit=receipt_commit,
            module_bindings=modules,
            allowed_outputs=existing,
        )
        cli_before = docker_remediation.approved_cli_binding()
        preflight_attempt = _create_attempt_artifact(
            root,
            phase="read-only-no-call-preflight",
            source=source,
            receipt_commit=receipt_commit,
            module_bindings=modules,
        )
        existing = (*existing, PREFLIGHT_ATTEMPT_PATH)
        _require_runtime_identity(
            root,
            source=source,
            receipt_commit=receipt_commit,
            module_bindings=modules,
            allowed_outputs=existing,
        )
        _require_attempt_unchanged(
            root, phase="read-only-no-call-preflight", expected=preflight_attempt
        )
        snapshots = [
            docker_remediation.observe_docker_readiness(),
            docker_remediation.observe_docker_readiness(),
        ]
        for snapshot in snapshots:
            docker_remediation.validate_docker_readiness_snapshot(snapshot)
        _require_runtime_identity(
            root,
            source=source,
            receipt_commit=receipt_commit,
            module_bindings=modules,
            allowed_outputs=existing,
        )
        cli_after = docker_remediation.approved_cli_binding()
        try:
            factory = d127._model_factory_contract(root)
        except ContractError as exc:
            raise D128PreflightError("D-128 production model factory changed") from exc
        sdk = _sdk_observation(root, source, factory)
        try:
            d127._validate_sdk_observation(root, sdk, source=source)
        except ContractError as exc:
            raise D128PreflightError("D-128 final SDK observation differs") from exc
        _require_runtime_identity(
            root,
            source=source,
            receipt_commit=receipt_commit,
            module_bindings=modules,
            allowed_outputs=existing,
        )
        _write_preflight_terminal(
            root,
            source=source,
            receipt_commit=receipt_commit,
            cli_before=cli_before,
            cli_after=cli_after,
            snapshots=snapshots,
            sdk=sdk,
            expected_attempt=preflight_attempt,
        )
        existing = (*existing, PREFLIGHT_PATH)

    _require_runtime_identity(
        root,
        source=source,
        receipt_commit=receipt_commit,
        module_bindings=modules,
        allowed_outputs=existing,
    )
    gate = _write_gate(root)
    existing = (*existing, GATE_PATH)
    _require_runtime_identity(
        root,
        source=source,
        receipt_commit=receipt_commit,
        module_bindings=modules,
        allowed_outputs=existing,
    )
    return _validation_result(root, gate, post_commit=None)


def _validate_stored_receipt_commit_for_post_commit(
    root: Path, gate: dict[str, Any]
) -> dict[str, Any]:
    body = gate["semantic_body"]
    value = body["receipt_commit_identity"]
    _validate_receipt_commit_identity(root, value, source=body["source_identity"])
    return value


def _post_evidence_commit_state(root: Path, gate: dict[str, Any]) -> dict[str, Any]:
    receipt_commit = _validate_stored_receipt_commit_for_post_commit(root, gate)
    head = d127._run_git(root, "rev-parse", "HEAD")
    ancestry = d127._run_git(root, "rev-list", "--parents", "-n", "1", "HEAD").split()
    _require(
        ancestry == [head, receipt_commit["commit"]],
        "D-128 evidence commit must have the receipt commit as its only parent",
    )
    _require(
        not d127._run_git(root, "status", "--porcelain", "--untracked-files=all"),
        "D-128 post-evidence-commit worktree is not clean",
    )
    rows = [
        line.split("\t")
        for line in d127._run_git(
            root,
            "diff",
            "--name-status",
            "--no-renames",
            f"{receipt_commit['commit']}..{head}",
        ).splitlines()
        if line
    ]
    _require(
        all(len(row) == 2 and row[0] in {"A", "M"} for row in rows),
        "D-128 evidence commit contains a non-add-or-modify change",
    )
    status_by_path = {row[1]: row[0] for row in rows}
    changed = set(status_by_path)
    allowed = {
        *(path.as_posix() for path in _EXTERNAL_OUTPUT_PATHS),
        *_EVIDENCE_DOC_PATHS,
    }
    _require(changed.issubset(allowed), "D-128 evidence commit changed source paths")
    required = {path.as_posix() for path in _EXTERNAL_OUTPUT_PATHS}
    _require(required.issubset(changed), "D-128 evidence commit is missing artifacts")
    _require(
        all(status_by_path[path] == "A" for path in required),
        "D-128 successor artifacts were not newly added",
    )
    return {
        "head": head,
        "receipt_commit": receipt_commit["commit"],
        "source_commit": gate["semantic_body"]["source_identity"]["commit"],
        "changed_paths": sorted(changed),
    }


def _validation_result(
    root: Path,
    gate: dict[str, Any],
    *,
    post_commit: dict[str, Any] | None,
) -> dict[str, Any]:
    raw = _stable_read(root, GATE_PATH)
    body = gate["semantic_body"]
    preflight = _validate_preflight_artifact(root)["semantic_body"]
    docker = _validate_docker_artifact(root)["semantic_body"]["observation"]
    pricing = _validate_pricing_artifact(root)["semantic_body"]["official_pricing_evidence"]
    return {
        "status": body["status"],
        "gate_id": gate["artifact_id"],
        "semantic_body_hash": gate["semantic_body_hash"],
        "file_bytes": len(raw),
        "file_sha256": sha256_bytes(raw),
        "source_commit": body["source_identity"]["commit"],
        "receipt_commit": body["receipt_commit_identity"]["commit"],
        "environment_ready_for_execution_hash": body["qualification"][
            "environment_ready_for_execution_hash"
        ],
        "observed_blockers": body["qualification"]["observed_blockers"],
        "official_public_get_request_count": pricing["public_get_request_count"],
        "docker_cli_command_count": docker["docker_cli_command_count"]
        + preflight["authority"]["read_only_snapshot_docker_cli_command_count"],
        "docker_image_store_mutation_count": docker["image_store_mutation_count"],
        "docker_desktop_or_daemon_start_count": 0,
        "provider_evaluator_agent_calls_made": 0,
        "container_create_start_run_exec_count": 0,
        "execution_hash_created": False,
        "execution_candidate_created": False,
        "cost_reserved_or_spent_usd": "0",
        "post_commit": post_commit,
    }


def validate_d128_no_call_gate(
    *,
    repository: str | Path | None = None,
    mode: str = "current-source",
) -> dict[str, Any]:
    """Replay D-128 evidence without Docker or network activity."""

    root = _repo_root(repository)
    gate = _validate_gate_artifact(root)
    post_commit = None
    if mode == "current-source":
        body = gate["semantic_body"]
        current = _current_receipt_commit_identity(
            root,
            source=body["source_identity"],
            allowed_outputs=_EXTERNAL_OUTPUT_PATHS,
        )
        _require(
            canonical_json(current) == canonical_json(body["receipt_commit_identity"]),
            "D-128 current receipt commit differs from gate",
        )
        if body["qualification"]["environment_ready_for_execution_hash"]:
            age = _pricing_age_microseconds(
                _validate_pricing_artifact(root)["semantic_body"]["official_pricing_evidence"][
                    "observed_at"
                ],
                _now(),
            )
            _require(
                0 <= age <= FRESHNESS_SECONDS * 1_000_000,
                "D-128 ready gate pricing is no longer fresh",
            )
            try:
                d127._require_current_sdk_matches_artifact(
                    root,
                    body["source_identity"],
                    _validate_preflight_artifact(root)["semantic_body"][
                        "sdk_credential_factory_observation"
                    ],
                )
            except ContractError as exc:
                raise D128PreflightError("D-128 current SDK differs") from exc
            _require(
                docker_remediation.approved_cli_binding()
                == _validate_preflight_artifact(root)["semantic_body"][
                    "approved_docker_cli_bindings"
                ]["after"],
                "D-128 current Docker CLI differs",
            )
    elif mode == "post-evidence-commit":
        post_commit = _post_evidence_commit_state(root, gate)
    else:
        raise D128PreflightError("D-128 validation mode differs")
    return _validation_result(root, gate, post_commit=post_commit)


__all__ = [
    "D128PreflightError",
    "GATE_PATH",
    "PREFLIGHT_PATH",
    "PRICING_PATH",
    "RECEIPT_PATH",
    "DOCKER_PATH",
    "STATIC_READY_STATUS",
    "check_d128_static_prerequisites",
    "create_d128_approval_receipt",
    "run_d128_external_no_call_preflight",
    "validate_d128_no_call_gate",
]
