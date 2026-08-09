"""Build the offline D-129 successor contract for the blocked D-128 terminal.

D-129 records the user's out-of-band Docker readiness statement without
turning it into agent-observed readiness or execution authority.  The module
validates the exact append-only D-128 source/receipt/attempt/terminal chain and
the clean committed D-129 source, then materializes one offline source gate.
It has no approval-receipt writer and no Docker, network, SDK, provider,
evaluator, agent, retrieval, execution-hash, candidate, cost, or experiment
entrypoint.  Its only subprocess boundary is a fixed, read-only local Git
provenance observer.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import stat
import subprocess
import uuid
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from patchloop.errors import ContractError
from patchloop.runtime import repository_root
from patchloop.util import canonical_json, sha256_bytes, sha256_text

MILESTONE = "D-129"
SCHEMA_VERSION = "d128-terminal-successor-offline-source-gate-d129-v1"
STATUS = "D129_D128_TERMINAL_SUCCESSOR_OFFLINE_SOURCE_QUALIFIED_APPROVAL_REQUIRED"
OUTPUT_PATH = Path(
    "reports/live-pilot/artifacts/d129-d128-terminal-successor-offline-source-gate.json"
)

D128_SOURCE_COMMIT = "23038c16467a32c5b862f84e09797a298101f4e4"
D128_SOURCE_TREE = "46862cc0d48035e866d8d5086926391b56f90ba2"
D128_SOURCE_PARENT = "aeac01a04447c731ee5eac4c56e599eb74532a60"
D128_RECEIPT_COMMIT = "4b2ef5a15e9c721c1c8fa1e73375a3bf061bda50"
D128_RECEIPT_TREE = "2d01c39b264cff0abf18ec1a11a05c49b2507895"
D128_EVIDENCE_COMMIT = "4633f867ebd8b1ad8f6c6cd0dc357250fbe58d81"
D128_EVIDENCE_TREE = "4a94b34cf286db323804ef5ec116cde656eb9e95"

D128_OFFLINE_PATH = Path(
    "reports/live-pilot/artifacts/d128-d127-terminal-successor-offline-source-gate.json"
)
D128_OFFLINE_SCHEMA = "d127-terminal-successor-offline-source-gate-d128-v1"
D128_OFFLINE_ID = "d128_9edb9d1396b2f572c3b1ade623c7c5f6fb3fdf083d17a71680e7f1041bfba7de"
D128_OFFLINE_BODY_SHA256 = "sha256:9edb9d1396b2f572c3b1ade623c7c5f6fb3fdf083d17a71680e7f1041bfba7de"
D128_OFFLINE_FILE_SHA256 = "sha256:2528aa018908958bdd35b4b6202c75be2b4ca72521d64bfed800284a015a739c"
D128_OFFLINE_FILE_BYTES = 12_557
D128_OFFLINE_BLOB_OID = "c871908f61bcdf0e012f193479e8644246e0e0bd"
D128_OFFLINE_STATUS = "D128_D127_TERMINAL_SUCCESSOR_OFFLINE_SOURCE_QUALIFIED_APPROVAL_REQUIRED"

D128_RECEIPT_PATH = Path(
    "reports/live-pilot/artifacts/"
    "d128-d127-terminal-successor-external-no-call-preflight-approval-receipt.json"
)
D128_RECEIPT_SCHEMA = "d127-terminal-successor-external-no-call-approval-receipt-d128-v1"
D128_RECEIPT_ID = "d128approval_11c8d00ba507ead135d82db96de9e0d2ff66600b06801261daad6bf5c25abacd"
D128_RECEIPT_BODY_SHA256 = "sha256:11c8d00ba507ead135d82db96de9e0d2ff66600b06801261daad6bf5c25abacd"
D128_RECEIPT_FILE_SHA256 = "sha256:b5cb1e1d65e1a1d3ebf726ba85031ccb66dfb7cf950fab1dde68cbeebaf72050"
D128_RECEIPT_FILE_BYTES = 7_713
D128_RECEIPT_BLOB_OID = "67bd41987d15107d3a2eeda9b34f3ecdadb494b5"
D128_RECEIPT_STATUS = "D128_D127_TERMINAL_SUCCESSOR_EXTERNAL_NO_CALL_APPROVAL_RECORDED"

D128_ATTEMPT_PATH = Path(
    "reports/live-pilot/artifacts/d128-docker-image-readiness-remediation-attempt-intent.json"
)
D128_ATTEMPT_SCHEMA = "d127-terminal-successor-external-phase-attempt-intent-d128-v1"
D128_ATTEMPT_ID = (
    "d128dockerimagereadinessremediationattempt_"
    "25c78d210117696eb1f2f8b7f73069c022b9bb00b332bc83350eb5dab388cc21"
)
D128_ATTEMPT_BODY_SHA256 = "sha256:25c78d210117696eb1f2f8b7f73069c022b9bb00b332bc83350eb5dab388cc21"
D128_ATTEMPT_FILE_SHA256 = "sha256:04c5d2a32bc908d2dfc4b754779ec75a43aee19ff28c68c1bc7843c4d38c71c5"
D128_ATTEMPT_FILE_BYTES = 5_583
D128_ATTEMPT_BLOB_OID = "12175d420a8b44f63040d09e94f6d91a886b10f2"
D128_ATTEMPT_STATUS = "D128_DOCKER_IMAGE_READINESS_REMEDIATION_ATTEMPT_INTENT_RECORDED"

D128_TERMINAL_PATH = Path(
    "reports/live-pilot/artifacts/d128-exact-docker-image-readiness-remediation-observation.json"
)
D128_TERMINAL_SCHEMA = "d127-terminal-successor-docker-image-remediation-d128-v1"
D128_TERMINAL_ID = (
    "d128dockerremediation_2682a64e07d869c9989f02028d994f7e16a50327f07b0692917475cdac0ad78f"
)
D128_TERMINAL_BODY_SHA256 = (
    "sha256:2682a64e07d869c9989f02028d994f7e16a50327f07b0692917475cdac0ad78f"
)
D128_TERMINAL_FILE_SHA256 = (
    "sha256:77dbd861466e5ce4913a0a7f0c4d1240b83a0a5be5169571c104c0e42a95e939"
)
D128_TERMINAL_FILE_BYTES = 9_270
D128_TERMINAL_BLOB_OID = "5868bc24808b5fc205714c2b7d77c8fc8c0c687b"
D128_TERMINAL_STATUS = "D128_EXACT_DOCKER_IMAGE_READINESS_REMEDIATION_OBSERVED_BLOCKED"
D128_TERMINAL_BLOCKER = "already-running-docker-desktop-linux-daemon-unavailable"

D128_DESCENDANT_PATHS = (
    Path("reports/live-pilot/artifacts/d128-official-pricing-capture-attempt-intent.json"),
    Path("reports/live-pilot/artifacts/d128-replayable-official-pricing-evidence.json"),
    Path("reports/live-pilot/artifacts/d128-read-only-preflight-attempt-intent.json"),
    Path("reports/live-pilot/artifacts/d128-repeated-no-call-readiness-preflight.json"),
    Path(
        "reports/live-pilot/artifacts/d128-terminal-successor-external-no-call-preflight-gate.json"
    ),
)

IMPLEMENTATION_PATHS = (
    Path("patchloop/evals/d129_d128_terminal_successor_offline.py"),
    Path("scripts/build_d129_d128_terminal_successor_offline.py"),
    Path("tests/test_d129_d128_terminal_successor_offline.py"),
)
ACTIVE_DOC_PATHS = (
    Path("AGENTS.md"),
    Path("README.md"),
    Path("docs/current-status.md"),
    Path("docs/03-contracts.md"),
    Path("docs/04-evaluation-protocol.md"),
    Path("docs/05-implementation-plan.md"),
    Path("docs/06-decisions.md"),
    Path("docs/07-reproduction.md"),
    Path("docs/08-limitations.md"),
    Path("docs/09-evidence.md"),
)

ROOT_KEYS = ("schema_version", "gate_id", "semantic_body_hash", "semantic_body")
BODY_KEYS = (
    "milestone",
    "evidence_kind",
    "recorded_at",
    "status",
    "predecessor_chain",
    "manual_readiness_attestation",
    "source_identity",
    "successor_contract",
    "approval_template_contract",
    "implementation_integrity",
    "offline_qualification",
    "blocked_prerequisites",
    "evidence_boundary",
    "authority",
    "next_gate",
)

FUTURE_APPROVED_SCOPE = (
    "record-a-new-exact-d129-successor-user-approval-receipt",
    "use-the-exact-approved-docker-cli-identity",
    "reobserve-the-already-running-docker-desktop-linux-daemon-read-only",
    "pull-only-moto-and-babel-exact-digest-images-when-confirmed-absent",
    "capture-bounded-replayable-openai-official-pricing-evidence",
    "run-sdk-credential-presence-official-endpoint-no-call-preflight",
    "create-append-only-d129-attempt-terminal-preflight-and-gate-evidence",
    "modify-related-source-tests-docs-and-create-local-git-commit",
)
FUTURE_NOT_AUTHORIZED = (
    "agent-start-docker-desktop-or-daemon",
    "container-create-start-run-or-exec",
    "pull-or-load-any-image-other-than-the-two-exact-approved-digests",
    "provider-evaluator-or-agent-execution",
    "runtime-memory-injection-or-retrieval",
    "execution-hash-or-execution-candidate-creation",
    "cost-reservation-or-spend",
    "four-row-ac-execution",
)
BLOCKED_PREREQUISITES = (
    "new-exact-d129-successor-user-approval-not-recorded",
    "manual-readiness-is-self-attested-and-must-be-reobserved-after-that-receipt",
    "future-receipt-bound-clean-committed-source-identity-not-yet-recorded",
    "d129-external-attempt-pricing-preflight-and-gate-not-created",
    "exact-runner-execution-hash-and-candidate-remain-separately-gated",
)

FOCUSED_TESTS_PASSED = 12
SELECTED_REGRESSION_TESTS_PASSED = 115
MAX_READ_BYTES = 4 * 1024 * 1024
MAX_GIT_OUTPUT_BYTES = 4 * 1024 * 1024


class D129OfflineGateError(ContractError):
    """Raised when the offline D-129 successor contract drifts."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise D129OfflineGateError(message)


