"""D-126 clean-source, pricing, and no-call environment preflight.

This module consumes the user's exact D-125 next-gate approval.  It may seal a
clean local source commit, read public official OpenAI documentation, and run a
strictly read-only Docker/SDK/credential/endpoint observation.  It never builds
an execution hash or candidate and never invokes an agent, provider, evaluator,
retrieval path, or Docker workload operation.
"""

from __future__ import annotations

import ast
import importlib.metadata
import json
import os
import re
import stat
import subprocess
import sys
import uuid
from collections.abc import Sequence
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal, Protocol

from patchloop.errors import ContractError
from patchloop.evals import d125_ac_runtime_finalization_qualification as d125
from patchloop.runtime import repository_root
from patchloop.util import canonical_json, sha256_bytes, sha256_text

MILESTONE = "D-126"
RECEIPT_SCHEMA = "ac-clean-pricing-no-call-preflight-approval-receipt-d126-v1"
PREFLIGHT_SCHEMA = "ac-clean-pricing-no-call-readiness-preflight-d126-v1"
GATE_SCHEMA = "ac-clean-source-pricing-no-call-preflight-gate-d126-v1"
RECEIPT_STATUS = "D126_D125_NEXT_GATE_APPROVAL_RECORDED"
READY_STATUS = "D126_CLEAN_SOURCE_PRICING_NO_CALL_PREFLIGHT_READY_EXECUTION_HASH_BLOCKED"
BLOCKED_STATUS = "D126_CLEAN_SOURCE_PRICING_NO_CALL_PREFLIGHT_OBSERVED_BLOCKED"

D125_PATH = Path(
    "reports/live-pilot/artifacts/d125-ac-runtime-finalization-offline-source-gate.json"
)
D125_GATE_ID = "d125_ed9c892a598ce4543591bf3b9135a1cbe3752589fdc447b05867d59e07d45539"
D125_BODY_SHA256 = "sha256:ed9c892a598ce4543591bf3b9135a1cbe3752589fdc447b05867d59e07d45539"
D125_FILE_SHA256 = "sha256:9bc5f6e618f31312dc5026a807eabf478e47c05893cca72c71328378b593856e"
D125_FILE_BYTES = 13_820
D125_STATUS = "D125_AC_RUNTIME_FINALIZATION_SOURCE_QUALIFIED_EXECUTION_CANDIDATE_BLOCKED"

RECEIPT_PATH = Path(
    "reports/live-pilot/artifacts/d126-ac-clean-pricing-no-call-preflight-approval-receipt.json"
)
PREFLIGHT_PATH = Path(
    "reports/live-pilot/artifacts/d126-ac-clean-pricing-no-call-readiness-preflight.json"
)
GATE_PATH = Path(
    "reports/live-pilot/artifacts/d126-ac-clean-source-pricing-no-call-preflight-gate.json"
)

OFFICIAL_MODEL_PAGE_URL = "https://developers.openai.com/api/docs/models/gpt-5.4-mini.md"
OFFICIAL_PRICING_PAGE_URL = "https://developers.openai.com/api/docs/pricing"
OFFICIAL_API_BASE_URL = "https://api.openai.com/v1"
MODEL_ID = "gpt-5.4-mini-2026-03-17"
MODEL_LABEL = "GPT-5.4 mini"
INPUT_RATE = Decimal("0.75")
CACHED_INPUT_RATE = Decimal("0.075")
OUTPUT_RATE = Decimal("4.5")
MAX_TOTAL_TOKENS = 3_000_000
MAX_OUTPUT_TOKENS = 25_000
SCHEDULED_ROWS = 4
PER_ROW_RESERVE = Decimal("13.6125")
FULL_RESERVE = Decimal("54.45")
HARD_CAP = Decimal("55.00")
FRESHNESS_SECONDS = 72 * 60 * 60

LOCAL_DOCKER_CONTEXT = "desktop-linux"
LOCAL_DOCKER_ENDPOINT = "npipe:////./pipe/dockerDesktopLinuxEngine"
DOCKER_VERSION_FORMAT = (
    '{"ClientVersion":{{json .Client.Version}},'
    '"ServerVersion":{{json .Server.Version}},'
    '"ServerOs":{{json .Server.Os}},'
    '"ServerArch":{{json .Server.Arch}}}'
)
DOCKER_CONTEXT_ENDPOINT_FORMAT = "{{json .Endpoints.docker.Host}}"
DOCKER_IMAGE_ID_FORMAT = "{{.Id}}"
DOCKER_IMAGES = (
    "docker.io/swerebenchv2/getmoto-moto@"
    "sha256:dfdf957ab30b8829e8b6bbfd693b00fab88b7979d3c856362fd5d66c489a1fee",
    "docker.io/swerebenchv2/python-babel-babel@"
    "sha256:864e84fc4bdf09252f7fda4f85665cc05155a7b1d75847d61c67325abce7ef5a",
)
MAX_COMMAND_OUTPUT_BYTES = 16_384
MAX_HTTP_BODY_BYTES = 128_000

APPROVED_SCOPE = (
    "seal-clean-committed-source-identity-and-create-required-local-git-commit",
    "read-current-official-openai-pricing-and-create-within-72-hour-evidence",
    "run-read-only-no-call-docker-sdk-credential-presence-and-endpoint-preflight",
)
NOT_AUTHORIZED = (
    "provider-evaluator-or-agent-execution",
    "runtime-memory-injection-or-retrieval",
    "docker-workload-container-create-start-run-exec-or-mutation",
    "execution-hash-creation",
    "execution-authorization-candidate-creation",
    "cost-reservation-spend-or-four-row-ac-execution",
)

ROOT_KEYS = ("schema_version", "artifact_id", "semantic_body_hash", "semantic_body")
RECEIPT_BODY_KEYS = (
    "milestone",
    "evidence_kind",
    "recorded_at",
    "status",
    "predecessor_binding",
    "approval",
    "authority",
    "evidence_boundary",
)
PREFLIGHT_BODY_KEYS = (
    "milestone",
    "evidence_kind",
    "recorded_at",
    "status",
    "observer_contract",
    "receipt_binding",
    "source_commit_observation",
    "official_pricing_observation",
    "docker_observation",
    "sdk_credential_endpoint_observation",
    "observed_blockers",
    "authority",
    "evidence_boundary",
)
GATE_BODY_KEYS = (
    "milestone",
    "evidence_kind",
    "recorded_at",
    "status",
    "receipt_binding",
    "preflight_binding",
    "qualification",
    "authority",
    "next_gate",
    "evidence_boundary",
)

SENSITIVE_ENV_NAMES = (
    "OPENAI_API_KEY",
    "OPENAI_ADMIN_KEY",
    "OPENAI_BASE_URL",
    "OPENAI_API_BASE",
    "OPENAI_CUSTOM_HEADERS",
    "OPENAI_ORG_ID",
    "OPENAI_ORGANIZATION",
    "OPENAI_PROJECT_ID",
    "OPENAI_PROJECT",
    "OPENAI_WEBHOOK_SECRET",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "NO_PROXY",
    "SSL_CERT_FILE",
    "SSL_CERT_DIR",
    "REQUESTS_CA_BUNDLE",
    "CURL_CA_BUNDLE",
)
FORBIDDEN_ROUTING_ENV_NAMES = tuple(
    name for name in SENSITIVE_ENV_NAMES if name != "OPENAI_API_KEY"
)


