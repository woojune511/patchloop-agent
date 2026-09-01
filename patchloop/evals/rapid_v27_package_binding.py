"""Bind the immutable V27 review after explicitly marked R24 admission-only integration.

Restore predecessor source bytes in memory, never rewrite or rebuild a consumed
qualification/candidate. New integration behavior is tested separately.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from patchloop.errors import RecoveryError
from patchloop.util import ensure_within, sha256_bytes, sha256_json

REVIEW_PATH = "experiments/lean-harness-provider-schema-activation-review-20260901-v2.json"
REVIEW_HASH = "sha256:f10914748b0d91f7c060d3063e3115df6e96705e8996683f99f0dc2738f47340"
QUALIFICATION_PATH = (
    "experiments/lean-harness-provider-schema-public-qualification-20260831-v1.json"
)
QUALIFICATION_HASH = "sha256:cb80ed051f37fa50a601462510fdc866b3bf40d18c0df6fb027bdb75e286bcc2"
R23_CANDIDATE_PATH = (
    "reports/rapid-development/artifacts/"
    "rapid-public-dev-anyio-v5-batch-image-ab-20260831-r23-candidate-v32.json"
)
RUNTIME_IDENTITY = {
    "runtime_policy_version": "lean-harness-v27",
    "tool_schema_version": "v28",
    "context_policy_version": "phase-evidence-v37",
    "request_evidence_schema": "lean-harness-request-evidence-v27",
}
INTEGRATED_FILES = {
    "patchloop/agent/runner.py",
    "patchloop/contracts.py",
    "patchloop/evals/live_verifier_registry.py",
}
_REGION = re.compile(
    rb"^[ \t]*# R24 integration begin: ([a-z-]+)\r?\n"
    rb".*?^[ \t]*# R24 integration end: \1\r?\n",
    re.MULTILINE | re.DOTALL,
)


def restore_reviewed_source(raw: bytes) -> bytes:
    return _REGION.sub(b"", raw)


def _raw(root: Path, relative: str) -> bytes:
    path = ensure_within(root, relative)
    if (root / relative).is_symlink() or not path.is_file():
        raise RecoveryError(f"R24 binding input is unavailable: {relative}")
    return path.read_bytes()


def _document(root: Path, relative: str, expected_hash: str) -> dict[str, Any]:
    raw = _raw(root, relative)
    if sha256_bytes(raw) != expected_hash:
        raise RecoveryError(f"R24 immutable input changed: {relative}")
    value = json.loads(raw)
    if value.get("content_hash") != sha256_json(
        {key: item for key, item in value.items() if key != "content_hash"}
    ):
        raise RecoveryError("R24 immutable content hash differs")
    return value


def validate_v27_integration_binding(repository: str | Path) -> dict[str, Any]:
    root = Path(repository).resolve()
    review = _document(root, REVIEW_PATH, REVIEW_HASH)
    qualification = _document(root, QUALIFICATION_PATH, QUALIFICATION_HASH)
    if (
        review["decision"]["adoption_status"] != "eligible-not-adopted"
        or review["runtime_identity"] != RUNTIME_IDENTITY
        or qualification["runtime_identity"] != RUNTIME_IDENTITY
        or review["qualification"]["content_hash"] != qualification["content_hash"]
    ):
        raise RecoveryError("R24 reviewed package differs")
    sources = {
        row["path"]: row for row in qualification["source_files"] + review["review_source_files"]
    }
    for row in qualification["predecessor_preservation"]["source_proof"]:
        sources.setdefault(
            row["path"],
            {
                "path": row["path"],
                "file_sha256": row["current_file_sha256"],
            },
        )
    proven = []
    for relative, descriptor in sorted(sources.items()):
        current = _raw(root, relative)
        restored = restore_reviewed_source(current) if relative in INTEGRATED_FILES else current
        if sha256_bytes(restored) != descriptor["file_sha256"]:
            raise RecoveryError(f"R24 change exceeds its marked integration: {relative}")
        proven.append(
            {
                "path": relative,
                "reviewed_file_sha256": descriptor["file_sha256"],
                "current_file_sha256": sha256_bytes(current),
                "reviewed_bytes_recovered": True,
                "marked_integration": current != restored,
            }
        )
    immutable = qualification["predecessor_preservation"]["immutable_artifacts"]
    immutable = [*immutable, qualification["predecessor_preservation"]["r23_audit"]]
    for row in immutable:
        raw = _raw(root, row["path"])
        if len(raw) != row["bytes"] or sha256_bytes(raw) != row["file_sha256"]:
            raise RecoveryError(f"R24 predecessor artifact differs: {row['path']}")
    prior = next((row for row in immutable if row["path"] == R23_CANDIDATE_PATH), None)
    if prior is None:
        raise RecoveryError("R24 binding lacks its consumed R23 candidate identity")
    candidate = _document(root, R23_CANDIDATE_PATH, prior["file_sha256"])
    body = {
        "schema_version": "rapid-v27-request-integration-binding-v1",
        "runtime_identity": RUNTIME_IDENTITY,
        "qualification": review["qualification"],
        "activation_review": {
            "path": REVIEW_PATH,
            "file_sha256": REVIEW_HASH,
            "bytes": len(_raw(root, REVIEW_PATH)),
            "content_hash": review["content_hash"],
        },
        "reviewed_source_proof": proven,
        "immutable_inputs": immutable,
        "frozen_control": candidate["selection_evidence"]["control_lean_v25"],
        "historical_artifacts_modified": False,
        "historical_builders_invoked": False,
        "runner_continuity_check_included": False,
        "agent_semantic_policy_changed_by_integration": False,
        "rehearsal_is_not_provider_acceptance": True,
    }
    return {**body, "content_hash": sha256_json(body)}