def _repo_root(repository: str | Path | None) -> Path:
    selected = Path(repository) if repository is not None else repository_root()
    try:
        root = selected.resolve(strict=True)
    except OSError as exc:
        raise D129OfflineGateError("D-129 repository root is unavailable") from exc
    _require(root.is_dir(), "D-129 repository root is not a directory")
    return root


def _is_linklike(path: Path) -> bool:
    try:
        info = path.lstat()
    except OSError:
        return False
    attributes = int(getattr(info, "st_file_attributes", 0))
    reparse = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    return stat.S_ISLNK(info.st_mode) or bool(attributes & reparse)


def _lexists(path: Path) -> bool:
    return os.path.lexists(path)


def _logical_path(root: Path, relative: Path, *, must_exist: bool) -> Path:
    _require(not relative.is_absolute(), "D-129 path must be repository-relative")
    _require(
        relative.parts
        and all(part not in ("", ".", "..") and ":" not in part for part in relative.parts),
        "D-129 path is noncanonical",
    )
    current = root
    for part in relative.parts[:-1]:
        current = current / part
        _require(current.exists(), "D-129 path parent is unavailable")
        _require(current.is_dir() and not _is_linklike(current), "D-129 path parent is unsafe")
    selected = root / relative
    try:
        parent = selected.parent.resolve(strict=True)
    except OSError as exc:
        raise D129OfflineGateError("D-129 path parent is unavailable") from exc
    _require(parent == root or root in parent.parents, "D-129 path escapes repository")
    exists = _lexists(selected)
    _require(not must_exist or exists, "D-129 required path is absent")
    if exists:
        _require(not _is_linklike(selected), "D-129 path is linklike")
    return selected


def _stable_read(root: Path, relative: Path, *, maximum: int = MAX_READ_BYTES) -> bytes:
    selected = _logical_path(root, relative, must_exist=True)
    try:
        before = selected.lstat()
        _require(stat.S_ISREG(before.st_mode), "D-129 path is not a regular file")
        _require(0 <= before.st_size <= maximum, "D-129 file exceeds bound")
        with selected.open("rb") as handle:
            opened = os.fstat(handle.fileno())
            _require(
                (opened.st_dev, opened.st_ino, opened.st_size)
                == (before.st_dev, before.st_ino, before.st_size),
                "D-129 file identity changed before read",
            )
            raw = handle.read(maximum + 1)
        after = selected.lstat()
    except OSError as exc:
        raise D129OfflineGateError(f"D-129 cannot stably read {relative.as_posix()}") from exc
    _require(len(raw) <= maximum, "D-129 file exceeds bound")
    _require(
        (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
        == (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns),
        "D-129 file changed during read",
    )
    return raw


def _pretty_bytes(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, ensure_ascii=True, indent=2) + "\n").encode("utf-8")