class D126PreflightError(ContractError):
    """Raised when D-126 evidence cannot be built or validated fail-closed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise D126PreflightError(message)


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _parse_time(value: Any, *, label: str) -> datetime:
    _require(isinstance(value, str), f"D-126 {label} is missing")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise D126PreflightError(f"D-126 {label} is invalid") from exc
    _require(parsed.tzinfo is not None, f"D-126 {label} is timezone-naive")
    return parsed.astimezone(UTC)


def _repo_root(repository: str | Path | None) -> Path:
    selected = Path(repository) if repository is not None else repository_root()
    try:
        root = selected.resolve(strict=True)
    except OSError as exc:
        raise D126PreflightError("D-126 repository root is unavailable") from exc
    _require(root.is_dir(), "D-126 repository root is not a directory")
    return root


def _is_linklike(path: Path) -> bool:
    if path.is_symlink():
        return True
    is_junction = getattr(path, "is_junction", None)
    if callable(is_junction) and is_junction():
        return True
    try:
        info = path.lstat()
    except OSError:
        return False
    attributes = getattr(info, "st_file_attributes", 0)
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return stat.S_ISLNK(info.st_mode) or bool(reparse and attributes & reparse)


def _safe_path(root: Path, relative: Path, *, must_exist: bool) -> Path:
    _require(not relative.is_absolute(), "D-126 path must be repository-relative")
    _require(".." not in relative.parts, "D-126 path traversal is forbidden")
    _require(":" not in relative.as_posix(), "D-126 alternate stream path is forbidden")
    current = root
    parts = relative.parts if must_exist else relative.parent.parts
    for part in parts:
        current = current / part
        _require(current.exists(), f"D-126 path parent is missing: {relative.as_posix()}")
        _require(not _is_linklike(current), f"D-126 path is linklike: {relative.as_posix()}")
    selected = root / relative
    if must_exist:
        _require(selected.is_file(), f"D-126 file is missing: {relative.as_posix()}")
        _require(not _is_linklike(selected), f"D-126 file is linklike: {relative.as_posix()}")
    else:
        _require(not selected.exists(), f"D-126 output already exists: {relative.as_posix()}")
    try:
        resolved = selected.resolve(strict=must_exist)
    except OSError as exc:
        raise D126PreflightError(f"D-126 path cannot be resolved: {relative.as_posix()}") from exc
    _require(resolved.is_relative_to(root), "D-126 path escapes repository")
    return selected


def _stable_read(root: Path, relative: Path) -> bytes:
    path = _safe_path(root, relative, must_exist=True)
    try:
        before = path.stat()
        with path.open("rb") as stream:
            opened = os.fstat(stream.fileno())
            content = stream.read()
            after_open = os.fstat(stream.fileno())
        after = path.stat()
    except OSError as exc:
        raise D126PreflightError(f"D-126 cannot stably read {relative.as_posix()}") from exc

    def identity(value: os.stat_result) -> tuple[int, int, int, int]:
        return (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns)

    _require(
        identity(before) == identity(opened) == identity(after_open) == identity(after),
        f"D-126 file changed while reading: {relative.as_posix()}",
    )
    _require(len(content) == after.st_size, f"D-126 file size differs: {relative.as_posix()}")
    return content


def _write_new(root: Path, relative: Path, content: bytes) -> None:
    target = _safe_path(root, relative, must_exist=False)
    temporary = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        _require(temporary.read_bytes() == content, "D-126 temporary artifact bytes differ")
        try:
            os.link(temporary, target)
        except FileExistsError as exc:
            raise D126PreflightError(f"D-126 output collision: {relative.as_posix()}") from exc
        _require(_stable_read(root, relative) == content, "D-126 persisted artifact bytes differ")
    finally:
        with suppress(OSError):
            temporary.unlink()


def _pretty_bytes(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def _envelope(schema: str, prefix: str, body: dict[str, Any]) -> dict[str, Any]:
    digest = sha256_text(canonical_json(body))
    return {
        "schema_version": schema,
        "artifact_id": f"{prefix}{digest.removeprefix('sha256:')}",
        "semantic_body_hash": digest,
        "semantic_body": body,
    }


def _binding(root: Path, relative: Path, id_key: str = "artifact_id") -> dict[str, Any]:
    content = _stable_read(root, relative)
    try:
        payload = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise D126PreflightError(f"D-126 artifact JSON is invalid: {relative.as_posix()}") from exc
    _require(isinstance(payload, dict), "D-126 artifact root is not an object")
    return {
        "path": relative.as_posix(),
        "artifact_id": payload.get(id_key),
        "semantic_body_hash": payload.get("semantic_body_hash"),
        "file_bytes": len(content),
        "file_sha256": sha256_bytes(content),
    }


def _load_envelope(root: Path, relative: Path, *, schema: str, prefix: str) -> dict[str, Any]:
    content = _stable_read(root, relative)
    try:
        payload = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise D126PreflightError(f"D-126 artifact JSON is invalid: {relative.as_posix()}") from exc
    _require(isinstance(payload, dict), "D-126 artifact root is not an object")
    _require(tuple(payload) == ROOT_KEYS, "D-126 artifact root fields differ")
    _require(payload.get("schema_version") == schema, "D-126 artifact schema differs")
    body = payload.get("semantic_body")
    _require(isinstance(body, dict), "D-126 semantic body is not an object")
    expected = _envelope(schema, prefix, body)
    _require(canonical_json(payload) == canonical_json(expected), "D-126 envelope hash differs")
    _require(_pretty_bytes(payload) == content, "D-126 artifact bytes are noncanonical")
    return payload


def _d125_binding(root: Path) -> dict[str, Any]:
    _require(
        d125.SEALED_HISTORICAL_GATE_ID == D125_GATE_ID
        and d125.SEALED_HISTORICAL_BODY_SHA256 == D125_BODY_SHA256
        and d125.SEALED_HISTORICAL_FILE_SHA256 == D125_FILE_SHA256
        and d125.SEALED_HISTORICAL_FILE_BYTES == D125_FILE_BYTES,
        "D-126 D-125 sealed constants differ",
    )
    result = d125.validate_d125_source_gate(
        repository=root,
        mode="sealed-historical",
    )
    _require(result["gate_id"] == D125_GATE_ID, "D-126 D-125 gate ID differs")
    _require(result["semantic_body_hash"] == D125_BODY_SHA256, "D-126 D-125 body SHA differs")
    _require(result["file_sha256"] == D125_FILE_SHA256, "D-126 D-125 file SHA differs")
    _require(result["file_bytes"] == D125_FILE_BYTES, "D-126 D-125 file bytes differ")
    raw = _stable_read(root, D125_PATH)
    payload = json.loads(raw.decode("utf-8"))
    _require(payload["semantic_body"]["status"] == D125_STATUS, "D-126 D-125 status differs")
    return {
        "path": D125_PATH.as_posix(),
        "gate_id": D125_GATE_ID,
        "semantic_body_hash": D125_BODY_SHA256,
        "file_bytes": D125_FILE_BYTES,
        "file_sha256": D125_FILE_SHA256,
        "status": D125_STATUS,
        "artifact_mutated": False,
    }


def _receipt_body(root: Path, recorded_at: str) -> dict[str, Any]:
    _parse_time(recorded_at, label="receipt recorded_at")
    return {
        "milestone": MILESTONE,
        "evidence_kind": "exact-d125-next-gate-user-approval-receipt",
        "recorded_at": recorded_at,
        "status": RECEIPT_STATUS,
        "predecessor_binding": _d125_binding(root),
        "approval": {
            "statement_code": "D125_NEXT_GATE_APPROVAL_KO_20260809_V1",
            "approved_scope": list(APPROVED_SCOPE),
            "explicitly_not_authorized": list(NOT_AUTHORIZED),
            "approval_is_self_attested": True,
            "approval_is_authenticated_or_signed": False,
        },
        "authority": {
            "clean_source_commit_authorized": True,
            "official_openai_pricing_lookup_authorized": True,
            "read_only_no_call_environment_preflight_authorized": True,
            "execution_hash_creation_authorized": False,
            "execution_candidate_creation_authorized": False,
            "provider_evaluator_agent_execution_authorized": False,
            "runtime_memory_or_retrieval_authorized": False,
            "docker_workload_or_mutation_authorized": False,
            "cost_reservation_or_spend_authorized": False,
        },
        "evidence_boundary": {
            "receipt_must_precede_production_pricing_and_environment_observations": True,
            "receipt_does_not_prove_environment_readiness": True,
            "receipt_does_not_authorize_execution": True,
        },
    }


def _validate_receipt(root: Path) -> dict[str, Any]:
    payload = _load_envelope(root, RECEIPT_PATH, schema=RECEIPT_SCHEMA, prefix="d126approval_")
    body = payload["semantic_body"]
    _require(tuple(body) == RECEIPT_BODY_KEYS, "D-126 receipt body fields differ")
    expected = _receipt_body(root, body.get("recorded_at"))
    _require(canonical_json(body) == canonical_json(expected), "D-126 receipt payload differs")
    return payload


def create_d126_approval_receipt(*, repository: str | Path | None = None) -> dict[str, Any]:
    root = _repo_root(repository)
    if (root / RECEIPT_PATH).exists():
        payload = _validate_receipt(root)
    else:
        _require(not (root / PREFLIGHT_PATH).exists(), "D-126 preflight exists without receipt")
        _require(not (root / GATE_PATH).exists(), "D-126 gate exists without receipt")
        body = _receipt_body(root, _now())
        payload = _envelope(RECEIPT_SCHEMA, "d126approval_", body)
        _write_new(root, RECEIPT_PATH, _pretty_bytes(payload))
        payload = _validate_receipt(root)
    binding = _binding(root, RECEIPT_PATH)
    return {"status": RECEIPT_STATUS, **binding}


def _run_git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, check=False, shell=False
    )
    _require(result.returncode == 0, f"D-126 git command failed: {' '.join(args)}")
    return result.stdout.strip()


def _git_observation(root: Path) -> dict[str, Any]:
    status = _run_git(root, "status", "--porcelain", "--untracked-files=all")
    _require(not status, "D-126 source commit observation requires a clean Git worktree")
    commit = _run_git(root, "rev-parse", "HEAD")
    tree = _run_git(root, "rev-parse", "HEAD^{tree}")
    parent = _run_git(root, "rev-parse", "HEAD^")
    branch = _run_git(root, "branch", "--show-current")
    tracked = _run_git(root, "ls-tree", "-r", "--full-tree", "HEAD")
    return {
        "commit": commit,
        "tree": tree,
        "parent": parent,
        "branch": branch,
        "tracked_tree_listing_sha256": sha256_bytes((tracked + "\n").encode("utf-8")),
        "worktree_clean_before_observation": True,
        "index_clean_before_observation": True,
        "scope": "current-main-worktree-commit-tree-only",
        "ignored_or_external_worktrees_claimed_clean": False,
    }


@dataclass(frozen=True)
class FetchedDocument:
    status_code: int
    final_url: str
    content_type: str
    etag: str | None
    body: bytes
    redirect_count: int = 0


class DocumentFetcher(Protocol):
    def fetch(self, url: str) -> FetchedDocument: ...


class OfficialDocsFetcher:
    def fetch(self, url: str) -> FetchedDocument:
        import httpx

        current = url
        redirects = 0
        with httpx.Client(trust_env=False, follow_redirects=False, timeout=30.0) as client:
            while True:
                parsed = httpx.URL(current)
                _require(
                    parsed.scheme == "https" and parsed.host == "developers.openai.com",
                    "D-126 official docs request left the allowlisted host",
                )
                response = client.get(
                    current,
                    headers={"User-Agent": "PatchLoop-D126-NoCall-Preflight/1"},
                )
                if response.is_redirect:
                    redirects += 1
                    _require(redirects <= 3, "D-126 official docs redirect limit exceeded")
                    current = str(response.url.join(response.headers["location"]))
                    continue
                body = response.content
                _require(len(body) <= MAX_HTTP_BODY_BYTES, "D-126 official docs body is too large")
                return FetchedDocument(
                    status_code=int(response.status_code),
                    final_url=str(response.url),
                    content_type=str(response.headers.get("Content-Type") or ""),
                    etag=response.headers.get("ETag"),
                    body=body,
                    redirect_count=redirects,
                )


def _pricing_observation(fetcher: DocumentFetcher, observed_at: str) -> dict[str, Any]:
    observed_time = _parse_time(observed_at, label="pricing observed_at")
    document = fetcher.fetch(OFFICIAL_MODEL_PAGE_URL)
    _require(document.status_code == 200, "D-126 official model page status differs")
    _require(document.final_url == OFFICIAL_MODEL_PAGE_URL, "D-126 official model page URL differs")
    _require(
        document.content_type.lower().startswith("text/markdown"),
        "D-126 official model page content type differs",
    )
    try:
        text = document.body.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise D126PreflightError("D-126 official model page is not UTF-8") from exc
    required_fragments = (
        f"Default snapshot: `{MODEL_ID}`",
        "| Input | $0.75 | 1M tokens |",
        "| Cached input | $0.075 | 1M tokens |",
        "| Output | $4.5 | 1M tokens |",
        "| Responses | `v1/responses` | Supported |",
        "| GPT-5.4 mini | $0.75 | $0.075 | $4.5 |",
    )
    _require(all(fragment in text for fragment in required_fragments), "D-126 pricing facts differ")
    worst_rate = max(INPUT_RATE, CACHED_INPUT_RATE, OUTPUT_RATE)
    per_row = (Decimal(MAX_TOTAL_TOKENS + MAX_OUTPUT_TOKENS) * worst_rate) / Decimal(1_000_000)
    full = per_row * Decimal(SCHEDULED_ROWS)
    _require(per_row == PER_ROW_RESERVE, "D-126 per-row reserve arithmetic differs")
    _require(full == FULL_RESERVE, "D-126 full reserve arithmetic differs")
    facts = {
        "model_label": MODEL_LABEL,
        "dated_model_id": MODEL_ID,
        "service_tier": "default-standard",
        "unit": "usd-per-1m-text-tokens",
        "input_usd": str(INPUT_RATE),
        "cached_input_usd": str(CACHED_INPUT_RATE),
        "cache_write_input_usd": None,
        "output_usd": str(OUTPUT_RATE),
        "responses_endpoint_supported": True,
    }
    return {
        "observed_at": observed_time.isoformat().replace("+00:00", "Z"),
        "source_url": OFFICIAL_MODEL_PAGE_URL,
        "pricing_index_url": OFFICIAL_PRICING_PAGE_URL,
        "final_url": document.final_url,
        "official_host": "developers.openai.com",
        "http_status": document.status_code,
        "content_type": document.content_type,
        "etag": document.etag,
        "redirect_count": document.redirect_count,
        "public_get_request_count": document.redirect_count + 1,
        "public_body_bytes": len(document.body),
        "public_body_sha256": sha256_bytes(document.body),
        "source_evidence_lines": list(required_fragments),
        "source_evidence_sha256": sha256_text(canonical_json(list(required_fragments))),
        "facts": facts,
        "facts_sha256": sha256_text(canonical_json(facts)),
        "planning_math": {
            "max_total_tokens": MAX_TOTAL_TOKENS,
            "max_output_tokens": MAX_OUTPUT_TOKENS,
            "conservative_worst_rate_usd_per_million": str(worst_rate),
            "per_row_reserve_usd": str(PER_ROW_RESERVE),
            "scheduled_rows": SCHEDULED_ROWS,
            "full_schedule_reserve_usd": str(FULL_RESERVE),
            "hard_cap_usd": str(HARD_CAP),
            "per_row_reserve_nanos": 13_612_500_000,
            "full_schedule_reserve_nanos": 54_450_000_000,
            "hard_cap_nanos": 55_000_000_000,
        },
        "freshness_window_seconds": FRESHNESS_SECONDS,
        "fresh_at_capture": True,
        "request_auth_or_cookie_sent": False,
        "proxy_use_disabled_by_fetcher": True,
        "raw_body_persisted": False,
    }


class CommandRunner(Protocol):
    def run(
        self,
        command: Sequence[str],
        *,
        environment: dict[str, str],
        timeout_seconds: int,
    ) -> subprocess.CompletedProcess[bytes]: ...


class SubprocessCommandRunner:
    def run(
        self,
        command: Sequence[str],
        *,
        environment: dict[str, str],
        timeout_seconds: int,
    ) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(  # noqa: S603
            list(command),
            capture_output=True,
            check=False,
            shell=False,
            env=environment,
            timeout=timeout_seconds,
        )


def _docker_cli_path() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    _require(bool(local_app_data), "D-126 LOCALAPPDATA is unavailable")
    return Path(str(local_app_data)) / "Programs/DockerDesktop/resources/bin/docker.exe"


def _external_file_binding(path: Path, *, label: str) -> dict[str, Any]:
    _require(path.is_file(), f"D-126 {label} is missing")
    _require(not _is_linklike(path), f"D-126 {label} is linklike")
    try:
        resolved = path.resolve(strict=True)
        before = resolved.stat()
        content = resolved.read_bytes()
        after = resolved.stat()
    except OSError as exc:
        raise D126PreflightError(f"D-126 {label} cannot be read") from exc
    _require(
        (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
        == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns),
        f"D-126 {label} changed while reading",
    )
    return {
        "file_name": resolved.name,
        "file_bytes": len(content),
        "file_sha256": sha256_bytes(content),
        "linklike": False,
    }


def _docker_commands(docker: str) -> tuple[tuple[str, str, list[str]], ...]:
    return (
        ("cli-version", "config", [docker, "--version"]),
        ("context-show", "config", [docker, "context", "show"]),
        (
            "context-endpoint",
            "config",
            [
                docker,
                "context",
                "inspect",
                LOCAL_DOCKER_CONTEXT,
                "--format",
                DOCKER_CONTEXT_ENDPOINT_FORMAT,
            ],
        ),
        (
            "daemon-version",
            "daemon",
            [docker, "version", "--format", DOCKER_VERSION_FORMAT],
        ),
        (
            "image-moto",
            "daemon",
            [docker, "image", "inspect", "--format", DOCKER_IMAGE_ID_FORMAT, DOCKER_IMAGES[0]],
        ),
        (
            "image-babel",
            "daemon",
            [docker, "image", "inspect", "--format", DOCKER_IMAGE_ID_FORMAT, DOCKER_IMAGES[1]],
        ),
    )


def _validate_docker_argv(command: Sequence[str], docker: str) -> None:
    allowed = {tuple(item[2]) for item in _docker_commands(docker)}
    _require(tuple(command) in allowed, "D-126 Docker argv is outside the read-only allowlist")
    forbidden = {"pull", "info", "build", "create", "start", "run", "exec", "rm", "ps"}
    _require(
        not any(token in forbidden for token in command[1:]), "D-126 Docker workload verb forbidden"
    )


def _docker_environment(*, daemon: bool) -> dict[str, str]:
    allowed = ("SYSTEMROOT", "WINDIR", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "TEMP", "TMP")
    environment = {key: os.environ[key] for key in allowed if os.environ.get(key)}
    if daemon:
        environment["DOCKER_HOST"] = LOCAL_DOCKER_ENDPOINT
    return environment


def _summary(
    role: str, command: Sequence[str], result: subprocess.CompletedProcess[bytes]
) -> dict[str, Any]:
    return {
        "role": role,
        "argv_contract": ["<exact-docker-cli>", *command[1:]],
        "return_code": int(result.returncode),
        "stdout_bytes": len(result.stdout),
        "stdout_sha256": sha256_bytes(result.stdout),
        "stderr_bytes": len(result.stderr),
        "stderr_sha256": sha256_bytes(result.stderr),
        "stdout_within_bound": len(result.stdout) <= MAX_COMMAND_OUTPUT_BYTES,
        "stderr_within_bound": len(result.stderr) <= MAX_COMMAND_OUTPUT_BYTES,
        "raw_stdout_persisted": False,
        "raw_stderr_persisted": False,
    }


def _docker_snapshot(runner: CommandRunner, docker: str, label: str) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    raw: dict[str, subprocess.CompletedProcess[bytes] | None] = {}
    for role, mode, command in _docker_commands(docker):
        _validate_docker_argv(command, docker)
        try:
            result = runner.run(
                command,
                environment=_docker_environment(daemon=mode == "daemon"),
                timeout_seconds=30,
            )
        except (OSError, subprocess.SubprocessError):
            result = None
        if result is None:
            rows.append(
                {
                    "role": role,
                    "argv_contract": ["<exact-docker-cli>", *command[1:]],
                    "invocation_error_code": "COMMAND_INVOCATION_FAILED",
                    "raw_stdout_persisted": False,
                    "raw_stderr_persisted": False,
                }
            )
        else:
            rows.append(_summary(role, command, result))
        raw[role] = result

    def exact_text(role: str) -> str | None:
        result = raw[role]
        if result is None or result.returncode != 0 or result.stderr:
            return None
        if len(result.stdout) > MAX_COMMAND_OUTPUT_BYTES:
            return None
        try:
            return result.stdout.decode("utf-8").rstrip("\r\n")
        except UnicodeDecodeError:
            return None

    cli_raw = exact_text("cli-version")
    cli_match = re.fullmatch(
        r"Docker version ([0-9]+\.[0-9]+\.[0-9]+), build ([0-9A-Za-z._-]+)",
        cli_raw or "",
    )
    cli_projection = (
        {"version": cli_match.group(1), "build": cli_match.group(2)} if cli_match else None
    )
    context_projection = (
        LOCAL_DOCKER_CONTEXT if exact_text("context-show") == LOCAL_DOCKER_CONTEXT else None
    )
    endpoint_raw = exact_text("context-endpoint")
    try:
        endpoint_candidate = json.loads(endpoint_raw) if endpoint_raw is not None else None
    except json.JSONDecodeError:
        endpoint_candidate = None
    endpoint_projection = (
        LOCAL_DOCKER_ENDPOINT if endpoint_candidate == LOCAL_DOCKER_ENDPOINT else None
    )
    daemon_raw = exact_text("daemon-version")
    try:
        daemon_candidate = json.loads(daemon_raw) if daemon_raw is not None else None
    except json.JSONDecodeError:
        daemon_candidate = None
    daemon = None
    if (
        isinstance(daemon_candidate, dict)
        and tuple(daemon_candidate) == ("ClientVersion", "ServerVersion", "ServerOs", "ServerArch")
        and re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", daemon_candidate["ClientVersion"] or "")
        and re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", daemon_candidate["ServerVersion"] or "")
        and str(daemon_candidate["ServerOs"]).casefold() == "linux"
        and re.fullmatch(r"[0-9A-Za-z._-]+", daemon_candidate["ServerArch"] or "")
    ):
        daemon = {
            "ClientVersion": daemon_candidate["ClientVersion"],
            "ServerVersion": daemon_candidate["ServerVersion"],
            "ServerOs": "linux",
            "ServerArch": daemon_candidate["ServerArch"],
        }
    expected_ids = {
        "image-moto": "sha256:" + DOCKER_IMAGES[0].rsplit("sha256:", 1)[1],
        "image-babel": "sha256:" + DOCKER_IMAGES[1].rsplit("sha256:", 1)[1],
    }
    image_ids = {
        role: expected if exact_text(role) == expected else None
        for role, expected in expected_ids.items()
    }
    projection = {
        "cli_version": cli_projection,
        "context": context_projection,
        "context_endpoint": endpoint_projection,
        "daemon": daemon,
        "image_ids": image_ids,
    }
    checks = {
        "cli_version_observed": cli_projection is not None,
        "context_is_desktop_linux": context_projection == LOCAL_DOCKER_CONTEXT,
        "context_endpoint_is_local_named_pipe": endpoint_projection == LOCAL_DOCKER_ENDPOINT,
        "daemon_projection_available": daemon is not None,
        "moto_image_identity_matches": image_ids["image-moto"] == expected_ids["image-moto"],
        "babel_image_identity_matches": image_ids["image-babel"] == expected_ids["image-babel"],
        "every_output_within_bound": all(
            row.get("stdout_within_bound") is True and row.get("stderr_within_bound") is True
            for row in rows
            if "return_code" in row
        )
        and all("return_code" in row for row in rows),
    }
    return {
        "snapshot": label,
        "commands": rows,
        "command_count": len(rows),
        "config_read_calls": 3,
        "read_only_daemon_calls": 3,
        "workload_or_mutating_calls": 0,
        "forced_daemon_endpoint": LOCAL_DOCKER_ENDPOINT,
        "observed_projection": projection,
        "checks": checks,
        "passed": all(checks.values()),
    }


def _docker_observation(runner: CommandRunner) -> dict[str, Any]:
    _require(not os.environ.get("PATCHLOOP_DOCKER_CLI"), "D-126 Docker CLI override is forbidden")
    path = _docker_cli_path()
    before_cli = _external_file_binding(path, label="Docker CLI")
    _require(before_cli["file_name"].casefold() == "docker.exe", "D-126 Docker CLI name differs")
    resolved = str(path.resolve(strict=True))
    before = _docker_snapshot(runner, resolved, "before")
    after = _docker_snapshot(runner, resolved, "after")
    after_cli = _external_file_binding(path, label="Docker CLI")
    stable = before_cli == after_cli
    before_normalized = {key: value for key, value in before.items() if key != "snapshot"}
    after_normalized = {key: value for key, value in after.items() if key != "snapshot"}
    snapshots_stable = canonical_json(before_normalized) == canonical_json(after_normalized)
    return {
        "docker_cli_before": before_cli,
        "docker_cli_after": after_cli,
        "docker_cli_stable": stable,
        "parent_docker_prefixed_environment_value_persisted": False,
        "child_environment_contract": {
            "remove_every_case_insensitive_docker_prefixed_variable": True,
            "minimal_nonsecret_environment_allowlist": [
                "SYSTEMROOT",
                "WINDIR",
                "USERPROFILE",
                "APPDATA",
                "LOCALAPPDATA",
                "TEMP",
                "TMP",
            ],
            "openai_proxy_tls_and_other_parent_environment_inherited": False,
            "force_daemon_host": LOCAL_DOCKER_ENDPOINT,
            "shell": False,
        },
        "snapshots": [before, after],
        "normalized_snapshots_stable": snapshots_stable,
        "total_command_count": before["command_count"] + after["command_count"],
        "read_only_daemon_call_count": before["read_only_daemon_calls"]
        + after["read_only_daemon_calls"],
        "docker_workload_or_mutating_call_count": 0,
        "passed": stable and snapshots_stable and before["passed"] and after["passed"],
    }


def _locked_openai_version(root: Path) -> str | None:
    text = _stable_read(root, Path("uv.lock")).decode("utf-8")
    match = re.search(r'\[\[package\]\]\s+name = "openai"\s+version = "([^"]+)"', text)
    return match.group(1) if match else None


def _production_openai_factory_contract(root: Path) -> dict[str, bool]:
    source = _stable_read(root, Path("patchloop/agent/model.py")).decode("utf-8")
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise D126PreflightError("D-126 production model source cannot be parsed") from exc
    calls: list[ast.Call] = []
    for node in tree.body:
        if not isinstance(node, ast.ClassDef) or node.name != "OpenAIResponsesAdapter":
            continue
        for member in node.body:
            if not isinstance(member, ast.FunctionDef) or member.name != "__init__":
                continue
            for candidate in ast.walk(member):
                if (
                    isinstance(candidate, ast.Call)
                    and isinstance(candidate.func, ast.Name)
                    and candidate.func.id == "OpenAI"
                ):
                    calls.append(candidate)
    explicit_base = bool(calls)
    trust_env_false = bool(calls)
    for call in calls:
        keywords = {item.arg: item.value for item in call.keywords if item.arg is not None}
        base = keywords.get("base_url")
        explicit_base = (
            explicit_base and isinstance(base, ast.Name) and base.id == "OFFICIAL_API_BASE_URL"
        )
        http_client = keywords.get("http_client")
        if not isinstance(http_client, ast.Call):
            trust_env_false = False
            continue
        client_keywords = {
            item.arg: item.value for item in http_client.keywords if item.arg is not None
        }
        trust = client_keywords.get("trust_env")
        trust_env_false = (
            trust_env_false and isinstance(trust, ast.Constant) and trust.value is False
        )
    return {
        "explicit_official_base_url": explicit_base,
        "trust_env_false": trust_env_false,
    }


def _synthetic_openai_client_probe(installed: str | None) -> bool:
    if installed is None:
        return False
    try:
        import httpx
        from openai import OpenAI

        client = OpenAI(
            api_key="d126-nonsecret-placeholder",
            base_url=OFFICIAL_API_BASE_URL,
            max_retries=0,
            http_client=httpx.Client(trust_env=False),
        )
        passed = (
            str(client.base_url).rstrip("/") == OFFICIAL_API_BASE_URL and client.max_retries == 0
        )
        client.close()
        return passed
    except Exception:
        return False


def _sdk_observation(root: Path) -> dict[str, Any]:
    try:
        installed = importlib.metadata.version("openai")
    except importlib.metadata.PackageNotFoundError:
        installed = None
    locked = _locked_openai_version(root)
    presence = {name: bool(os.environ.get(name)) for name in SENSITIVE_ENV_NAMES}
    production_factory = _production_openai_factory_contract(root)
    synthetic_passed = _synthetic_openai_client_probe(installed)
    python_binding = _external_file_binding(Path(sys.executable), label="Python executable")
    checks = {
        "python_is_repository_venv": Path(sys.executable).resolve().is_relative_to(root / ".venv"),
        "openai_sdk_installed": installed is not None,
        "openai_sdk_matches_lock": installed is not None and installed == locked,
        "api_key_present": presence["OPENAI_API_KEY"],
        "alternate_openai_or_proxy_tls_environment_absent": not any(
            presence[name] for name in FORBIDDEN_ROUTING_ENV_NAMES
        ),
        "synthetic_explicit_official_endpoint_no_call_probe_passed": synthetic_passed,
        "production_client_factory_explicit_official_base_url": production_factory[
            "explicit_official_base_url"
        ],
        "production_client_factory_trust_env_false": production_factory["trust_env_false"],
    }
    return {
        "python": {
            "version": ".".join(str(value) for value in sys.version_info[:3]),
            **python_binding,
        },
        "openai_sdk": {"installed_version": installed, "locked_version": locked},
        "credential": {
            "name": "OPENAI_API_KEY",
            "present": presence["OPENAI_API_KEY"],
            "value_hash_length_or_prefix_persisted": False,
            "identity_continuity_claimed": False,
        },
        "routing_environment_presence": presence,
        "routing_environment_values_persisted": False,
        "official_endpoint": OFFICIAL_API_BASE_URL,
        "network_call_count": 0,
        "checks": checks,
        "passed": all(checks.values()),
    }


def _blockers(docker: dict[str, Any], sdk: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if not docker.get("passed"):
        blockers.append("docker-local-daemon-and-exact-images-readiness-failed")
    blockers.append("docker-cli-observed-identity-awaits-separate-exact-approval")
    checks = sdk["checks"]
    if not checks["python_is_repository_venv"]:
        blockers.append("python-interpreter-is-not-the-repository-venv")
    if not checks["openai_sdk_installed"]:
        blockers.append("openai-sdk-is-not-installed")
    if not checks["api_key_present"]:
        blockers.append("openai-api-key-presence-missing")
    if not checks["openai_sdk_matches_lock"]:
        blockers.append("openai-sdk-lock-binding-failed")
    if not checks["alternate_openai_or_proxy_tls_environment_absent"]:
        blockers.append("alternate-openai-proxy-or-tls-routing-environment-present")
    if not checks["synthetic_explicit_official_endpoint_no_call_probe_passed"]:
        blockers.append("openai-sdk-explicit-endpoint-no-call-probe-failed")
    if not checks["production_client_factory_explicit_official_base_url"]:
        blockers.append("production-openai-client-official-base-url-not-explicit")
    if not checks["production_client_factory_trust_env_false"]:
        blockers.append("production-openai-client-trust-env-not-disabled")
    return sorted(set(blockers))


def _preflight_body(
    *,
    receipt_binding: dict[str, Any],
    receipt_recorded_at: str,
    source: dict[str, Any],
    pricing: dict[str, Any],
    docker: dict[str, Any],
    sdk: dict[str, Any],
    recorded_at: str,
) -> dict[str, Any]:
    receipt = _parse_time(receipt_recorded_at, label="receipt recorded_at")
    recorded = _parse_time(recorded_at, label="preflight recorded_at")
    observed = _parse_time(pricing["observed_at"], label="pricing observed_at")
    _require(receipt <= observed <= recorded, "D-126 preflight chronology differs")
    _require((recorded - observed).total_seconds() <= FRESHNESS_SECONDS, "D-126 pricing is stale")
    blockers = _blockers(docker, sdk)
    status = READY_STATUS if not blockers else BLOCKED_STATUS
    return {
        "milestone": MILESTONE,
        "evidence_kind": "clean-source-official-pricing-and-no-call-environment-observation",
        "recorded_at": recorded_at,
        "status": status,
        "observer_contract": {
            "pricing_fetcher_kind": "official-docs-public-https-no-proxy-no-auth-v1",
            "docker_runner_kind": "subprocess-exact-read-only-argv-minimal-env-no-shell-v1",
            "sdk_observer_kind": "local-metadata-ast-and-synthetic-client-no-call-v1",
            "public_api_observer_injection_supported": False,
        },
        "receipt_binding": receipt_binding,
        "source_commit_observation": source,
        "official_pricing_observation": pricing,
        "docker_observation": docker,
        "sdk_credential_endpoint_observation": sdk,
        "observed_blockers": blockers,
        "authority": {
            "approved_work_item_6_observations_completed": True,
            "environment_ready_for_execution_hash": not blockers,
            "execution_hash_created": False,
            "execution_authorization_candidate_created": False,
            "provider_calls_made": 0,
            "evaluator_calls_made": 0,
            "agent_runs_started": 0,
            "runtime_memory_injection_count": 0,
            "retrieval_call_count": 0,
            "docker_workload_or_mutating_call_count": 0,
            "cost_reserved_or_spent_usd": "0",
        },
        "evidence_boundary": {
            "pricing_public_network_get_count": pricing["public_get_request_count"],
            "docker_calls_are_read_only_cli_context_daemon_and_image_inspection": True,
            "docker_raw_output_not_persisted_but_size_and_sha256_digest_are_persisted": True,
            "sdk_probe_is_local_construction_without_endpoint_call": True,
            "credential_value_hash_length_prefix_or_identity_not_recorded": True,
            "ignored_scratch_and_external_worktrees_not_attested": True,
            "noncooperative_docker_executable_or_path_swap_verified": False,
            "bounded_streaming_http_and_subprocess_output_capture_verified": False,
            "later_candidate_must_repeat_freshness_and_environment_checks": True,
            "runtime_or_global_network_instrumentation_claimed": False,
        },
    }


def _gate_body(root: Path, preflight: dict[str, Any], recorded_at: str) -> dict[str, Any]:
    body = preflight["semantic_body"]
    preflight_time = _parse_time(body["recorded_at"], label="preflight recorded_at")
    gate_time = _parse_time(recorded_at, label="gate recorded_at")
    _require(preflight_time <= gate_time, "D-126 gate chronology differs")
    observed_time = _parse_time(
        body["official_pricing_observation"]["observed_at"],
        label="pricing observed_at",
    )
    _require(
        0 <= (gate_time - observed_time).total_seconds() <= FRESHNESS_SECONDS,
        "D-126 pricing is not fresh at gate creation",
    )
    blockers = body["observed_blockers"]
    ready = not blockers
    return {
        "milestone": MILESTONE,
        "evidence_kind": "derived-clean-source-pricing-no-call-preflight-gate",
        "recorded_at": recorded_at,
        "status": READY_STATUS if ready else BLOCKED_STATUS,
        "receipt_binding": _binding(root, RECEIPT_PATH),
        "preflight_binding": _binding(root, PREFLIGHT_PATH),
        "qualification": {
            "source_commit_sealed": True,
            "official_pricing_observed_within_72_hours": True,
            "no_call_environment_observation_completed": True,
            "environment_ready_for_execution_hash": ready,
            "observed_blockers": blockers,
        },
        "authority": {
            "d125_next_gate_approval_consumed": True,
            "approved_work_item_6_complete": True,
            "execution_hash_authorized_or_created": False,
            "execution_candidate_authorized_or_created": False,
            "provider_evaluator_agent_execution_authorized": False,
            "runtime_memory_or_retrieval_authorized": False,
            "docker_workload_authorized": False,
            "cost_reservation_or_spend_authorized": False,
        },
        "next_gate": {
            "if_blocked": (
                "resolve-every-observed-blocker-and-repeat-an-exact-separately-"
                "authorized-no-call-preflight"
            ),
            "if_ready": (
                "request-separate-exact-d126-gate-approval-before-execution-hash-"
                "or-candidate-preparation"
            ),
            "does_not_authorize_execution_hash_candidate_or_live_run": True,
        },
        "evidence_boundary": {
            "qualification_grade": (
                "local-clean-source-public-pricing-and-read-only-no-call-observation"
            ),
            "live_result_present": False,
            "memory_benefit_or_core_readiness_claimed": False,
            "candidate_must_recheck_environment_and_pricing": True,
        },
    }


def _validate_source_observation(source: Any) -> None:
    _require(isinstance(source, dict), "D-126 source observation is not an object")
    expected_keys = (
        "commit",
        "tree",
        "parent",
        "branch",
        "tracked_tree_listing_sha256",
        "worktree_clean_before_observation",
        "index_clean_before_observation",
        "scope",
        "ignored_or_external_worktrees_claimed_clean",
    )
    _require(tuple(source) == expected_keys, "D-126 source observation fields differ")
    hex40 = re.compile(r"[0-9a-f]{40}\Z")
    _require(
        all(
            isinstance(source[key], str) and hex40.fullmatch(source[key])
            for key in ("commit", "tree", "parent")
        ),
        "D-126 Git identity differs",
    )
    _require(
        isinstance(source["tracked_tree_listing_sha256"], str)
        and re.fullmatch(r"sha256:[0-9a-f]{64}", source["tracked_tree_listing_sha256"]) is not None,
        "D-126 tracked tree hash differs",
    )
    _require(source["worktree_clean_before_observation"] is True, "D-126 worktree claim differs")
    _require(source["index_clean_before_observation"] is True, "D-126 index claim differs")
    _require(source["scope"] == "current-main-worktree-commit-tree-only", "D-126 Git scope differs")
    _require(
        source["ignored_or_external_worktrees_claimed_clean"] is False,
        "D-126 Git scope overclaims",
    )


def _expected_pricing_facts() -> dict[str, Any]:
    return {
        "model_label": MODEL_LABEL,
        "dated_model_id": MODEL_ID,
        "service_tier": "default-standard",
        "unit": "usd-per-1m-text-tokens",
        "input_usd": str(INPUT_RATE),
        "cached_input_usd": str(CACHED_INPUT_RATE),
        "cache_write_input_usd": None,
        "output_usd": str(OUTPUT_RATE),
        "responses_endpoint_supported": True,
    }


def _expected_pricing_math() -> dict[str, Any]:
    return {
        "max_total_tokens": MAX_TOTAL_TOKENS,
        "max_output_tokens": MAX_OUTPUT_TOKENS,
        "conservative_worst_rate_usd_per_million": str(OUTPUT_RATE),
        "per_row_reserve_usd": str(PER_ROW_RESERVE),
        "scheduled_rows": SCHEDULED_ROWS,
        "full_schedule_reserve_usd": str(FULL_RESERVE),
        "hard_cap_usd": str(HARD_CAP),
        "per_row_reserve_nanos": 13_612_500_000,
        "full_schedule_reserve_nanos": 54_450_000_000,
        "hard_cap_nanos": 55_000_000_000,
    }


def _validate_pricing_observation(pricing: Any) -> None:
    _require(isinstance(pricing, dict), "D-126 pricing observation is not an object")
    expected_keys = (
        "observed_at",
        "source_url",
        "pricing_index_url",
        "final_url",
        "official_host",
        "http_status",
        "content_type",
        "etag",
        "redirect_count",
        "public_get_request_count",
        "public_body_bytes",
        "public_body_sha256",
        "source_evidence_lines",
        "source_evidence_sha256",
        "facts",
        "facts_sha256",
        "planning_math",
        "freshness_window_seconds",
        "fresh_at_capture",
        "request_auth_or_cookie_sent",
        "proxy_use_disabled_by_fetcher",
        "raw_body_persisted",
    )
    _require(tuple(pricing) == expected_keys, "D-126 pricing observation fields differ")
    _parse_time(pricing["observed_at"], label="pricing observed_at")
    _require(pricing["source_url"] == OFFICIAL_MODEL_PAGE_URL, "D-126 pricing source differs")
    _require(
        pricing["pricing_index_url"] == OFFICIAL_PRICING_PAGE_URL, "D-126 pricing index differs"
    )
    _require(pricing["final_url"] == OFFICIAL_MODEL_PAGE_URL, "D-126 pricing final URL differs")
    _require(pricing["official_host"] == "developers.openai.com", "D-126 pricing host differs")
    _require(
        type(pricing["http_status"]) is int and pricing["http_status"] == 200,
        "D-126 pricing status differs",
    )
    _require(
        isinstance(pricing["content_type"], str)
        and pricing["content_type"].lower().startswith("text/markdown"),
        "D-126 pricing content type differs",
    )
    _require(
        pricing["etag"] is None or isinstance(pricing["etag"], str), "D-126 pricing ETag differs"
    )
    _require(
        type(pricing["redirect_count"]) is int and 0 <= pricing["redirect_count"] <= 3,
        "D-126 redirect count differs",
    )
    _require(
        pricing["public_get_request_count"] == pricing["redirect_count"] + 1,
        "D-126 public GET count differs",
    )
    _require(
        type(pricing["public_body_bytes"]) is int
        and 0 < pricing["public_body_bytes"] <= MAX_HTTP_BODY_BYTES,
        "D-126 pricing body size differs",
    )
    _require(
        isinstance(pricing["public_body_sha256"], str)
        and re.fullmatch(r"sha256:[0-9a-f]{64}", pricing["public_body_sha256"]) is not None,
        "D-126 pricing body hash differs",
    )
    expected_lines = [
        f"Default snapshot: `{MODEL_ID}`",
        "| Input | $0.75 | 1M tokens |",
        "| Cached input | $0.075 | 1M tokens |",
        "| Output | $4.5 | 1M tokens |",
        "| Responses | `v1/responses` | Supported |",
        "| GPT-5.4 mini | $0.75 | $0.075 | $4.5 |",
    ]
    _require(pricing["source_evidence_lines"] == expected_lines, "D-126 pricing evidence differs")
    _require(
        pricing["source_evidence_sha256"] == sha256_text(canonical_json(expected_lines)),
        "D-126 pricing evidence hash differs",
    )
    facts = _expected_pricing_facts()
    _require(
        canonical_json(pricing["facts"]) == canonical_json(facts), "D-126 pricing facts differ"
    )
    _require(
        pricing["facts_sha256"] == sha256_text(canonical_json(facts)),
        "D-126 pricing facts hash differs",
    )
    _require(
        canonical_json(pricing["planning_math"]) == canonical_json(_expected_pricing_math()),
        "D-126 pricing math differs",
    )
    _require(pricing["freshness_window_seconds"] == FRESHNESS_SECONDS, "D-126 freshness differs")
    _require(pricing["fresh_at_capture"] is True, "D-126 freshness claim differs")
    _require(pricing["request_auth_or_cookie_sent"] is False, "D-126 request authority differs")
    _require(pricing["proxy_use_disabled_by_fetcher"] is True, "D-126 proxy boundary differs")
    _require(pricing["raw_body_persisted"] is False, "D-126 raw body boundary differs")


def _validate_docker_observation(docker: Any) -> None:
    _require(isinstance(docker, dict), "D-126 Docker observation is not an object")
    expected_keys = (
        "docker_cli_before",
        "docker_cli_after",
        "docker_cli_stable",
        "parent_docker_prefixed_environment_value_persisted",
        "child_environment_contract",
        "snapshots",
        "normalized_snapshots_stable",
        "total_command_count",
        "read_only_daemon_call_count",
        "docker_workload_or_mutating_call_count",
        "passed",
    )
    _require(tuple(docker) == expected_keys, "D-126 Docker observation fields differ")
    binding_keys = ("file_name", "file_bytes", "file_sha256", "linklike")
    for key in ("docker_cli_before", "docker_cli_after"):
        item = docker[key]
        _require(isinstance(item, dict) and tuple(item) == binding_keys, "D-126 CLI fields differ")
        _require(item["file_name"].casefold() == "docker.exe", "D-126 CLI name differs")
        _require(
            type(item["file_bytes"]) is int and item["file_bytes"] > 0, "D-126 CLI size differs"
        )
        _require(
            isinstance(item["file_sha256"], str)
            and re.fullmatch(r"sha256:[0-9a-f]{64}", item["file_sha256"]) is not None,
            "D-126 CLI hash differs",
        )
        _require(item["linklike"] is False, "D-126 CLI link claim differs")
    stable = docker["docker_cli_before"] == docker["docker_cli_after"]
    _require(docker["docker_cli_stable"] is stable, "D-126 CLI stability differs")
    _require(
        docker["parent_docker_prefixed_environment_value_persisted"] is False,
        "D-126 Docker environment persistence differs",
    )
    _require(
        docker["child_environment_contract"]
        == {
            "remove_every_case_insensitive_docker_prefixed_variable": True,
            "minimal_nonsecret_environment_allowlist": [
                "SYSTEMROOT",
                "WINDIR",
                "USERPROFILE",
                "APPDATA",
                "LOCALAPPDATA",
                "TEMP",
                "TMP",
            ],
            "openai_proxy_tls_and_other_parent_environment_inherited": False,
            "force_daemon_host": LOCAL_DOCKER_ENDPOINT,
            "shell": False,
        },
        "D-126 Docker child environment differs",
    )
    snapshots = docker["snapshots"]
    _require(isinstance(snapshots, list) and len(snapshots) == 2, "D-126 snapshots differ")
    expected_commands = _docker_commands("<exact-docker-cli>")
    expected_roles = [item[0] for item in expected_commands]
    expected_argv = {
        role: ["<exact-docker-cli>", *command[1:]] for role, _, command in expected_commands
    }
    for index, snapshot in enumerate(snapshots):
        snapshot_keys = (
            "snapshot",
            "commands",
            "command_count",
            "config_read_calls",
            "read_only_daemon_calls",
            "workload_or_mutating_calls",
            "forced_daemon_endpoint",
            "observed_projection",
            "checks",
            "passed",
        )
        _require(
            isinstance(snapshot, dict) and tuple(snapshot) == snapshot_keys,
            "D-126 snapshot fields differ",
        )
        _require(
            snapshot["snapshot"] == ("before" if index == 0 else "after"),
            "D-126 snapshot order differs",
        )
        rows = snapshot["commands"]
        _require(
            [row.get("role") for row in rows] == expected_roles, "D-126 transcript roles differ"
        )
        for row in rows:
            _require(row.get("argv_contract") == expected_argv[row["role"]], "D-126 argv differs")
            if "return_code" in row:
                success_keys = (
                    "role",
                    "argv_contract",
                    "return_code",
                    "stdout_bytes",
                    "stdout_sha256",
                    "stderr_bytes",
                    "stderr_sha256",
                    "stdout_within_bound",
                    "stderr_within_bound",
                    "raw_stdout_persisted",
                    "raw_stderr_persisted",
                )
                _require(tuple(row) == success_keys, "D-126 transcript fields differ")
                _require(type(row["return_code"]) is int, "D-126 return code differs")
                for size_key in ("stdout_bytes", "stderr_bytes"):
                    _require(
                        type(row[size_key]) is int and row[size_key] >= 0,
                        "D-126 output size differs",
                    )
                for hash_key in ("stdout_sha256", "stderr_sha256"):
                    _require(
                        isinstance(row[hash_key], str)
                        and re.fullmatch(r"sha256:[0-9a-f]{64}", row[hash_key]) is not None,
                        "D-126 output hash differs",
                    )
                _require(
                    row["raw_stdout_persisted"] is False and row["raw_stderr_persisted"] is False,
                    "D-126 raw Docker output boundary differs",
                )
            else:
                error_keys = (
                    "role",
                    "argv_contract",
                    "invocation_error_code",
                    "raw_stdout_persisted",
                    "raw_stderr_persisted",
                )
                _require(tuple(row) == error_keys, "D-126 invocation-error fields differ")
                _require(
                    row["invocation_error_code"] == "COMMAND_INVOCATION_FAILED",
                    "D-126 invocation error differs",
                )
        projection = snapshot["observed_projection"]
        projection_keys = ("cli_version", "context", "context_endpoint", "daemon", "image_ids")
        _require(
            isinstance(projection, dict) and tuple(projection) == projection_keys,
            "D-126 projection fields differ",
        )
        _require(
            tuple(projection["image_ids"]) == ("image-moto", "image-babel"),
            "D-126 image projection differs",
        )
        cli_projection = projection["cli_version"]
        cli_ok = (
            isinstance(cli_projection, dict)
            and tuple(cli_projection) == ("version", "build")
            and re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", cli_projection["version"] or "") is not None
            and re.fullmatch(r"[0-9A-Za-z._-]+", cli_projection["build"] or "") is not None
        )
        daemon = projection["daemon"]
        daemon_ok = (
            isinstance(daemon, dict)
            and tuple(daemon) == ("ClientVersion", "ServerVersion", "ServerOs", "ServerArch")
            and re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", daemon["ClientVersion"] or "") is not None
            and re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", daemon["ServerVersion"] or "") is not None
            and daemon["ServerOs"] == "linux"
            and re.fullmatch(r"[0-9A-Za-z._-]+", daemon["ServerArch"] or "") is not None
        )
        expected_checks = {
            "cli_version_observed": cli_ok,
            "context_is_desktop_linux": projection["context"] == LOCAL_DOCKER_CONTEXT,
            "context_endpoint_is_local_named_pipe": (
                projection["context_endpoint"] == LOCAL_DOCKER_ENDPOINT
            ),
            "daemon_projection_available": daemon_ok,
            "moto_image_identity_matches": projection["image_ids"]["image-moto"]
            == "sha256:" + DOCKER_IMAGES[0].rsplit("sha256:", 1)[1],
            "babel_image_identity_matches": projection["image_ids"]["image-babel"]
            == "sha256:" + DOCKER_IMAGES[1].rsplit("sha256:", 1)[1],
            "every_output_within_bound": all(
                "return_code" in row
                and row["stdout_within_bound"] is True
                and row["stderr_within_bound"] is True
                for row in rows
            ),
        }
        _require(
            canonical_json(snapshot["checks"]) == canonical_json(expected_checks),
            "D-126 Docker checks differ",
        )
        _require(
            snapshot["passed"] is all(expected_checks.values()), "D-126 snapshot result differs"
        )
        _require(snapshot["command_count"] == 6, "D-126 command count differs")
        _require(snapshot["config_read_calls"] == 3, "D-126 config count differs")
        _require(snapshot["read_only_daemon_calls"] == 3, "D-126 daemon count differs")
        _require(snapshot["workload_or_mutating_calls"] == 0, "D-126 workload count differs")
        _require(
            snapshot["forced_daemon_endpoint"] == LOCAL_DOCKER_ENDPOINT, "D-126 endpoint differs"
        )
    before_normalized = {key: value for key, value in snapshots[0].items() if key != "snapshot"}
    after_normalized = {key: value for key, value in snapshots[1].items() if key != "snapshot"}
    snapshots_stable = canonical_json(before_normalized) == canonical_json(after_normalized)
    _require(
        docker["normalized_snapshots_stable"] is snapshots_stable,
        "D-126 Docker snapshot stability differs",
    )
    expected_pass = (
        stable and snapshots_stable and snapshots[0]["passed"] and snapshots[1]["passed"]
    )
    _require(docker["passed"] is expected_pass, "D-126 Docker result differs")
    _require(docker["total_command_count"] == 12, "D-126 total command count differs")
    _require(docker["read_only_daemon_call_count"] == 6, "D-126 daemon call count differs")
    _require(docker["docker_workload_or_mutating_call_count"] == 0, "D-126 workload count differs")


def _validate_sdk_observation(root: Path, sdk: Any) -> None:
    _require(isinstance(sdk, dict), "D-126 SDK observation is not an object")
    expected_keys = (
        "python",
        "openai_sdk",
        "credential",
        "routing_environment_presence",
        "routing_environment_values_persisted",
        "official_endpoint",
        "network_call_count",
        "checks",
        "passed",
    )
    _require(tuple(sdk) == expected_keys, "D-126 SDK observation fields differ")
    _require(
        tuple(sdk["python"]) == ("version", "file_name", "file_bytes", "file_sha256", "linklike"),
        "D-126 Python binding fields differ",
    )
    _require(
        tuple(sdk["openai_sdk"]) == ("installed_version", "locked_version"),
        "D-126 SDK binding fields differ",
    )
    current_python = {
        "version": ".".join(str(value) for value in sys.version_info[:3]),
        **_external_file_binding(Path(sys.executable), label="Python executable"),
    }
    _require(
        canonical_json(sdk["python"]) == canonical_json(current_python),
        "D-126 Python binding differs",
    )
    try:
        current_installed = importlib.metadata.version("openai")
    except importlib.metadata.PackageNotFoundError:
        current_installed = None
    current_sdk = {
        "installed_version": current_installed,
        "locked_version": _locked_openai_version(root),
    }
    _require(
        canonical_json(sdk["openai_sdk"]) == canonical_json(current_sdk),
        "D-126 SDK binding differs",
    )
    presence = sdk["routing_environment_presence"]
    _require(
        isinstance(presence, dict) and tuple(presence) == SENSITIVE_ENV_NAMES,
        "D-126 routing fields differ",
    )
    _require(all(type(value) is bool for value in presence.values()), "D-126 routing types differ")
    current_presence = {name: bool(os.environ.get(name)) for name in SENSITIVE_ENV_NAMES}
    _require(
        canonical_json(presence) == canonical_json(current_presence),
        "D-126 routing environment changed",
    )
    expected_credential = {
        "name": "OPENAI_API_KEY",
        "present": presence["OPENAI_API_KEY"],
        "value_hash_length_or_prefix_persisted": False,
        "identity_continuity_claimed": False,
    }
    _require(sdk["credential"] == expected_credential, "D-126 credential boundary differs")
    _require(sdk["routing_environment_values_persisted"] is False, "D-126 routing boundary differs")
    _require(sdk["official_endpoint"] == OFFICIAL_API_BASE_URL, "D-126 official endpoint differs")
    _require(sdk["network_call_count"] == 0, "D-126 SDK network count differs")
    checks = sdk["checks"]
    expected_check_keys = (
        "python_is_repository_venv",
        "openai_sdk_installed",
        "openai_sdk_matches_lock",
        "api_key_present",
        "alternate_openai_or_proxy_tls_environment_absent",
        "synthetic_explicit_official_endpoint_no_call_probe_passed",
        "production_client_factory_explicit_official_base_url",
        "production_client_factory_trust_env_false",
    )
    _require(tuple(checks) == expected_check_keys, "D-126 SDK check fields differ")
    production_factory = _production_openai_factory_contract(root)
    expected_checks = {
        "python_is_repository_venv": Path(sys.executable).resolve().is_relative_to(root / ".venv"),
        "openai_sdk_installed": sdk["openai_sdk"]["installed_version"] is not None,
        "openai_sdk_matches_lock": sdk["openai_sdk"]["installed_version"] is not None
        and sdk["openai_sdk"]["installed_version"] == sdk["openai_sdk"]["locked_version"],
        "api_key_present": presence["OPENAI_API_KEY"],
        "alternate_openai_or_proxy_tls_environment_absent": not any(
            presence[name] for name in FORBIDDEN_ROUTING_ENV_NAMES
        ),
        "synthetic_explicit_official_endpoint_no_call_probe_passed": (
            _synthetic_openai_client_probe(current_installed)
        ),
        "production_client_factory_explicit_official_base_url": (
            production_factory["explicit_official_base_url"]
        ),
        "production_client_factory_trust_env_false": production_factory["trust_env_false"],
    }
    _require(canonical_json(checks) == canonical_json(expected_checks), "D-126 SDK checks differ")
    _require(sdk["passed"] is all(checks.values()), "D-126 SDK result differs")


def _validate_preflight(root: Path) -> dict[str, Any]:
    receipt = _validate_receipt(root)
    payload = _load_envelope(root, PREFLIGHT_PATH, schema=PREFLIGHT_SCHEMA, prefix="d126preflight_")
    body = payload["semantic_body"]
    _require(tuple(body) == PREFLIGHT_BODY_KEYS, "D-126 preflight body fields differ")
    _require(
        body["receipt_binding"] == _binding(root, RECEIPT_PATH), "D-126 receipt binding differs"
    )
    _require(
        body["receipt_binding"]["artifact_id"] == receipt["artifact_id"], "D-126 receipt ID differs"
    )
    _validate_source_observation(body["source_commit_observation"])
    _validate_pricing_observation(body["official_pricing_observation"])
    _validate_docker_observation(body["docker_observation"])
    _validate_sdk_observation(root, body["sdk_credential_endpoint_observation"])
    _require(isinstance(body["observed_blockers"], list), "D-126 blocker list differs")
    _require(
        body["observed_blockers"] == sorted(set(body["observed_blockers"])), "D-126 blockers differ"
    )
    _require(
        body["observed_blockers"]
        == _blockers(body["docker_observation"], body["sdk_credential_endpoint_observation"]),
        "D-126 derived blockers differ",
    )
    expected_status = READY_STATUS if not body["observed_blockers"] else BLOCKED_STATUS
    _require(body["status"] == expected_status, "D-126 preflight status differs")
    receipt_time = _parse_time(receipt["semantic_body"]["recorded_at"], label="receipt recorded_at")
    observed_time = _parse_time(
        body["official_pricing_observation"]["observed_at"], label="pricing observed_at"
    )
    preflight_time = _parse_time(body["recorded_at"], label="preflight recorded_at")
    _require(receipt_time <= observed_time <= preflight_time, "D-126 preflight chronology differs")
    pricing = body["official_pricing_observation"]
    _require(pricing["facts"]["dated_model_id"] == MODEL_ID, "D-126 pricing model differs")
    _require(
        pricing["facts_sha256"] == sha256_text(canonical_json(pricing["facts"])),
        "D-126 pricing facts hash differs",
    )
    _require(
        pricing["planning_math"]["per_row_reserve_nanos"] == 13_612_500_000,
        "D-126 pricing math differs",
    )
    _require(
        pricing["planning_math"]["full_schedule_reserve_nanos"] == 54_450_000_000,
        "D-126 pricing math differs",
    )
    _require(
        pricing["planning_math"]["hard_cap_nanos"] == 55_000_000_000, "D-126 pricing math differs"
    )
    authority = body["authority"]
    _require(authority["execution_hash_created"] is False, "D-126 execution hash authority differs")
    _require(
        authority["execution_authorization_candidate_created"] is False,
        "D-126 candidate authority differs",
    )
    _require(authority["provider_calls_made"] == 0, "D-126 provider count differs")
    _require(
        authority["docker_workload_or_mutating_call_count"] == 0,
        "D-126 Docker workload count differs",
    )
    expected = _preflight_body(
        receipt_binding=_binding(root, RECEIPT_PATH),
        receipt_recorded_at=receipt["semantic_body"]["recorded_at"],
        source=body["source_commit_observation"],
        pricing=body["official_pricing_observation"],
        docker=body["docker_observation"],
        sdk=body["sdk_credential_endpoint_observation"],
        recorded_at=body["recorded_at"],
    )
    _require(canonical_json(body) == canonical_json(expected), "D-126 preflight payload differs")
    return payload


def _validate_gate(root: Path) -> dict[str, Any]:
    preflight = _validate_preflight(root)
    payload = _load_envelope(root, GATE_PATH, schema=GATE_SCHEMA, prefix="d126_")
    body = payload["semantic_body"]
    _require(tuple(body) == GATE_BODY_KEYS, "D-126 gate body fields differ")
    expected = _gate_body(root, preflight, body.get("recorded_at"))
    _require(canonical_json(body) == canonical_json(expected), "D-126 gate payload differs")
    return payload


def run_d126_preflight(
    *,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    root = _repo_root(repository)
    if (root / GATE_PATH).exists():
        return validate_d126_preflight_gate(repository=root)
    receipt = _validate_receipt(root)
    if not (root / PREFLIGHT_PATH).exists():
        source = _git_observation(root)
        sdk = _sdk_observation(root)
        observed_at = _now()
        fetcher = OfficialDocsFetcher()
        command_runner = SubprocessCommandRunner()
        _require(type(fetcher) is OfficialDocsFetcher, "D-126 production fetcher kind differs")
        _require(
            type(command_runner) is SubprocessCommandRunner,
            "D-126 production command runner kind differs",
        )
        pricing = _pricing_observation(fetcher, observed_at)
        docker = _docker_observation(command_runner)
        body = _preflight_body(
            receipt_binding=_binding(root, RECEIPT_PATH),
            receipt_recorded_at=receipt["semantic_body"]["recorded_at"],
            source=source,
            pricing=pricing,
            docker=docker,
            sdk=sdk,
            recorded_at=_now(),
        )
        preflight = _envelope(PREFLIGHT_SCHEMA, "d126preflight_", body)
        _write_new(root, PREFLIGHT_PATH, _pretty_bytes(preflight))
    preflight = _validate_preflight(root)
    gate_body = _gate_body(root, preflight, _now())
    gate = _envelope(GATE_SCHEMA, "d126_", gate_body)
    _write_new(root, GATE_PATH, _pretty_bytes(gate))
    return validate_d126_preflight_gate(repository=root)


def _post_commit_state(root: Path, source: dict[str, Any]) -> dict[str, Any]:
    source_commit = source["commit"]
    _require(
        _run_git(root, "rev-parse", f"{source_commit}^{{tree}}") == source["tree"],
        "D-126 source tree differs",
    )
    _require(
        _run_git(root, "rev-parse", f"{source_commit}^") == source["parent"],
        "D-126 source parent differs",
    )
    source_listing = _run_git(root, "ls-tree", "-r", "--full-tree", source_commit)
    _require(
        sha256_bytes((source_listing + "\n").encode("utf-8"))
        == source["tracked_tree_listing_sha256"],
        "D-126 source tree listing differs",
    )
    head = _run_git(root, "rev-parse", "HEAD")
    parent = _run_git(root, "rev-parse", "HEAD^")
    _require(parent == source_commit, "D-126 evidence commit parent differs")
    status = _run_git(root, "status", "--porcelain", "--untracked-files=all")
    _require(not status, "D-126 post-commit worktree is not clean")
    ancestry = subprocess.run(
        ["git", "merge-base", "--is-ancestor", source_commit, head],
        cwd=root,
        capture_output=True,
        check=False,
        shell=False,
    )
    _require(ancestry.returncode == 0, "D-126 source commit is not an ancestor")
    changed = [
        value
        for value in _run_git(root, "diff", "--name-only", f"{source_commit}..{head}").splitlines()
        if value
    ]
    allowed = {
        PREFLIGHT_PATH.as_posix(),
        GATE_PATH.as_posix(),
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
    _require(set(changed).issubset(allowed), "D-126 evidence commit changed source paths")
    _require(
        {PREFLIGHT_PATH.as_posix(), GATE_PATH.as_posix()}.issubset(changed),
        "D-126 evidence commit is missing preflight artifacts",
    )
    return {"head": head, "source_commit": source_commit, "changed_paths": changed, "clean": True}


def validate_d126_preflight_gate(
    *,
    repository: str | Path | None = None,
    mode: Literal["current-source", "post-evidence-commit"] = "current-source",
) -> dict[str, Any]:
    root = _repo_root(repository)
    gate = _validate_gate(root)
    preflight = _validate_preflight(root)
    body = gate["semantic_body"]
    source = preflight["semantic_body"]["source_commit_observation"]
    post_commit = None
    if mode == "current-source":
        head = _run_git(root, "rev-parse", "HEAD")
        _require(head == source["commit"], "D-126 current source commit differs")
        current_identity = {
            "commit": head,
            "tree": _run_git(root, "rev-parse", "HEAD^{tree}"),
            "parent": _run_git(root, "rev-parse", "HEAD^"),
            "branch": _run_git(root, "branch", "--show-current"),
            "tracked_tree_listing_sha256": sha256_bytes(
                (_run_git(root, "ls-tree", "-r", "--full-tree", "HEAD") + "\n").encode("utf-8")
            ),
        }
        _require(
            all(source[key] == value for key, value in current_identity.items()),
            "D-126 current Git identity differs",
        )
        dirty = _run_git(root, "status", "--porcelain", "--untracked-files=all").splitlines()
        allowed = {f"?? {PREFLIGHT_PATH.as_posix()}", f"?? {GATE_PATH.as_posix()}"}
        _require(set(dirty).issubset(allowed), "D-126 current source has unexpected changes")
    elif mode == "post-evidence-commit":
        post_commit = _post_commit_state(root, source)
    else:
        raise D126PreflightError("D-126 validation mode differs")
    binding = _binding(root, GATE_PATH)
    return {
        "status": body["status"],
        "gate_id": gate["artifact_id"],
        "semantic_body_hash": gate["semantic_body_hash"],
        "file_bytes": binding["file_bytes"],
        "file_sha256": binding["file_sha256"],
        "source_commit": source["commit"],
        "environment_ready_for_execution_hash": body["qualification"][
            "environment_ready_for_execution_hash"
        ],
        "observed_blockers": body["qualification"]["observed_blockers"],
        "execution_hash_created": False,
        "execution_candidate_created": False,
        "provider_calls_made": 0,
        "docker_workload_calls_made": 0,
        "post_commit": post_commit,
    }


__all__ = [
    "BLOCKED_STATUS",
    "CommandRunner",
    "D126PreflightError",
    "FetchedDocument",
    "GATE_PATH",
    "PREFLIGHT_PATH",
    "READY_STATUS",
    "RECEIPT_PATH",
    "create_d126_approval_receipt",
    "run_d126_preflight",
    "validate_d126_preflight_gate",
]