def _parse_time(value: Any, *, label: str) -> datetime:
    _require(isinstance(value, str) and value.endswith("Z"), f"D-129 {label} differs")
    try:
        parsed = datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except ValueError as exc:
        raise D129OfflineGateError(f"D-129 {label} differs") from exc
    _require(parsed.tzinfo is not None, f"D-129 {label} differs")
    return parsed.astimezone(UTC)


def _file_binding(raw: bytes) -> dict[str, Any]:
    return {"file_bytes": len(raw), "file_sha256": sha256_bytes(raw)}


def _bounded_external_file_binding(path: Path) -> dict[str, Any]:
    _require(path.is_absolute(), "D-129 external executable path is not absolute")
    _require(path.is_file() and not _is_linklike(path), "D-129 Git engine is unsafe")
    before = path.lstat()
    _require(before.st_size <= 8 * 1024 * 1024, "D-129 Git engine exceeds bound")
    with path.open("rb") as handle:
        opened = os.fstat(handle.fileno())
        _require(
            (opened.st_dev, opened.st_ino, opened.st_size)
            == (before.st_dev, before.st_ino, before.st_size),
            "D-129 Git engine identity changed",
        )
        raw = handle.read(8 * 1024 * 1024 + 1)
    after = path.lstat()
    _require(
        len(raw) <= 8 * 1024 * 1024
        and (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
        == (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns),
        "D-129 Git engine changed during read",
    )
    return {
        "resolved_path": str(path),
        "file_name": path.name,
        **_file_binding(raw),
        "linklike": False,
    }


def _git_environment() -> dict[str, str]:
    routed = sorted(
        name
        for name, value in os.environ.items()
        if name.upper().startswith("GIT_") and bool(value)
    )
    _require(not routed, "D-129 Git routing environment is present")
    environment = {
        name: value
        for name in ("SYSTEMROOT", "WINDIR", "TEMP", "TMP")
        if (value := os.environ.get(name))
    }
    environment.update(
        {
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": "NUL",
            "GIT_CONFIG_SYSTEM": "NUL",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_NO_LAZY_FETCH": "1",
            "GIT_TERMINAL_PROMPT": "0",
        }
    )
    return environment


def _git_executable() -> Path:
    selected = shutil.which("git")
    _require(bool(selected), "D-129 Git executable is unavailable")
    launcher = Path(str(selected))
    _require(launcher.is_absolute(), "D-129 Git executable path is not absolute")
    _require(launcher.is_file() and not _is_linklike(launcher), "D-129 Git launcher is unsafe")
    launcher = launcher.resolve(strict=True)
    if launcher.parent.name.casefold() == "cmd":
        engine = launcher.parent.parent / "mingw64/bin/git.exe"
    else:
        engine = launcher
    _require(engine.is_file() and not _is_linklike(engine), "D-129 Git engine is unavailable")
    return engine.resolve(strict=True)


def _git_command(root: Path, *args: str, binary: bool = False) -> bytes | str:
    executable = _git_executable()
    before = _bounded_external_file_binding(executable)
    try:
        result = subprocess.run(
            [
                str(executable),
                "-c",
                "core.fsmonitor=false",
                "-c",
                "commit.gpgSign=false",
                *args,
            ],
            cwd=root,
            capture_output=True,
            text=False,
            check=False,
            shell=False,
            env=_git_environment(),
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise D129OfflineGateError("D-129 bounded local Git observation failed") from exc
    after = _bounded_external_file_binding(executable)
    _require(before == after, "D-129 Git engine changed during command")
    _require(
        len(result.stdout) <= MAX_GIT_OUTPUT_BYTES and len(result.stderr) <= MAX_GIT_OUTPUT_BYTES,
        "D-129 Git output exceeds bound",
    )
    _require(result.returncode == 0, f"D-129 git command failed: {' '.join(args)}")
    if binary:
        return result.stdout
    try:
        return result.stdout.decode("utf-8").strip()
    except UnicodeDecodeError as exc:
        raise D129OfflineGateError("D-129 Git output is not UTF-8") from exc


def _git_cli_observation(root: Path) -> dict[str, Any]:
    executable = _git_executable()
    binding = _bounded_external_file_binding(executable)
    version = _git_command(root, "--version")
    _require(isinstance(version, str), "D-129 Git version differs")
    _require(
        re.fullmatch(r"git version [0-9]+\.[0-9]+\.[0-9]+(?:\.[^\s]+)?", version) is not None,
        "D-129 Git version differs",
    )
    normalization = _git_command(root, "config", "--local", "--get", "core.autocrlf")
    _require(normalization == "false", "D-129 checkout must bind core.autocrlf=false")
    return {
        **binding,
        "version": version,
        "actual_git_engine_invoked_directly": True,
        "repository_local_core_autocrlf": "false",
        "authenticated_or_vendor_signed_identity_claimed": False,
        "stable_during_observation": True,
        "minimal_secret_free_environment": True,
        "fsmonitor_disabled": True,
        "shell_used": False,
    }


def _commit_identity(root: Path, commit: str) -> dict[str, Any]:
    tree = _git_command(root, "rev-parse", f"{commit}^{{tree}}")
    ancestry = _git_command(root, "rev-list", "--parents", "-n", "1", commit)
    _require(isinstance(tree, str) and isinstance(ancestry, str), "D-129 commit differs")
    values = ancestry.split()
    _require(values and values[0] == commit, "D-129 commit ancestry differs")
    return {"commit": commit, "tree": tree, "parents": values[1:]}


def _diff_rows(root: Path, commit: str) -> list[dict[str, str]]:
    value = _git_command(
        root,
        "diff-tree",
        "--no-renames",
        "--no-ext-diff",
        "--no-commit-id",
        "--name-status",
        "-r",
        commit,
    )
    _require(isinstance(value, str), "D-129 commit diff differs")
    rows: list[dict[str, str]] = []
    for line in value.splitlines() if value else []:
        parts = line.split("\t")
        _require(len(parts) == 2, "D-129 commit diff row differs")
        rows.append({"status": parts[0], "path": parts[1].replace("\\", "/")})
    return rows


def _commit_blob(root: Path, commit: str, relative: Path) -> tuple[str, bytes]:
    listing = _git_command(root, "ls-tree", commit, "--", relative.as_posix())
    _require(isinstance(listing, str), "D-129 committed blob differs")
    match = re.fullmatch(r"100644 blob ([0-9a-f]{40})\t(.+)", listing)
    _require(match is not None, "D-129 committed blob differs")
    _require(match.group(2) == relative.as_posix(), "D-129 committed blob path differs")
    raw = _git_command(root, "cat-file", "blob", f"{commit}:{relative.as_posix()}", binary=True)
    _require(isinstance(raw, bytes), "D-129 committed blob differs")
    return match.group(1), raw


def _status_lines(root: Path) -> list[str]:
    value = _git_command(root, "status", "--porcelain", "--untracked-files=all")
    _require(isinstance(value, str), "D-129 Git status differs")
    return [line for line in value.splitlines() if line]


def _validate_historical_topology(root: Path) -> dict[str, Any]:
    source = _commit_identity(root, D128_SOURCE_COMMIT)
    receipt = _commit_identity(root, D128_RECEIPT_COMMIT)
    evidence = _commit_identity(root, D128_EVIDENCE_COMMIT)
    _require(
        source
        == {
            "commit": D128_SOURCE_COMMIT,
            "tree": D128_SOURCE_TREE,
            "parents": [D128_SOURCE_PARENT],
        },
        "D-129 D-128 source commit differs",
    )
    _require(
        receipt
        == {
            "commit": D128_RECEIPT_COMMIT,
            "tree": D128_RECEIPT_TREE,
            "parents": [D128_SOURCE_COMMIT],
        },
        "D-129 D-128 receipt commit differs",
    )
    _require(
        evidence
        == {
            "commit": D128_EVIDENCE_COMMIT,
            "tree": D128_EVIDENCE_TREE,
            "parents": [D128_RECEIPT_COMMIT],
        },
        "D-129 D-128 evidence commit differs",
    )
    _require(
        _diff_rows(root, D128_RECEIPT_COMMIT)
        == [{"status": "A", "path": D128_RECEIPT_PATH.as_posix()}],
        "D-129 D-128 receipt commit scope differs",
    )
    evidence_diff = _diff_rows(root, D128_EVIDENCE_COMMIT)
    expected_evidence = [
        *({"status": "M", "path": path.as_posix()} for path in ACTIVE_DOC_PATHS),
        {"status": "A", "path": D128_ATTEMPT_PATH.as_posix()},
        {"status": "A", "path": D128_TERMINAL_PATH.as_posix()},
    ]
    _require(
        sorted(evidence_diff, key=lambda row: row["path"])
        == sorted(expected_evidence, key=lambda row: row["path"]),
        "D-129 D-128 evidence commit scope differs",
    )
    return {"source": source, "receipt": receipt, "evidence": evidence}


def _parse_artifact(
    root: Path,
    *,
    path: Path,
    schema: str,
    artifact_id: str,
    id_key: str,
    body_sha256: str,
    file_sha256: str,
    file_bytes: int,
    status: str,
    blob_oid: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    raw = _stable_read(root, path)
    _require(len(raw) == file_bytes, f"D-129 {path.name} bytes differ")
    _require(sha256_bytes(raw) == file_sha256, f"D-129 {path.name} file SHA differs")
    committed_oid, committed = _commit_blob(root, D128_EVIDENCE_COMMIT, path)
    _require(committed_oid == blob_oid and committed == raw, f"D-129 {path.name} blob differs")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise D129OfflineGateError(f"D-129 {path.name} is not canonical JSON") from exc
    _require(isinstance(payload, dict), f"D-129 {path.name} root differs")
    _require(payload.get("schema_version") == schema, f"D-129 {path.name} schema differs")
    _require(payload.get(id_key) == artifact_id, f"D-129 {path.name} ID differs")
    _require(
        payload.get("semantic_body_hash") == body_sha256,
        f"D-129 {path.name} body SHA differs",
    )
    body = payload.get("semantic_body")
    _require(isinstance(body, dict), f"D-129 {path.name} body differs")
    _require(sha256_text(canonical_json(body)) == body_sha256, f"D-129 {path.name} body differs")
    _require(body.get("status") == status, f"D-129 {path.name} status differs")
    expected_raw = (
        (canonical_json(payload) + "\n").encode("utf-8")
        if path == D128_OFFLINE_PATH
        else _pretty_bytes(payload)
    )
    _require(expected_raw == raw, f"D-129 {path.name} bytes are noncanonical")
    return payload, {
        "path": path.as_posix(),
        "schema_version": schema,
        "artifact_id": artifact_id,
        "semantic_body_hash": body_sha256,
        "file_bytes": file_bytes,
        "file_sha256": file_sha256,
        "blob_oid_at_d128_evidence_commit": blob_oid,
        "status": status,
        "recorded_at": body.get("recorded_at"),
        "artifact_mutated": False,
    }


def _predecessor_chain(root: Path) -> dict[str, Any]:
    topology = _validate_historical_topology(root)
    offline_payload, offline = _parse_artifact(
        root,
        path=D128_OFFLINE_PATH,
        schema=D128_OFFLINE_SCHEMA,
        artifact_id=D128_OFFLINE_ID,
        id_key="gate_id",
        body_sha256=D128_OFFLINE_BODY_SHA256,
        file_sha256=D128_OFFLINE_FILE_SHA256,
        file_bytes=D128_OFFLINE_FILE_BYTES,
        status=D128_OFFLINE_STATUS,
        blob_oid=D128_OFFLINE_BLOB_OID,
    )
    receipt_payload, receipt = _parse_artifact(
        root,
        path=D128_RECEIPT_PATH,
        schema=D128_RECEIPT_SCHEMA,
        artifact_id=D128_RECEIPT_ID,
        id_key="artifact_id",
        body_sha256=D128_RECEIPT_BODY_SHA256,
        file_sha256=D128_RECEIPT_FILE_SHA256,
        file_bytes=D128_RECEIPT_FILE_BYTES,
        status=D128_RECEIPT_STATUS,
        blob_oid=D128_RECEIPT_BLOB_OID,
    )
    attempt_payload, attempt = _parse_artifact(
        root,
        path=D128_ATTEMPT_PATH,
        schema=D128_ATTEMPT_SCHEMA,
        artifact_id=D128_ATTEMPT_ID,
        id_key="artifact_id",
        body_sha256=D128_ATTEMPT_BODY_SHA256,
        file_sha256=D128_ATTEMPT_FILE_SHA256,
        file_bytes=D128_ATTEMPT_FILE_BYTES,
        status=D128_ATTEMPT_STATUS,
        blob_oid=D128_ATTEMPT_BLOB_OID,
    )
    terminal_payload, terminal = _parse_artifact(
        root,
        path=D128_TERMINAL_PATH,
        schema=D128_TERMINAL_SCHEMA,
        artifact_id=D128_TERMINAL_ID,
        id_key="artifact_id",
        body_sha256=D128_TERMINAL_BODY_SHA256,
        file_sha256=D128_TERMINAL_FILE_SHA256,
        file_bytes=D128_TERMINAL_FILE_BYTES,
        status=D128_TERMINAL_STATUS,
        blob_oid=D128_TERMINAL_BLOB_OID,
    )
    offline_body = offline_payload["semantic_body"]
    receipt_body = receipt_payload["semantic_body"]
    attempt_body = attempt_payload["semantic_body"]
    terminal_body = terminal_payload["semantic_body"]
    _require(
        receipt_body["predecessor_binding"]["gate_id"] == D128_OFFLINE_ID,
        "D-129 D-128 receipt predecessor differs",
    )
    _require(
        attempt_body["receipt_binding"]["artifact_id"] == D128_RECEIPT_ID,
        "D-129 D-128 attempt receipt differs",
    )
    _require(
        terminal_body["receipt_binding"]["artifact_id"] == D128_RECEIPT_ID
        and terminal_body["attempt_binding"]["artifact_id"] == D128_ATTEMPT_ID,
        "D-129 D-128 terminal binding differs",
    )
    observation = terminal_body["observation"]
    authority = terminal_body["authority"]
    _require(
        observation["observed_blockers"] == [D128_TERMINAL_BLOCKER]
        and observation["passed"] is False
        and observation["docker_cli_command_count"] == 3
        and observation["read_only_daemon_or_image_call_count"] == 3
        and observation["daemon_start_count"] == 0
        and observation["image_pull_call_count"] == 0
        and observation["image_store_mutation_count"] == 0
        and observation["container_create_start_run_exec_count"] == 0
        and authority["execution_hash_created"] is False
        and authority["execution_candidate_created"] is False
        and authority["provider_calls_made"] == 0
        and authority["evaluator_calls_made"] == 0
        and authority["agent_runs_started"] == 0,
        "D-129 D-128 terminal boundary differs",
    )
    times = [
        _parse_time(offline_body["recorded_at"], label="offline recorded_at"),
        _parse_time(receipt_body["recorded_at"], label="receipt recorded_at"),
        _parse_time(attempt_body["recorded_at"], label="attempt recorded_at"),
        _parse_time(terminal_body["recorded_at"], label="terminal recorded_at"),
    ]
    _require(times == sorted(times) and len(set(times)) == 4, "D-129 D-128 chronology differs")
    for descendant in D128_DESCENDANT_PATHS:
        selected = root / descendant
        _require(not _lexists(selected), "D-129 D-128 descendant evidence exists")
    return {
        "d128_source_receipt_evidence_git_topology": topology,
        "offline_source_gate": offline,
        "approval_receipt": receipt,
        "docker_attempt": attempt,
        "blocked_docker_terminal": terminal,
        "terminal_blocker": D128_TERMINAL_BLOCKER,
        "receipt_is_consumed": True,
        "d128_retry_resume_or_repair_opened": False,
        "d128_pricing_preflight_and_gate_descendants_absent": True,
        "historical_d128_agent_docker_cli_calls": 3,
        "historical_d128_agent_image_pull_calls": 0,
    }


def _source_identity_for_build(root: Path) -> dict[str, Any]:
    git_before = _git_cli_observation(root)
    top = _git_command(root, "rev-parse", "--show-toplevel")
    _require(isinstance(top, str), "D-129 Git top-level differs")
    _require(Path(top).resolve(strict=True) == root, "D-129 Git top-level differs")
    _require(_status_lines(root) == [], "D-129 source gate requires clean committed source")
    head = _git_command(root, "rev-parse", "HEAD")
    _require(isinstance(head, str), "D-129 source commit differs")
    identity = _commit_identity(root, head)
    _require(identity["parents"] == [D128_EVIDENCE_COMMIT], "D-129 source parent differs")
    expected_diff = [{"status": "A", "path": path.as_posix()} for path in IMPLEMENTATION_PATHS]
    _require(
        sorted(_diff_rows(root, head), key=lambda row: row["path"])
        == sorted(expected_diff, key=lambda row: row["path"]),
        "D-129 source commit scope differs",
    )
    bindings = []
    for relative in IMPLEMENTATION_PATHS:
        oid, committed = _commit_blob(root, head, relative)
        current = _stable_read(root, relative)
        _require(current == committed, "D-129 implementation differs from committed blob")
        bindings.append(
            {
                "path": relative.as_posix(),
                "blob_oid": oid,
                **_file_binding(committed),
            }
        )
    git_after = _git_cli_observation(root)
    _require(git_before == git_after, "D-129 Git engine changed during source observation")
    return {
        **identity,
        "branch": _git_command(root, "branch", "--show-current") or None,
        "implementation_bindings": bindings,
        "source_commit_is_clean_exact_child_of_d128_evidence": True,
        "git_cli_observation": git_before,
    }


def _validate_git_observation(value: Any) -> None:
    _require(isinstance(value, dict), "D-129 Git observation differs")
    expected = (
        "resolved_path",
        "file_name",
        "file_bytes",
        "file_sha256",
        "linklike",
        "version",
        "actual_git_engine_invoked_directly",
        "repository_local_core_autocrlf",
        "authenticated_or_vendor_signed_identity_claimed",
        "stable_during_observation",
        "minimal_secret_free_environment",
        "fsmonitor_disabled",
        "shell_used",
    )
    _require(tuple(value) == expected, "D-129 Git observation fields differ")
    _require(
        Path(value["resolved_path"]).is_absolute()
        and value["file_name"].casefold() == "git.exe"
        and type(value["file_bytes"]) is int
        and value["file_bytes"] > 0
        and re.fullmatch(r"sha256:[0-9a-f]{64}", value["file_sha256"]) is not None
        and value["linklike"] is False
        and isinstance(value["version"], str)
        and value["actual_git_engine_invoked_directly"] is True
        and value["repository_local_core_autocrlf"] == "false"
        and value["authenticated_or_vendor_signed_identity_claimed"] is False
        and value["stable_during_observation"] is True
        and value["minimal_secret_free_environment"] is True
        and value["fsmonitor_disabled"] is True
        and value["shell_used"] is False,
        "D-129 Git observation differs",
    )


def _validate_source_identity(root: Path, source: Any) -> None:
    _require(isinstance(source, dict), "D-129 source identity differs")
    _require(
        tuple(source)
        == (
            "commit",
            "tree",
            "parents",
            "branch",
            "implementation_bindings",
            "source_commit_is_clean_exact_child_of_d128_evidence",
            "git_cli_observation",
        ),
        "D-129 source identity fields differ",
    )
    _require(
        re.fullmatch(r"[0-9a-f]{40}", source["commit"]) is not None
        and re.fullmatch(r"[0-9a-f]{40}", source["tree"]) is not None
        and source["parents"] == [D128_EVIDENCE_COMMIT]
        and (source["branch"] is None or isinstance(source["branch"], str))
        and source["source_commit_is_clean_exact_child_of_d128_evidence"] is True,
        "D-129 source identity differs",
    )
    _require(
        _commit_identity(root, source["commit"])
        == {
            "commit": source["commit"],
            "tree": source["tree"],
            "parents": source["parents"],
        },
        "D-129 committed source replay differs",
    )
    expected_diff = [{"status": "A", "path": path.as_posix()} for path in IMPLEMENTATION_PATHS]
    _require(
        sorted(_diff_rows(root, source["commit"]), key=lambda row: row["path"])
        == sorted(expected_diff, key=lambda row: row["path"]),
        "D-129 committed source scope differs",
    )
    bindings = source["implementation_bindings"]
    _require(
        isinstance(bindings, list) and len(bindings) == len(IMPLEMENTATION_PATHS),
        "D-129 implementation bindings differ",
    )
    for binding, relative in zip(bindings, IMPLEMENTATION_PATHS, strict=True):
        _require(
            isinstance(binding, dict)
            and tuple(binding) == ("path", "blob_oid", "file_bytes", "file_sha256")
            and binding["path"] == relative.as_posix(),
            "D-129 implementation binding differs",
        )
        oid, committed = _commit_blob(root, source["commit"], relative)
        _require(
            binding
            == {
                "path": relative.as_posix(),
                "blob_oid": oid,
                **_file_binding(committed),
            },
            "D-129 committed implementation binding differs",
        )
        _require(_stable_read(root, relative) == committed, "D-129 current source drifted")
    _validate_git_observation(source["git_cli_observation"])
    _require(
        _git_cli_observation(root) == source["git_cli_observation"],
        "D-129 current Git engine differs",
    )
    _require(
        (_git_command(root, "branch", "--show-current") or None) == source["branch"],
        "D-129 current branch differs",
    )


def _validate_checkout_state(root: Path, source: dict[str, Any]) -> dict[str, Any]:
    head = _git_command(root, "rev-parse", "HEAD")
    _require(isinstance(head, str), "D-129 current HEAD differs")
    status = _status_lines(root)
    if head == source["commit"]:
        _require(
            status in ([], [f"?? {OUTPUT_PATH.as_posix()}"]),
            "D-129 source checkout has unexpected changes",
        )
        return {"mode": "source-head", "evidence_commit": None}
    identity = _commit_identity(root, head)
    _require(identity["parents"] == [source["commit"]], "D-129 evidence parent differs")
    expected = [
        {"status": "A", "path": OUTPUT_PATH.as_posix()},
        *({"status": "M", "path": path.as_posix()} for path in ACTIVE_DOC_PATHS),
    ]
    _require(
        sorted(_diff_rows(root, head), key=lambda row: row["path"])
        == sorted(expected, key=lambda row: row["path"]),
        "D-129 evidence commit scope differs",
    )
    _require(status == [], "D-129 evidence checkout is not clean")
    _, committed = _commit_blob(root, head, OUTPUT_PATH)
    _require(committed == _stable_read(root, OUTPUT_PATH), "D-129 committed gate bytes differ")
    return {"mode": "post-evidence-commit", "evidence_commit": head}


def _manual_readiness_attestation() -> dict[str, Any]:
    return {
        "statement_code": "D129_USER_DOCKER_DESKTOP_LINUX_READY_NO_AUTO_START_KO_20260809_V1",
        "source": "current-user-conversation",
        "docker_endpoint": "npipe:////./pipe/dockerDesktopLinuxEngine",
        "reported_client_version": "29.6.2",
        "reported_server_version": "29.6.2",
        "reported_server_os": "linux",
        "reported_server_arch": "amd64",
        "reported_exit_code": 0,
        "user_reported_no_preexisting_container_auto_started": True,
        "user_reported_manual_docker_check_attempt_count": 2,
        "user_reported_successful_readiness_check_count": 1,
        "user_reported_failed_readiness_check_count": 1,
        "user_self_attested": True,
        "authenticated_or_signed": False,
        "independently_observed_by_agent": False,
        "raw_user_command_output_persisted": False,
        "agent_invoked_docker_call_count_for_d129": 0,
        "d128_terminal_reopened_or_retried": False,
        "readiness_is_temporally_unstable": True,
        "future_external_phase_must_reobserve_after_new_receipt": True,
        "attestation_is_not_external_approval_or_readiness_evidence": True,
    }


def _successor_contract() -> dict[str, Any]:
    contract = {
        "contract_version": "d128-terminal-successor-no-call-contract-d129-v1",
        "manual_prerequisite_supplied": True,
        "external_approval_recorded": False,
        "new_receipt_requires_future_exact_user_message": True,
        "offline_gate_is_not_an_approval_receipt": True,
        "external_entrypoint_present_in_this_module": False,
        "future_approved_scope": list(FUTURE_APPROVED_SCOPE),
        "future_explicitly_not_authorized": list(FUTURE_NOT_AUTHORIZED),
        "future_source_and_receipt_boundary": {
            "receipt_must_be_new_append_only_and_tracked_at_source_head": True,
            "receipt_must_bind_exact_clean_commit_tree_parent_and_module_bytes": True,
            "source_and_receipt_must_be_rechecked_before_each_external_phase": True,
            "future_evidence_commit_must_add_only_exact_successor_artifacts_and_docs": True,
        },
        "future_external_failure_boundary": {
            "attempt_intent_must_be_durable_before_each_first_external_call": True,
            "attempt_must_bind_receipt_source_modules_and_exact_phase_scope": True,
            "orphaned_attempt_must_block_retry_without_new_exact_user_approval": True,
            "existing_terminal_is_idempotent_and_must_not_be_rewritten": True,
            "terminal_must_record_actual_activity_counts_after_any_external_action": True,
        },
        "future_receipt_identity_boundary": {
            "approval_is_self_attested": True,
            "approval_is_authenticated_or_signed": False,
            "no_identity_upgrade_claim_is_permitted": True,
        },
        "future_exact_docker_boundary": {
            "endpoint": "npipe:////./pipe/dockerDesktopLinuxEngine",
            "cli_file_bytes": 43_095_472,
            "cli_file_sha256": (
                "sha256:8985cd8ac002c3240b5aa48fe401fcb55dca5d849b537e3c835564e8e8c49a70"
            ),
            "version": "29.6.2",
            "agent_must_not_start_desktop_or_daemon": True,
            "must_reobserve_linux_amd64_daemon_after_receipt": True,
        },
        "future_exact_image_refs": [
            (
                "docker.io/swerebenchv2/getmoto-moto@"
                "sha256:dfdf957ab30b8829e8b6bbfd693b00fab88b7979d3c856362fd5d66c489a1fee"
            ),
            (
                "docker.io/swerebenchv2/python-babel-babel@"
                "sha256:864e84fc4bdf09252f7fda4f85665cc05155a7b1d75847d61c67325abce7ef5a"
            ),
        ],
    }
    return {"contract": contract, "contract_hash": sha256_text(canonical_json(contract))}


def _approval_template_contract() -> dict[str, Any]:
    return {
        "template_version": "d129-terminal-successor-user-approval-template-v1",
        "required_predecessor_fields": [
            "D-129 gate ID",
            "D-129 semantic body SHA",
            "D-129 file SHA",
            "D-129 file bytes",
            "D-129 source/evidence commit",
        ],
        "manual_attestation_already_recorded_but_must_be_reobserved": True,
        "approved_scope": list(FUTURE_APPROVED_SCOPE),
        "explicitly_not_authorized": list(FUTURE_NOT_AUTHORIZED),
        "approval_is_self_attested": True,
        "approval_is_authenticated_or_signed": False,
        "generic_proceed_message_is_exact_approval": False,
        "rendering_this_template_records_approval": False,
        "receipt_must_be_tracked_at_clean_source_head_before_external_action": True,
    }


def _body(
    *,
    recorded_at: str,
    predecessor: dict[str, Any],
    source: dict[str, Any],
) -> dict[str, Any]:
    implementation = {
        "source_commit": source["commit"],
        "source_tree": source["tree"],
        "source_parent": source["parents"][0],
        "implementation_bindings": source["implementation_bindings"],
        "implementation_binding_hash": sha256_text(
            canonical_json(source["implementation_bindings"])
        ),
    }
    return {
        "milestone": MILESTONE,
        "evidence_kind": "offline-d128-terminal-successor-source-qualification",
        "recorded_at": recorded_at,
        "status": STATUS,
        "predecessor_chain": predecessor,
        "manual_readiness_attestation": _manual_readiness_attestation(),
        "source_identity": source,
        "successor_contract": _successor_contract(),
        "approval_template_contract": _approval_template_contract(),
        "implementation_integrity": implementation,
        "offline_qualification": {
            "exact_d128_chain_and_committed_bytes_validated": True,
            "d128_artifacts_preserved": True,
            "d128_terminal_retry_or_resume_opened": False,
            "manual_readiness_attestation_recorded": True,
            "manual_readiness_independently_observed_by_agent": False,
            "source_only_no_external_entrypoint": True,
            "focused_tests_external_to_builder": True,
            "focused_tests_are_local_not_remote_ci": True,
            "focused_tests_passed": FOCUSED_TESTS_PASSED,
            "selected_d122_d127_d128_d129_regression_tests_passed": (
                SELECTED_REGRESSION_TESTS_PASSED
            ),
            "selected_regression_count_includes_focused_tests": True,
            "focused_and_selected_counts_are_not_additive": True,
        },
        "blocked_prerequisites": list(BLOCKED_PREREQUISITES),
        "evidence_boundary": {
            "qualification_grade": "offline-source-local-git-and-zero-external-call-tests",
            "source_commit_tree_parent_and_module_blobs_bound": True,
            "git_identity_is_locally_observed_not_vendor_authenticated": True,
            "manual_readiness_is_user_self_attested": True,
            "manual_readiness_is_agent_observed": False,
            "manual_readiness_is_future_freshness_evidence": False,
            "raw_user_command_output_persisted": False,
            "dotenv_or_credential_presence_observed": False,
            "official_pricing_get_made": False,
            "sdk_or_endpoint_preflight_made": False,
            "execution_hash_candidate_reservation_or_ac_result_present": False,
        },
        "authority": {
            "d129_offline_source_gate_materialized": True,
            "d129_manual_readiness_attestation_recorded": True,
            "d129_user_external_approval_recorded": False,
            "d129_approval_receipt_created": False,
            "d129_source_commit_bound": True,
            "d129_evidence_commit_self_bound": False,
            "d129_offline_agent_invoked_docker_cli_calls": 0,
            "d129_offline_agent_invoked_docker_daemon_calls": 0,
            "historical_d128_agent_read_only_docker_calls": 3,
            "user_reported_manual_docker_check_attempts": 2,
            "user_reported_successful_manual_docker_readiness_checks": 1,
            "user_reported_failed_manual_docker_readiness_checks": 1,
            "docker_desktop_or_daemon_start_authorized": False,
            "d129_offline_container_create_start_run_exec_count": 0,
            "d129_offline_image_pull_or_store_mutation_count": 0,
            "d129_offline_network_calls_made": 0,
            "d129_offline_pricing_public_get_count": 0,
            "d129_offline_sdk_probe_count": 0,
            "d129_offline_credential_presence_observed": False,
            "d129_offline_provider_calls_made": 0,
            "d129_offline_evaluator_calls_made": 0,
            "d129_offline_agent_runs_started": 0,
            "d129_offline_retrieval_call_count": 0,
            "d129_offline_runtime_memory_injection_count": 0,
            "d129_offline_execution_hash_created": False,
            "d129_offline_execution_candidate_created": False,
            "d129_offline_cost_reserved_or_spent_usd": "0",
            "d129_offline_four_row_ac_execution_authorized": False,
        },
        "next_gate": {
            "action": "request-exact-d129-terminal-successor-external-no-call-approval",
            "must_quote_exact_materialized_d129_gate_triple_and_file_bytes": True,
            "must_quote_exact_d129_source_or_evidence_commit": True,
            "must_create_a_new_append_only_receipt": True,
            "receipt_must_bind_clean_commit_tree_parent_and_module_bytes": True,
            "must_reobserve_daemon_and_images_after_receipt": True,
            "attempt_intent_must_precede_every_external_phase": True,
            "orphaned_attempt_requires_another_exact_user_approval": True,
            "must_not_reuse_delete_or_rewrite_d128_receipt_attempt_or_terminal": True,
            "does_not_authorize_any_external_action": True,
            "execution_hash_candidate_cost_and_ac_run_remain_later_gates": True,
        },
    }


def _envelope(body: dict[str, Any]) -> dict[str, Any]:
    body_hash = sha256_text(canonical_json(body))
    return {
        "schema_version": SCHEMA_VERSION,
        "gate_id": f"d129_{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": body,
    }


def _write_new(root: Path, raw: bytes) -> None:
    output = _logical_path(root, OUTPUT_PATH, must_exist=False)
    _require(not _lexists(output), "D-129 output already exists")
    temporary = output.with_name(f".{output.name}.d129-{uuid.uuid4().hex}.tmp")
    _require(not _lexists(temporary), "D-129 temporary output collision")
    try:
        with temporary.open("xb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        _require(temporary.read_bytes() == raw, "D-129 temporary output differs")
        try:
            os.link(temporary, output)
        except FileExistsError as exc:
            raise D129OfflineGateError("D-129 output collision") from exc
        _require(_stable_read(root, OUTPUT_PATH) == raw, "D-129 persisted output differs")
    finally:
        with suppress(OSError):
            temporary.unlink()


def _validate_payload(root: Path, payload: Any, raw: bytes) -> dict[str, Any]:
    _require(isinstance(payload, dict), "D-129 gate root is not an object")
    _require(tuple(payload) == ROOT_KEYS, "D-129 gate root fields differ")
    _require(payload["schema_version"] == SCHEMA_VERSION, "D-129 gate schema differs")
    body = payload["semantic_body"]
    _require(isinstance(body, dict), "D-129 semantic body differs")
    _require(tuple(body) == BODY_KEYS, "D-129 semantic body fields differ")
    _require(body["milestone"] == MILESTONE and body["status"] == STATUS, "D-129 status differs")
    body_hash = sha256_text(canonical_json(body))
    _require(payload["semantic_body_hash"] == body_hash, "D-129 semantic body SHA differs")
    _require(
        payload["gate_id"] == f"d129_{body_hash.removeprefix('sha256:')}",
        "D-129 gate ID differs",
    )
    _require(_pretty_bytes(payload) == raw, "D-129 gate bytes are noncanonical")
    recorded_at = _parse_time(body["recorded_at"], label="recorded_at")
    predecessor = _predecessor_chain(root)
    _require(
        canonical_json(predecessor) == canonical_json(body["predecessor_chain"]),
        "D-129 predecessor chain differs",
    )
    terminal_time = _parse_time(
        predecessor["blocked_docker_terminal"]["recorded_at"],
        label="terminal recorded_at",
    )
    _require(recorded_at > terminal_time, "D-129 chronology differs")
    source = body["source_identity"]
    _validate_source_identity(root, source)
    expected = _envelope(
        _body(recorded_at=body["recorded_at"], predecessor=predecessor, source=source)
    )
    _require(canonical_json(payload) == canonical_json(expected), "D-129 full payload differs")
    checkout = _validate_checkout_state(root, source)
    return {**payload, "_checkout": checkout}


def _result(payload: dict[str, Any], raw: bytes) -> dict[str, Any]:
    checkout = payload.get("_checkout", {})
    return {
        "status": STATUS,
        "gate_id": payload["gate_id"],
        "semantic_body_hash": payload["semantic_body_hash"],
        "file_bytes": len(raw),
        "file_sha256": sha256_bytes(raw),
        "source_commit": payload["semantic_body"]["source_identity"]["commit"],
        "evidence_commit": checkout.get("evidence_commit"),
        "user_approval_required": True,
        "approval_receipt_created": False,
        "manual_readiness_attestation_recorded": True,
        "agent_docker_calls_made": 0,
        "network_calls_made": 0,
        "execution_hash_created": False,
        "execution_candidate_created": False,
    }


def validate_d129_offline_source_gate(*, repository: str | Path | None = None) -> dict[str, Any]:
    """Validate the D-129 gate against exact committed source and D-128 history."""

    root = _repo_root(repository)
    raw = _stable_read(root, OUTPUT_PATH)
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise D129OfflineGateError("D-129 gate is not canonical UTF-8 JSON") from exc
    validated = _validate_payload(root, payload, raw)
    return _result(validated, raw)


def run_d129_offline_source_gate(*, repository: str | Path | None = None) -> dict[str, Any]:
    """Materialize only the append-only offline D-129 source gate."""

    root = _repo_root(repository)
    output = _logical_path(root, OUTPUT_PATH, must_exist=False)
    if _lexists(output):
        return validate_d129_offline_source_gate(repository=root)
    predecessor = _predecessor_chain(root)
    source = _source_identity_for_build(root)
    recorded_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    _require(
        _parse_time(recorded_at, label="recorded_at")
        > _parse_time(
            predecessor["blocked_docker_terminal"]["recorded_at"],
            label="terminal recorded_at",
        ),
        "D-129 chronology differs before output publication",
    )
    payload = _envelope(_body(recorded_at=recorded_at, predecessor=predecessor, source=source))
    raw = _pretty_bytes(payload)
    _validate_payload(root, payload, raw)
    _write_new(root, raw)
    validated = _validate_payload(root, payload, raw)
    return _result(validated, raw)


def render_d129_successor_approval_template(*, repository: str | Path | None = None) -> str:
    """Render a non-authoritative future approval template for the exact gate."""

    result = validate_d129_offline_source_gate(repository=repository)
    evidence_commit = result["evidence_commit"] or "<exact commit after gate/docs commit>"
    return "\n".join(
        (
            "D-129 terminal-successor external no-call preflight approval",
            "",
            f"Gate ID\n{result['gate_id']}",
            f"Semantic body SHA\n{result['semantic_body_hash']}",
            f"File SHA\n{result['file_sha256']}",
            f"File bytes\n{result['file_bytes']}",
            f"Source/evidence commit\n{evidence_commit}",
            "",
            "User prerequisite already self-attested",
            "- Docker Desktop Linux daemon reported ready: 29.6.2/linux/amd64/rc=0.",
            "- No pre-existing container auto-start was reported.",
            "- The future phase must reobserve readiness; the agent must not start the daemon.",
            "",
            "Approved scope",
            *(f"- {item}" for item in FUTURE_APPROVED_SCOPE),
            "",
            "Explicitly not authorized",
            *(f"- {item}" for item in FUTURE_NOT_AUTHORIZED),
        )
    )


__all__ = [
    "D129OfflineGateError",
    "OUTPUT_PATH",
    "render_d129_successor_approval_template",
    "run_d129_offline_source_gate",
    "validate_d129_offline_source_gate",
]
