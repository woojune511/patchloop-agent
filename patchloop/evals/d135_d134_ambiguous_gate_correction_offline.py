"""Correct the ambiguous D-134 gate without changing historical bytes.

D-135 preserves the D-134 gate as an explicitly non-authoritative predecessor,
binds the consumed D-132 pricing attempt and ``ACTION_STARTED`` marker, and
qualifies only a future append-only procedural incident terminal.  It never
resumes the D-132 runner or imports an external execution helper.
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from patchloop.errors import ContractError
from patchloop.evals import d131_d130_local_admission_offline as d131
from patchloop.util import canonical_json, sha256_bytes, sha256_text

MILESTONE = "D-135"
GATE_SCHEMA = "d134-ambiguous-gate-corrected-offline-source-gate-d135-v1"
GATE_STATUS = (
    "D135_D134_AMBIGUOUS_GATE_CORRECTION_OFFLINE_SOURCE_QUALIFIED_TERMINALIZATION_APPROVAL_REQUIRED"
)
GATE_PATH = Path(
    "reports/live-pilot/artifacts/d135-d134-ambiguous-gate-correction-offline-source-gate.json"
)
TERMINAL_SCHEMA = "d132-pricing-consumed-incident-procedural-terminal-d135-v1"
TERMINAL_STATUS = "D135_D132_PRICING_CONSUMED_INCIDENT_PROCEDURALLY_TERMINAL"
TERMINAL_PATH = Path(
    "reports/live-pilot/artifacts/d135-d132-pricing-consumed-incident-procedural-terminal.json"
)

ATTEMPT_PATH = Path(
    "reports/live-pilot/artifacts/d130-official-pricing-capture-attempt-intent.json"
)
ATTEMPT_ID = (
    "d132d130officialpricingcaptureattempt_"
    "c518711e0a12b75a3ab81bbfd3e53eb3e13059d0f6fe4b3c4c1309e25924245f"
)
ATTEMPT_BODY_SHA256 = "sha256:c518711e0a12b75a3ab81bbfd3e53eb3e13059d0f6fe4b3c4c1309e25924245f"
ATTEMPT_FILE_SHA256 = "sha256:ba79ad9362bf14f0cdf8952d9297bea8fcd77fe36ab0eeff44e47e9047ec3f55"
ATTEMPT_FILE_BYTES = 18_137
ATTEMPT_BLOB_OID = "530ad365efe8a79eaa6f131db1a4541a4f94c20c"
ATTEMPT_COMMIT = "30412b769b340f98000674f40de9102d1210507a"
ATTEMPT_TREE = "2a865bf4245936ccb2d4366153038875444a536b"
ATTEMPT_PARENT = "72f1aef7ab93b9d1167ef5d3b11947a9d1f32cf0"

MARKER_PATH = Path("reports/live-pilot/artifacts/d130-official-pricing-capture-action-started.json")
MARKER_ID = (
    "d132d130officialpricingcapturestarted_"
    "50876b05d4daa48d5f80bce7793f28ffb4f7909350661803dfa96f9a2e6dced7"
)
MARKER_BODY_SHA256 = "sha256:50876b05d4daa48d5f80bce7793f28ffb4f7909350661803dfa96f9a2e6dced7"
MARKER_FILE_SHA256 = "sha256:328c4fb5ae4d6e50308333e360f25fb88bc856bace7ba483f2eb7e2adde13328"
MARKER_FILE_BYTES = 12_815
MARKER_BLOB_OID = "4e1af70ae48884a5c3ec492a9afc83313829ee75"
MARKER_COMMIT = "a10033b6abd7155ebaa5c66c13627ad3ea738566"
MARKER_TREE = "33d7aa66d2e7aa23e0b73ca851a02db20ec295e8"
MARKER_PARENT = ATTEMPT_COMMIT

D134_SOURCE_COMMIT = "44a461de923357f36cadc94eebd14d264a7366fc"
D134_SOURCE_TREE = "32753ce3877cae916e5c9654d4887aa08e138ed7"
D134_SOURCE_PARENT = MARKER_COMMIT
D134_SOURCE_PATHS = (
    Path("patchloop/evals/d134_d132_pricing_consumed_incident_offline.py"),
    Path("scripts/build_d134_d132_pricing_consumed_incident_offline.py"),
    Path("tests/test_d134_d132_pricing_consumed_incident_offline.py"),
)
PRESERVED_D134_GATE_PATH = Path(
    "reports/live-pilot/artifacts/"
    "d134-d132-pricing-consumed-incident-procedural-terminal-offline-source-gate.json"
)
PRESERVED_D134_GATE_SCHEMA = (
    "d132-pricing-consumed-incident-procedural-terminal-offline-source-gate-d134-v1"
)
PRESERVED_D134_GATE_STATUS = (
    "D134_D132_PRICING_CONSUMED_INCIDENT_PROCEDURAL_TERMINAL_"
    "OFFLINE_SOURCE_QUALIFIED_TERMINALIZATION_APPROVAL_REQUIRED"
)
PRESERVED_D134_GATE_ID = "d134_a6ec18615a853b34de104a4a89d0db1d43bea3cea12c1412033e260c50779889"
PRESERVED_D134_GATE_BODY_SHA256 = (
    "sha256:a6ec18615a853b34de104a4a89d0db1d43bea3cea12c1412033e260c50779889"
)
PRESERVED_D134_GATE_FILE_SHA256 = (
    "sha256:ed32146e25b0fbde90ea3e1bbc7f63badbc1be098f3b031c09321e914a0f9b3c"
)
PRESERVED_D134_GATE_FILE_BYTES = 18_882
PRESERVED_D134_GATE_BLOB_OID = "56fdd6d3336fc402af13bf4d3ac63d47d57805aa"
PRESERVATION_COMMIT = "9dc450a747537634e89fe2ade824685f8b5a52d6"
PRESERVATION_TREE = "e62d3d62f9161e3f2732b4f2da2386fe61588147"
PRESERVATION_PARENT = D134_SOURCE_COMMIT
PRESERVED_D134_TERMINAL_PATH = Path(
    "reports/live-pilot/artifacts/d134-d132-pricing-consumed-incident-procedural-terminal.json"
)

CANONICAL_D132_PRICING_TERMINAL_PATH = Path(
    "reports/live-pilot/artifacts/d130-replayable-official-pricing-evidence.json"
)
CANONICAL_D132_DESCENDANT_PATHS = (
    CANONICAL_D132_PRICING_TERMINAL_PATH,
    Path("reports/live-pilot/artifacts/d130-read-only-preflight-attempt-intent.json"),
    Path("reports/live-pilot/artifacts/d130-read-only-preflight-action-started.json"),
    Path("reports/live-pilot/artifacts/d130-repeated-no-call-readiness-preflight.json"),
    Path("reports/live-pilot/artifacts/d130-terminal-successor-no-call-preflight-gate.json"),
    PRESERVED_D134_TERMINAL_PATH,
)

IMPLEMENTATION_PATHS = (
    Path("patchloop/evals/d135_d134_ambiguous_gate_correction_offline.py"),
    Path("scripts/build_d135_d134_ambiguous_gate_correction_offline.py"),
    Path("tests/test_d135_d134_ambiguous_gate_correction_offline.py"),
)
DEPENDENCY_PATHS = tuple(
    dict.fromkeys(
        (
            Path("patchloop/__init__.py"),
            Path("patchloop/contracts.py"),
            Path("patchloop/evals/__init__.py"),
            Path("patchloop/evals/d131_d130_local_admission_offline.py"),
            Path("patchloop/evals/d130_d129_sequence_block_successor_offline.py"),
            Path("patchloop/evals/d129_external_sequence_block.py"),
            Path("patchloop/evals/d129_d128_terminal_successor_offline.py"),
            *d131.DEPENDENCY_PATHS,
            Path("patchloop/errors.py"),
            Path("patchloop/runtime.py"),
            Path("patchloop/util.py"),
        )
    )
)
SOURCE_BINDING_PATHS = IMPLEMENTATION_PATHS + DEPENDENCY_PATHS
ACTIVE_DOC_PATHS = d131.ACTIVE_DOC_PATHS
PYTHON_ROUTING_ENV_NAMES = ("PYTHONHOME", "PYTHONPATH")
LOADED_MODULE_PATHS = (
    (IMPLEMENTATION_PATHS[0], __name__),
    (Path("patchloop/__init__.py"), "patchloop"),
    (Path("patchloop/contracts.py"), "patchloop.contracts"),
    (Path("patchloop/errors.py"), "patchloop.errors"),
    (Path("patchloop/evals/__init__.py"), "patchloop.evals"),
    (
        Path("patchloop/evals/d129_d128_terminal_successor_offline.py"),
        "patchloop.evals.d129_d128_terminal_successor_offline",
    ),
    (
        Path("patchloop/evals/d129_external_sequence_block.py"),
        "patchloop.evals.d129_external_sequence_block",
    ),
    (
        Path("patchloop/evals/d130_d129_sequence_block_successor_offline.py"),
        "patchloop.evals.d130_d129_sequence_block_successor_offline",
    ),
    (Path("patchloop/evals/d131_d130_local_admission_offline.py"), d131.__name__),
    (Path("patchloop/runtime.py"), "patchloop.runtime"),
    (Path("patchloop/util.py"), "patchloop.util"),
)

ROOT_KEYS = ("schema_version", "artifact_id", "semantic_body_hash", "semantic_body")
GATE_ROOT_KEYS = ("schema_version", "gate_id", "semantic_body_hash", "semantic_body")
GATE_BODY_KEYS = (
    "milestone",
    "evidence_kind",
    "recorded_at",
    "status",
    "predecessor_chain",
    "source_identity",
    "source_preparation_approval",
    "incident_contract",
    "qualified_procedural_terminal_contract",
    "offline_qualification",
    "evidence_boundary",
    "authority",
    "next_gate",
)
TERMINAL_BODY_KEYS = (
    "milestone",
    "evidence_kind",
    "recorded_at",
    "status",
    "d135_gate_binding",
    "source_identity",
    "predecessor_chain",
    "terminalization_approval",
    "incident_observation",
    "evidence_boundary",
    "authority",
    "next_gate",
)
GATE_EVIDENCE_COMMIT_KEYS = (
    "commit",
    "tree",
    "parents",
    "artifact_path",
    "artifact_blob_oid",
    "artifact_file_sha256",
    "artifact_file_bytes",
    "exact_gate_add_and_active_docs_modify_commit",
)

FOCUSED_TESTS_PASSED = 15
D135_SOURCE_PREPARATION_SCOPE = (
    "preserve-exact-d134-gate-in-sole-child-single-artifact-commit",
    "treat-preserved-d134-gate-as-ambiguous-invalid-and-non-authoritative",
    "create-corrected-source-test-cli-only-direct-child-of-preservation-commit",
    "remove-ambiguous-pricing-capture-get-count-from-corrected-artifacts",
    "bind-exact-attempt-marker-d134-source-preserved-gate-and-git-topology",
    "implement-corrected-procedural-terminal-writer-validator-cli-and-mocked-tests",
    "enforce-append-only-collision-orphan-idempotence-loaded-module-and-terminal-only-commit",
    "create-new-path-corrected-d135-gate-and-exact-ten-active-doc-evidence-commit",
    "render-fresh-exact-terminalization-approval-template",
    "create-only-local-git-commits-within-this-scope",
)
D135_SOURCE_PREPARATION_EXCLUSIONS = (
    "delete-modify-overwrite-or-authorize-preserved-d134-gate",
    "bundle-preserved-d134-gate-with-docs-as-normal-evidence",
    "create-procedural-terminal-in-this-source-preparation-turn",
    "retry-resume-repair-d132-pricing-or-backfill-canonical-terminal",
    "official-docs-search-open-network-or-pricing-capture",
    "docker-sdk-credential-dotenv-or-endpoint-observation",
    "import-or-execute-existing-external-runner-or-helper",
    "provider-evaluator-agent-memory-or-retrieval",
    "execution-hash-candidate-cost-or-four-row-ac",
)
TERMINALIZATION_SCOPE = (
    "create-one-exact-d135-procedural-terminal-artifact",
    "create-one-terminal-only-local-git-commit",
    "preserve-consumed-no-retry-and-observation-boundaries",
)
TERMINALIZATION_EXCLUSIONS = (
    "retry-resume-repair-or-canonical-pricing-terminal-backfill",
    "pricing-helper-fix-or-fixed-successor-source",
    "official-docs-search-open-network-or-pricing-capture",
    "docker-sdk-credential-dotenv-or-endpoint-observation",
    "provider-evaluator-agent-memory-retrieval-hash-candidate-cost-or-four-row-ac",
)


class D135PricingConsumedIncidentError(ContractError):
    """Raised when the D-135 offline incident boundary is not exact."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise D135PricingConsumedIncidentError(message)


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _repo_root(repository: str | Path | None) -> Path:
    try:
        return d131._repo_root(repository)
    except ContractError as exc:
        raise D135PricingConsumedIncidentError(str(exc)) from exc


def _parse_time(value: Any, *, label: str) -> datetime:
    try:
        return d131._parse_time(value, label=label)
    except ContractError as exc:
        raise D135PricingConsumedIncidentError(str(exc)) from exc


def _pretty_bytes(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, ensure_ascii=True, indent=2) + "\n").encode("utf-8")


def _envelope(schema: str, prefix: str, body: dict[str, Any]) -> dict[str, Any]:
    body_hash = sha256_text(canonical_json(body))
    return {
        "schema_version": schema,
        "artifact_id": f"{prefix}_{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": body,
    }


def _gate_envelope(body: dict[str, Any]) -> dict[str, Any]:
    body_hash = sha256_text(canonical_json(body))
    return {
        "schema_version": GATE_SCHEMA,
        "gate_id": f"d135_{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": body,
    }


def _stable_read(root: Path, relative: Path) -> bytes:
    try:
        return d131._stable_read(root, relative)
    except ContractError as exc:
        raise D135PricingConsumedIncidentError(str(exc)) from exc


def _lexists(root: Path, relative: Path) -> bool:
    return os.path.lexists(root / relative)


def _path_absent(root: Path, relative: Path) -> None:
    _require(not _lexists(root, relative), f"D-135 unexpected path exists: {relative}")


def _read_json(root: Path, relative: Path) -> tuple[dict[str, Any], bytes]:
    raw = _stable_read(root, relative)
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise D135PricingConsumedIncidentError(f"D-135 {relative.name} JSON differs") from exc
    _require(isinstance(payload, dict), f"D-135 {relative.name} root differs")
    return payload, raw


def _write_new(root: Path, relative: Path, raw: bytes) -> None:
    try:
        selected = d131.d129_offline._logical_path(root, relative, must_exist=False)
    except ContractError as exc:
        raise D135PricingConsumedIncidentError(str(exc)) from exc
    _require(not os.path.lexists(selected), f"D-135 {relative.name} already exists")
    temporary = selected.with_name(f".{selected.name}.d135-{uuid.uuid4().hex}.tmp")
    _require(not os.path.lexists(temporary), "D-135 temporary output collision")
    try:
        with temporary.open("xb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        _require(temporary.read_bytes() == raw, "D-135 temporary output differs")
        try:
            os.link(temporary, selected)
        except FileExistsError as exc:
            raise D135PricingConsumedIncidentError(
                f"D-135 {relative.name} publication collision"
            ) from exc
        _require(_stable_read(root, relative) == raw, "D-135 persisted output differs")
    finally:
        with suppress(OSError):
            temporary.unlink()


def _git_command(root: Path, *args: str, binary: bool = False) -> bytes | str:
    try:
        return d131._git_command(root, *args, binary=binary)
    except ContractError as exc:
        raise D135PricingConsumedIncidentError(str(exc)) from exc


def _commit_identity(root: Path, commit: str) -> dict[str, Any]:
    try:
        return d131._commit_identity(root, commit)
    except ContractError as exc:
        raise D135PricingConsumedIncidentError(str(exc)) from exc


def _diff_rows(root: Path, commit: str) -> list[dict[str, str]]:
    try:
        return d131._diff_rows(root, commit)
    except ContractError as exc:
        raise D135PricingConsumedIncidentError(str(exc)) from exc


def _commit_blob(root: Path, commit: str, path: Path) -> tuple[str, bytes]:
    try:
        return d131._commit_blob(root, commit, path)
    except ContractError as exc:
        raise D135PricingConsumedIncidentError(str(exc)) from exc


def _status_lines(root: Path) -> list[str]:
    try:
        return d131._status_lines(root)
    except ContractError as exc:
        raise D135PricingConsumedIncidentError(str(exc)) from exc


def _head(root: Path) -> str:
    try:
        return d131._head(root)
    except ContractError as exc:
        raise D135PricingConsumedIncidentError(str(exc)) from exc


def _assert_runtime_import_boundary(root: Path) -> None:
    presence = {name: name in os.environ for name in PYTHON_ROUTING_ENV_NAMES}
    _require(not any(presence.values()), "D-135 Python import routing environment is present")
    seen: set[tuple[str, str]] = set()
    for relative, module_name in LOADED_MODULE_PATHS:
        key = (relative.as_posix(), module_name)
        if key in seen:
            continue
        seen.add(key)
        module = sys.modules.get(module_name)
        loaded_value = getattr(module, "__file__", None)
        _require(isinstance(loaded_value, str), f"D-135 loaded module differs: {relative}")
        try:
            loaded = Path(loaded_value).resolve(strict=True)
            expected = (root / relative).resolve(strict=True)
        except OSError as exc:
            raise D135PricingConsumedIncidentError(
                f"D-135 loaded module differs: {relative}"
            ) from exc
        _require(loaded == expected, f"D-135 loaded module is outside repository: {relative}")


def _file_binding(root: Path, commit: str, path: Path) -> dict[str, Any]:
    oid, committed = _commit_blob(root, commit, path)
    current = _stable_read(root, path)
    _require(current == committed, f"D-135 source drift: {path}")
    return {
        "path": path.as_posix(),
        "blob_oid": oid,
        "file_sha256": sha256_bytes(committed),
        "file_bytes": len(committed),
        "current_bytes_match_commit": True,
    }


def _loaded_module_bindings(root: Path, commit: str) -> list[dict[str, Any]]:
    _assert_runtime_import_boundary(root)
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for path, module_name in LOADED_MODULE_PATHS:
        key = (path.as_posix(), module_name)
        if key in seen:
            continue
        seen.add(key)
        result.append(
            {
                **_file_binding(root, commit, path),
                "module_name": module_name,
                "loaded_path": path.as_posix(),
                "loaded_path_matches_repository": True,
            }
        )
    return result


def _validate_envelope(
    payload: dict[str, Any],
    raw: bytes,
    *,
    schema: str,
    prefix: str,
    gate: bool = False,
) -> dict[str, Any]:
    keys = GATE_ROOT_KEYS if gate else ROOT_KEYS
    _require(tuple(payload) == keys, "D-135 artifact root keys differ")
    body = payload.get("semantic_body")
    _require(isinstance(body, dict), "D-135 artifact body differs")
    body_hash = sha256_text(canonical_json(body))
    identity_key = "gate_id" if gate else "artifact_id"
    expected_id = f"{prefix}_{body_hash.removeprefix('sha256:')}"
    _require(payload.get("schema_version") == schema, "D-135 artifact schema differs")
    _require(payload.get(identity_key) == expected_id, "D-135 artifact identity differs")
    _require(payload.get("semantic_body_hash") == body_hash, "D-135 body hash differs")
    _require(_pretty_bytes(payload) == raw, "D-135 artifact serialization differs")
    return body


def _artifact_binding(
    *, path: Path, payload: dict[str, Any], raw: bytes, status: str
) -> dict[str, Any]:
    identity = payload.get("gate_id", payload.get("artifact_id"))
    return {
        "path": path.as_posix(),
        "artifact_id": identity,
        "semantic_body_hash": payload["semantic_body_hash"],
        "file_sha256": sha256_bytes(raw),
        "file_bytes": len(raw),
        "status": status,
        "recorded_at": payload["semantic_body"]["recorded_at"],
        "artifact_mutated": False,
    }


def _exact_commit_binding(
    root: Path,
    *,
    commit: str,
    tree: str,
    parent: str,
    path: Path,
    blob_oid: str,
    file_sha256: str,
    file_bytes: int,
) -> dict[str, Any]:
    identity = _commit_identity(root, commit)
    _require(
        identity == {"commit": commit, "tree": tree, "parents": [parent]},
        f"D-135 predecessor topology differs: {commit}",
    )
    _require(
        _diff_rows(root, commit) == [{"status": "A", "path": path.as_posix()}],
        f"D-135 predecessor scope differs: {commit}",
    )
    oid, committed = _commit_blob(root, commit, path)
    _require(
        oid == blob_oid and len(committed) == file_bytes and sha256_bytes(committed) == file_sha256,
        f"D-135 predecessor blob differs: {path}",
    )
    return {
        "commit": commit,
        "tree": tree,
        "parents": [parent],
        "artifact_path": path.as_posix(),
        "artifact_blob_oid": blob_oid,
        "artifact_file_sha256": file_sha256,
        "artifact_file_bytes": file_bytes,
        "single_artifact_add_commit": True,
    }


def _d134_source_binding(root: Path) -> dict[str, Any]:
    identity = _commit_identity(root, D134_SOURCE_COMMIT)
    _require(
        identity
        == {
            "commit": D134_SOURCE_COMMIT,
            "tree": D134_SOURCE_TREE,
            "parents": [D134_SOURCE_PARENT],
        },
        "D-135 preserved D-134 source topology differs",
    )
    expected = [{"status": "A", "path": path.as_posix()} for path in D134_SOURCE_PATHS]
    _require(
        sorted(_diff_rows(root, D134_SOURCE_COMMIT), key=lambda row: row["path"])
        == sorted(expected, key=lambda row: row["path"]),
        "D-135 preserved D-134 source scope differs",
    )
    bindings = []
    for path in D134_SOURCE_PATHS:
        oid, raw = _commit_blob(root, D134_SOURCE_COMMIT, path)
        bindings.append(
            {
                "path": path.as_posix(),
                "blob_oid": oid,
                "file_sha256": sha256_bytes(raw),
                "file_bytes": len(raw),
            }
        )
    return {
        **identity,
        "implementation_paths_added": [path.as_posix() for path in D134_SOURCE_PATHS],
        "file_bindings": bindings,
        "exact_source_only_add_commit": True,
    }


def _preserved_ambiguous_gate_binding(root: Path) -> dict[str, Any]:
    payload, raw = _read_json(root, PRESERVED_D134_GATE_PATH)
    body = _validate_envelope(
        payload,
        raw,
        schema=PRESERVED_D134_GATE_SCHEMA,
        prefix="d134",
        gate=True,
    )
    _require(
        payload["gate_id"] == PRESERVED_D134_GATE_ID
        and payload["semantic_body_hash"] == PRESERVED_D134_GATE_BODY_SHA256
        and sha256_bytes(raw) == PRESERVED_D134_GATE_FILE_SHA256
        and len(raw) == PRESERVED_D134_GATE_FILE_BYTES,
        "D-135 preserved D-134 gate tuple differs",
    )
    _require(body.get("status") == PRESERVED_D134_GATE_STATUS, "D-135 old gate status differs")
    _require(
        body.get("source_identity", {}).get("commit") == D134_SOURCE_COMMIT,
        "D-135 old gate source binding differs",
    )
    preservation = _exact_commit_binding(
        root,
        commit=PRESERVATION_COMMIT,
        tree=PRESERVATION_TREE,
        parent=PRESERVATION_PARENT,
        path=PRESERVED_D134_GATE_PATH,
        blob_oid=PRESERVED_D134_GATE_BLOB_OID,
        file_sha256=PRESERVED_D134_GATE_FILE_SHA256,
        file_bytes=PRESERVED_D134_GATE_FILE_BYTES,
    )
    artifact = _artifact_binding(
        path=PRESERVED_D134_GATE_PATH,
        payload=payload,
        raw=raw,
        status=body["status"],
    )
    artifact.update(
        {
            "preservation_commit_binding": preservation,
            "contains_ambiguous_numeric_get_counter": True,
            "qualification_status_is_authoritative": False,
            "terminalization_authority_valid": False,
            "may_be_used_by_terminal_writer_or_template": False,
            "artifact_bytes_are_immutable_historical_evidence": True,
        }
    )
    return artifact


def _predecessor_chain(root: Path) -> dict[str, Any]:
    attempt, attempt_raw = _read_json(root, ATTEMPT_PATH)
    attempt_body = _validate_envelope(
        attempt,
        attempt_raw,
        schema="d130-external-no-call-preflight-phase-attempt-d132-v1",
        prefix="d132d130officialpricingcaptureattempt",
    )
    marker, marker_raw = _read_json(root, MARKER_PATH)
    marker_body = _validate_envelope(
        marker,
        marker_raw,
        schema="d130-external-no-call-preflight-action-started-d132-v1",
        prefix="d132d130officialpricingcapturestarted",
    )
    _require(
        attempt["artifact_id"] == ATTEMPT_ID
        and attempt["semantic_body_hash"] == ATTEMPT_BODY_SHA256
        and len(attempt_raw) == ATTEMPT_FILE_BYTES
        and sha256_bytes(attempt_raw) == ATTEMPT_FILE_SHA256,
        "D-135 pricing attempt tuple differs",
    )
    _require(
        marker["artifact_id"] == MARKER_ID
        and marker["semantic_body_hash"] == MARKER_BODY_SHA256
        and len(marker_raw) == MARKER_FILE_BYTES
        and sha256_bytes(marker_raw) == MARKER_FILE_SHA256,
        "D-135 pricing marker tuple differs",
    )
    _require(attempt_body.get("phase") == "official-pricing-capture", "D-135 attempt phase differs")
    _require(marker_body.get("phase") == "official-pricing-capture", "D-135 marker phase differs")
    _require(
        marker_body.get("attempt_binding", {}).get("artifact_id") == ATTEMPT_ID,
        "D-135 marker attempt binding differs",
    )
    _require(
        marker_body.get("failure_boundary", {}).get(
            "marker_without_terminal_consumes_activation_and_forbids_retry"
        )
        is True,
        "D-135 consumed marker boundary differs",
    )
    attempt_commit = _exact_commit_binding(
        root,
        commit=ATTEMPT_COMMIT,
        tree=ATTEMPT_TREE,
        parent=ATTEMPT_PARENT,
        path=ATTEMPT_PATH,
        blob_oid=ATTEMPT_BLOB_OID,
        file_sha256=ATTEMPT_FILE_SHA256,
        file_bytes=ATTEMPT_FILE_BYTES,
    )
    marker_commit = _exact_commit_binding(
        root,
        commit=MARKER_COMMIT,
        tree=MARKER_TREE,
        parent=MARKER_PARENT,
        path=MARKER_PATH,
        blob_oid=MARKER_BLOB_OID,
        file_sha256=MARKER_FILE_SHA256,
        file_bytes=MARKER_FILE_BYTES,
    )
    _require(
        marker_body.get("attempt_commit_binding") == attempt_commit,
        "D-135 marker attempt commit binding differs",
    )
    for path in CANONICAL_D132_DESCENDANT_PATHS:
        _path_absent(root, path)
    return {
        "pricing_attempt": _artifact_binding(
            path=ATTEMPT_PATH,
            payload=attempt,
            raw=attempt_raw,
            status=attempt_body["status"],
        ),
        "pricing_attempt_commit": attempt_commit,
        "action_started_marker": _artifact_binding(
            path=MARKER_PATH,
            payload=marker,
            raw=marker_raw,
            status=marker_body["status"],
        ),
        "marker_only_commit": marker_commit,
        "d134_source_commit": _d134_source_binding(root),
        "preserved_ambiguous_d134_gate": _preserved_ambiguous_gate_binding(root),
        "activation_and_attempt_consumed": True,
        "retry_resume_repair_or_terminal_backfill_allowed": False,
    }


def _source_identity_for_gate(root: Path) -> dict[str, Any]:
    _assert_runtime_import_boundary(root)
    _require(_status_lines(root) == [], "D-135 gate requires clean committed source")
    head = _head(root)
    identity = _commit_identity(root, head)
    _require(identity["parents"] == [PRESERVATION_COMMIT], "D-135 source parent differs")
    expected = [{"status": "A", "path": path.as_posix()} for path in IMPLEMENTATION_PATHS]
    _require(
        sorted(_diff_rows(root, head), key=lambda row: row["path"])
        == sorted(expected, key=lambda row: row["path"]),
        "D-135 source scope differs",
    )
    return {
        "commit": head,
        "tree": identity["tree"],
        "parents": identity["parents"],
        "implementation_paths_added": [path.as_posix() for path in IMPLEMENTATION_PATHS],
        "file_bindings": [_file_binding(root, head, path) for path in SOURCE_BINDING_PATHS],
        "loaded_module_bindings": _loaded_module_bindings(root, head),
        "python_routing_env_presence": {name: False for name in PYTHON_ROUTING_ENV_NAMES},
        "git_cli_observation": d131._git_cli_observation(root),
        "worktree_and_index_clean_before_gate": True,
        "git_identity_vendor_authenticated_or_signed": False,
    }


def _validate_source_identity(root: Path, value: Any) -> None:
    _require(isinstance(value, dict), "D-135 source identity differs")
    commit = value.get("commit")
    _require(isinstance(commit, str), "D-135 source commit differs")
    identity = _commit_identity(root, commit)
    _require(identity["parents"] == [PRESERVATION_COMMIT], "D-135 stored source parent differs")
    expected = [{"status": "A", "path": path.as_posix()} for path in IMPLEMENTATION_PATHS]
    _require(
        sorted(_diff_rows(root, commit), key=lambda row: row["path"])
        == sorted(expected, key=lambda row: row["path"]),
        "D-135 stored source scope differs",
    )
    rebuilt = {
        "commit": commit,
        "tree": identity["tree"],
        "parents": identity["parents"],
        "implementation_paths_added": [path.as_posix() for path in IMPLEMENTATION_PATHS],
        "file_bindings": [_file_binding(root, commit, path) for path in SOURCE_BINDING_PATHS],
        "loaded_module_bindings": _loaded_module_bindings(root, commit),
        "python_routing_env_presence": {name: False for name in PYTHON_ROUTING_ENV_NAMES},
        "git_cli_observation": d131._git_cli_observation(root),
        "worktree_and_index_clean_before_gate": True,
        "git_identity_vendor_authenticated_or_signed": False,
    }
    _require(canonical_json(value) == canonical_json(rebuilt), "D-135 source identity drifted")


def _gate_body(
    *, recorded_at: str, predecessor: dict[str, Any], source: dict[str, Any]
) -> dict[str, Any]:
    return {
        "milestone": MILESTONE,
        "evidence_kind": "offline-ambiguous-gate-correction-source-qualification",
        "recorded_at": recorded_at,
        "status": GATE_STATUS,
        "predecessor_chain": predecessor,
        "source_identity": source,
        "source_preparation_approval": {
            "exact_user_approval_recorded": True,
            "approval_is_self_attested": True,
            "approval_is_authenticated_or_signed": False,
            "approved_scope": list(D135_SOURCE_PREPARATION_SCOPE),
            "explicit_exclusions": list(D135_SOURCE_PREPARATION_EXCLUSIONS),
            "procedural_terminal_creation_authorized_now": False,
            "supersedes_only_d134_gate_plus_docs_co_commit_instruction": True,
            "preserved_d134_source_and_gate_bytes_remain_immutable": True,
        },
        "incident_contract": {
            "application_level_client_send_returned_response_count": 1,
            "application_level_request_was_unauthenticated": True,
            "observation_provenance": (
                "user-approved-current-session-control-flow-observation-not-"
                "reconstructed-machine-telemetry"
            ),
            "underlying_http_request_count": "unknown",
            "completed_replayable_canonical_pricing_evidence_count": 0,
            "canonical_pricing_evidence_artifact_created": False,
            "canonical_response_status_retention_state": "not-retained",
            "canonical_response_headers_retention_state": "not-retained",
            "canonical_response_body_retention_state": "not-retained",
            "canonical_redirect_accounting_state": "not-retained",
            "canonical_replay_bytes_retained": 0,
            "canonical_http_exchange_completed": "unknown",
            "exact_failure_timestamp_retained": False,
            "existing_d132_pricing_terminal_absent": True,
            "existing_d132_preflight_and_final_gate_absent": True,
            "terminal_is_procedural_not_canonical_pricing_evidence": True,
            "preserved_d134_gate_contains_ambiguous_numeric_get_counter": True,
            "preserved_d134_gate_qualification_status_is_authoritative": False,
            "preserved_d134_gate_terminalization_authority_valid": False,
            "preserved_d134_procedural_terminal_absent": True,
        },
        "qualified_procedural_terminal_contract": {
            "writer_is_future_only": True,
            "future_exact_approval_required": True,
            "future_terminal_is_append_only_new_only": True,
            "future_terminal_only_commit_required": True,
            "future_terminal_commit_parent_is_gate_evidence_commit": True,
            "retry_resume_repair_or_backfill_forbidden": True,
            "fixed_successor_requires_later_offline_gate": True,
            "binds_only_corrected_d135_gate_evidence": True,
            "preserved_d134_gate_cannot_authorize_or_bind_terminal": True,
        },
        "offline_qualification": {
            "focused_mocked_tests_passed": FOCUSED_TESTS_PASSED,
            "builder_invoked_terminal_writer": False,
            "builder_invoked_network_or_external_helper": False,
            "predecessor_bytes_and_git_topology_replayed": True,
            "source_and_loaded_modules_bound": True,
        },
        "evidence_boundary": {
            "observed_send_return_count_is_not_canonical_pricing_evidence": True,
            "unknown_response_fields_remain_unknown": True,
            "no_system_wide_side_effect_denial_claimed": True,
            "no_secret_credential_or_environment_value_observed": True,
        },
        "authority": {
            "offline_gate_created": True,
            "procedural_terminal_created": False,
            "canonical_pricing_terminal_created": False,
            "preserved_d134_gate_authority_used": False,
            "d135_source_builder_network_call_count": 0,
            "d135_source_builder_official_docs_search_or_open_count": 0,
            "d135_source_builder_docker_cli_call_count": 0,
            "d135_source_builder_sdk_or_credential_observation_count": 0,
            "d135_source_builder_provider_evaluator_agent_call_count": 0,
            "d135_source_builder_memory_or_retrieval_count": 0,
            "execution_hash_or_candidate_created": False,
            "cost_reserved_or_spent_usd": "0",
            "four_row_ac_executed": False,
        },
        "next_gate": {
            "status": "D135_EXACT_PROCEDURAL_TERMINALIZATION_APPROVAL_REQUIRED",
            "must_quote_gate_tuple_and_evidence_commit": True,
            "terminal_only_commit_then_separate_fixed_successor": True,
            "no_external_action_in_terminalization_turn": True,
        },
    }


def _validate_gate_payload(root: Path, payload: dict[str, Any], raw: bytes) -> dict[str, Any]:
    body = _validate_envelope(payload, raw, schema=GATE_SCHEMA, prefix="d135", gate=True)
    _require(tuple(body) == GATE_BODY_KEYS, "D-135 gate body keys differ")
    predecessor = _predecessor_chain(root)
    _validate_source_identity(root, body.get("source_identity"))
    expected = _gate_envelope(
        _gate_body(
            recorded_at=body.get("recorded_at"),
            predecessor=predecessor,
            source=body["source_identity"],
        )
    )
    _require(canonical_json(payload) == canonical_json(expected), "D-135 gate full rebuild differs")
    _require(
        _parse_time(body["recorded_at"], label="D-135 gate recorded_at")
        > _parse_time(
            predecessor["preserved_ambiguous_d134_gate"]["recorded_at"],
            label="D-135 preserved D-134 gate recorded_at",
        ),
        "D-135 gate chronology differs",
    )
    return body


def _pending_gate_only(root: Path, *, source_commit: str) -> bool:
    return _head(root) == source_commit and _status_lines(root) == [f"?? {GATE_PATH.as_posix()}"]


def _rebuild_gate_evidence_commit(
    root: Path, *, payload: dict[str, Any], raw: bytes, commit: str
) -> dict[str, Any]:
    source_commit = payload["semantic_body"]["source_identity"]["commit"]
    identity = _commit_identity(root, commit)
    _require(identity["parents"] == [source_commit], "D-135 gate evidence parent differs")
    expected = [
        {"status": "A", "path": GATE_PATH.as_posix()},
        *({"status": "M", "path": path.as_posix()} for path in ACTIVE_DOC_PATHS),
    ]
    _require(
        sorted(_diff_rows(root, commit), key=lambda row: row["path"])
        == sorted(expected, key=lambda row: row["path"]),
        "D-135 gate evidence scope differs",
    )
    oid, committed = _commit_blob(root, commit, GATE_PATH)
    _require(committed == raw, "D-135 committed gate bytes differ")
    return {
        "commit": commit,
        "tree": identity["tree"],
        "parents": identity["parents"],
        "artifact_path": GATE_PATH.as_posix(),
        "artifact_blob_oid": oid,
        "artifact_file_sha256": sha256_bytes(raw),
        "artifact_file_bytes": len(raw),
        "exact_gate_add_and_active_docs_modify_commit": True,
    }


def _gate_evidence_commit_binding(
    root: Path, *, payload: dict[str, Any], raw: bytes
) -> dict[str, Any]:
    _require(_status_lines(root) == [], "D-135 gate evidence commit is not clean")
    return _rebuild_gate_evidence_commit(root, payload=payload, raw=raw, commit=_head(root))


def _validate_stored_gate_evidence_commit(
    root: Path,
    *,
    payload: dict[str, Any],
    raw: bytes,
    value: Any,
) -> dict[str, Any]:
    _require(isinstance(value, dict), "D-135 stored gate evidence commit differs")
    _require(tuple(value) == GATE_EVIDENCE_COMMIT_KEYS, "D-135 gate commit keys differ")
    commit = value.get("commit")
    _require(isinstance(commit, str), "D-135 stored gate commit differs")
    rebuilt = _rebuild_gate_evidence_commit(root, payload=payload, raw=raw, commit=commit)
    _require(
        canonical_json(value) == canonical_json(rebuilt),
        "D-135 stored gate evidence commit drifted",
    )
    return rebuilt


def run_d135_corrected_offline_source_gate(
    *, repository: str | Path | None = None
) -> dict[str, Any]:
    """Create only the D-135 offline gate; never create the procedural terminal."""

    root = _repo_root(repository)
    _assert_runtime_import_boundary(root)
    _path_absent(root, TERMINAL_PATH)
    for path in CANONICAL_D132_DESCENDANT_PATHS:
        _path_absent(root, path)
    if _lexists(root, GATE_PATH):
        if _pending_gate_only(
            root,
            source_commit=_read_json(root, GATE_PATH)[0]["semantic_body"]["source_identity"][
                "commit"
            ],
        ):
            return validate_d135_corrected_offline_source_gate(repository=root)
        return validate_d135_corrected_offline_source_gate(
            repository=root, mode="post-evidence-commit"
        )
    predecessor = _predecessor_chain(root)
    source = _source_identity_for_gate(root)
    recorded_at = _now()
    _require(
        _parse_time(recorded_at, label="D-135 gate recorded_at")
        > _parse_time(
            predecessor["preserved_ambiguous_d134_gate"]["recorded_at"],
            label="D-135 preserved D-134 gate recorded_at",
        ),
        "D-135 gate clock regressed",
    )
    payload = _gate_envelope(
        _gate_body(recorded_at=recorded_at, predecessor=predecessor, source=source)
    )
    raw = _pretty_bytes(payload)
    _validate_gate_payload(root, payload, raw)
    _write_new(root, GATE_PATH, raw)
    stored, stored_raw = _read_json(root, GATE_PATH)
    _validate_gate_payload(root, stored, stored_raw)
    _require(_pending_gate_only(root, source_commit=source["commit"]), "D-135 gate scope differs")
    return {
        "gate_id": stored["gate_id"],
        "semantic_body_hash": stored["semantic_body_hash"],
        "file_sha256": sha256_bytes(stored_raw),
        "file_bytes": len(stored_raw),
        "status": stored["semantic_body"]["status"],
        "source_commit": source["commit"],
        "evidence_commit": None,
        "procedural_terminal_created": False,
        "external_call_count": 0,
    }


def validate_d135_corrected_offline_source_gate(
    *,
    repository: str | Path | None = None,
    mode: Literal["current-source", "post-evidence-commit"] = "current-source",
) -> dict[str, Any]:
    """Replay the D-135 gate without creating terminal or external evidence."""

    root = _repo_root(repository)
    _assert_runtime_import_boundary(root)
    _path_absent(root, TERMINAL_PATH)
    payload, raw = _read_json(root, GATE_PATH)
    body = _validate_gate_payload(root, payload, raw)
    evidence_commit = None
    if mode == "current-source":
        _path_absent(root, TERMINAL_PATH)
        _require(
            _pending_gate_only(root, source_commit=body["source_identity"]["commit"]),
            "D-135 current-source gate checkout differs",
        )
    elif mode == "post-evidence-commit":
        evidence_commit = _gate_evidence_commit_binding(root, payload=payload, raw=raw)
    else:
        raise D135PricingConsumedIncidentError("D-135 gate validation mode differs")
    return {
        "gate_id": payload["gate_id"],
        "semantic_body_hash": payload["semantic_body_hash"],
        "file_sha256": sha256_bytes(raw),
        "file_bytes": len(raw),
        "status": body["status"],
        "source_commit": body["source_identity"]["commit"],
        "evidence_commit": evidence_commit,
        "procedural_terminal_created": False,
        "external_call_count": 0,
    }


def _gate_binding_for_terminal(
    root: Path, *, stored_evidence_commit: Any = None
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    payload, raw = _read_json(root, GATE_PATH)
    _validate_gate_payload(root, payload, raw)
    evidence = (
        _gate_evidence_commit_binding(root, payload=payload, raw=raw)
        if stored_evidence_commit is None
        else _validate_stored_gate_evidence_commit(
            root,
            payload=payload,
            raw=raw,
            value=stored_evidence_commit,
        )
    )
    binding = _artifact_binding(
        path=GATE_PATH,
        payload=payload,
        raw=raw,
        status=payload["semantic_body"]["status"],
    )
    binding["evidence_commit_binding"] = evidence
    return payload, binding, evidence


def _terminal_body(
    *,
    recorded_at: str,
    gate_binding: dict[str, Any],
    source: dict[str, Any],
    predecessor: dict[str, Any],
) -> dict[str, Any]:
    return {
        "milestone": MILESTONE,
        "evidence_kind": "append-only-procedural-consumed-incident-terminal",
        "recorded_at": recorded_at,
        "status": TERMINAL_STATUS,
        "d135_gate_binding": gate_binding,
        "source_identity": source,
        "predecessor_chain": predecessor,
        "terminalization_approval": {
            "exact_user_approval_recorded": True,
            "approval_is_self_attested": True,
            "approval_is_authenticated_or_signed": False,
            "approved_scope": list(TERMINALIZATION_SCOPE),
            "explicit_exclusions": list(TERMINALIZATION_EXCLUSIONS),
        },
        "incident_observation": {
            "activation_and_pricing_attempt_consumed": True,
            "application_level_client_send_returned_response_count": 1,
            "application_level_request_was_unauthenticated": True,
            "observation_provenance": (
                "user-approved-current-session-control-flow-observation-not-"
                "reconstructed-machine-telemetry"
            ),
            "underlying_http_request_count": "unknown",
            "completed_replayable_canonical_pricing_evidence_count": 0,
            "canonical_pricing_evidence_artifact_created": False,
            "canonical_response_status_retention_state": "not-retained",
            "canonical_response_headers_retention_state": "not-retained",
            "canonical_response_body_retention_state": "not-retained",
            "canonical_redirect_accounting_state": "not-retained",
            "canonical_replay_bytes_retained": 0,
            "canonical_http_exchange_completed": "unknown",
            "exact_failure_timestamp_retained": False,
            "retry_resume_repair_or_backfill_allowed": False,
            "preserved_d134_gate_qualification_status_is_authoritative": False,
            "preserved_d134_gate_terminalization_authority_used": False,
            "preserved_d134_procedural_terminal_absent": True,
        },
        "evidence_boundary": {
            "procedural_terminal_is_not_canonical_pricing_evidence": True,
            "historical_attempt_and_marker_are_immutable": True,
            "unknown_response_fields_remain_unknown": True,
            "no_secret_credential_or_environment_value_observed": True,
        },
        "authority": {
            "procedural_terminal_created": True,
            "canonical_pricing_terminal_created": False,
            "preserved_d134_gate_authority_used": False,
            "d135_terminalization_turn_network_call_count": 0,
            "d135_terminalization_turn_official_docs_search_or_open_count": 0,
            "d135_terminalization_turn_docker_cli_call_count": 0,
            "d135_terminalization_turn_sdk_or_credential_observation_count": 0,
            "d135_terminalization_turn_provider_evaluator_agent_call_count": 0,
            "d135_terminalization_turn_memory_or_retrieval_count": 0,
            "execution_hash_or_candidate_created": False,
            "cost_reserved_or_spent_usd": "0",
            "four_row_ac_executed": False,
        },
        "next_gate": {
            "status": "D135_FIXED_PRICING_SUCCESSOR_OFFLINE_SOURCE_APPROVAL_REQUIRED",
            "fresh_source_qualification_and_activation_required": True,
            "current_activation_reusable": False,
        },
    }


def _validate_terminal_payload(root: Path, payload: dict[str, Any], raw: bytes) -> dict[str, Any]:
    body = _validate_envelope(
        payload,
        raw,
        schema=TERMINAL_SCHEMA,
        prefix="d135pricingincident",
    )
    _require(tuple(body) == TERMINAL_BODY_KEYS, "D-135 terminal body keys differ")
    stored_gate = body.get("d135_gate_binding")
    _require(isinstance(stored_gate, dict), "D-135 stored terminal gate binding differs")
    gate_payload, gate_binding, _evidence = _gate_binding_for_terminal(
        root,
        stored_evidence_commit=stored_gate.get("evidence_commit_binding"),
    )
    predecessor = _predecessor_chain(root)
    expected = _envelope(
        TERMINAL_SCHEMA,
        "d135pricingincident",
        _terminal_body(
            recorded_at=body.get("recorded_at"),
            gate_binding=gate_binding,
            source=gate_payload["semantic_body"]["source_identity"],
            predecessor=predecessor,
        ),
    )
    _require(
        canonical_json(payload) == canonical_json(expected), "D-135 terminal full rebuild differs"
    )
    _require(
        _parse_time(body["recorded_at"], label="D-135 terminal recorded_at")
        > _parse_time(gate_binding["recorded_at"], label="D-135 gate recorded_at"),
        "D-135 terminal chronology differs",
    )
    return body


def create_d135_procedural_terminal(*, repository: str | Path | None = None) -> dict[str, Any]:
    """Create the future approved procedural terminal, never external evidence."""

    root = _repo_root(repository)
    _assert_runtime_import_boundary(root)
    for path in CANONICAL_D132_DESCENDANT_PATHS:
        _path_absent(root, path)
    if _lexists(root, TERMINAL_PATH):
        status = _status_lines(root)
        if status == [f"?? {TERMINAL_PATH.as_posix()}"]:
            return validate_d135_procedural_terminal(repository=root)
        if status == []:
            return validate_d135_procedural_terminal(repository=root, mode="post-terminal-commit")
        raise D135PricingConsumedIncidentError("D-135 existing terminal checkout state differs")
    gate_payload, gate_binding, evidence = _gate_binding_for_terminal(root)
    _require(_status_lines(root) == [], "D-135 terminal requires clean gate evidence commit")
    _require(_head(root) == evidence["commit"], "D-135 terminal parent differs")
    predecessor = _predecessor_chain(root)
    recorded_at = _now()
    _require(
        _parse_time(recorded_at, label="D-135 terminal recorded_at")
        > _parse_time(gate_binding["recorded_at"], label="D-135 gate recorded_at"),
        "D-135 terminal clock regressed",
    )
    payload = _envelope(
        TERMINAL_SCHEMA,
        "d135pricingincident",
        _terminal_body(
            recorded_at=recorded_at,
            gate_binding=gate_binding,
            source=gate_payload["semantic_body"]["source_identity"],
            predecessor=predecessor,
        ),
    )
    raw = _pretty_bytes(payload)
    _validate_terminal_payload(root, payload, raw)
    _write_new(root, TERMINAL_PATH, raw)
    stored, stored_raw = _read_json(root, TERMINAL_PATH)
    _validate_terminal_payload(root, stored, stored_raw)
    _require(
        _status_lines(root) == [f"?? {TERMINAL_PATH.as_posix()}"],
        "D-135 terminal is not the sole pending path",
    )
    return {
        "artifact_id": stored["artifact_id"],
        "semantic_body_hash": stored["semantic_body_hash"],
        "file_sha256": sha256_bytes(stored_raw),
        "file_bytes": len(stored_raw),
        "status": stored["semantic_body"]["status"],
        "terminal_commit": None,
        "external_call_count": 0,
    }


def _terminal_commit_binding(root: Path, *, payload: dict[str, Any], raw: bytes) -> dict[str, Any]:
    _require(_status_lines(root) == [], "D-135 terminal commit is not clean")
    head = _head(root)
    gate_commit = payload["semantic_body"]["d135_gate_binding"]["evidence_commit_binding"]["commit"]
    identity = _commit_identity(root, head)
    _require(identity["parents"] == [gate_commit], "D-135 terminal commit parent differs")
    _require(
        _diff_rows(root, head) == [{"status": "A", "path": TERMINAL_PATH.as_posix()}],
        "D-135 terminal commit scope differs",
    )
    oid, committed = _commit_blob(root, head, TERMINAL_PATH)
    _require(committed == raw, "D-135 committed terminal bytes differ")
    return {
        "commit": head,
        "tree": identity["tree"],
        "parents": identity["parents"],
        "artifact_path": TERMINAL_PATH.as_posix(),
        "artifact_blob_oid": oid,
        "artifact_file_sha256": sha256_bytes(raw),
        "artifact_file_bytes": len(raw),
        "single_artifact_add_commit": True,
    }


def validate_d135_procedural_terminal(
    *,
    repository: str | Path | None = None,
    mode: Literal["current-gate", "post-terminal-commit"] = "current-gate",
) -> dict[str, Any]:
    """Replay the procedural terminal without network or helper calls."""

    root = _repo_root(repository)
    _assert_runtime_import_boundary(root)
    payload, raw = _read_json(root, TERMINAL_PATH)
    body = _validate_terminal_payload(root, payload, raw)
    commit = None
    if mode == "current-gate":
        evidence_commit = body["d135_gate_binding"]["evidence_commit_binding"]["commit"]
        _require(
            _head(root) == evidence_commit
            and _status_lines(root) == [f"?? {TERMINAL_PATH.as_posix()}"],
            "D-135 pending terminal checkout differs",
        )
    elif mode == "post-terminal-commit":
        commit = _terminal_commit_binding(root, payload=payload, raw=raw)
    else:
        raise D135PricingConsumedIncidentError("D-135 terminal validation mode differs")
    return {
        "artifact_id": payload["artifact_id"],
        "semantic_body_hash": payload["semantic_body_hash"],
        "file_sha256": sha256_bytes(raw),
        "file_bytes": len(raw),
        "status": body["status"],
        "terminal_commit": commit,
        "external_call_count": 0,
    }


def render_d135_terminalization_approval_template(*, repository: str | Path | None = None) -> str:
    """Render the future terminal-only approval after the gate evidence commit."""

    root = _repo_root(repository)
    result = validate_d135_corrected_offline_source_gate(
        repository=root, mode="post-evidence-commit"
    )
    payload, raw = _read_json(root, GATE_PATH)
    evidence = result["evidence_commit"]
    _require(isinstance(evidence, dict), "D-135 evidence commit differs")
    lines = [
        "D-135 D-132 pricing consumed-incident procedural-terminal exact approval",
        "(local only; external actions zero)",
        "",
        f"Gate ID: {payload['gate_id']}",
        f"Gate body SHA: {payload['semantic_body_hash']}",
        f"Gate file SHA: {sha256_bytes(raw)}",
        f"Gate file bytes: {len(raw)}",
        f"Gate evidence commit tuple: {canonical_json(evidence)}",
        "",
        "Approved local-only scope:",
        *[f"- {value}" for value in TERMINALIZATION_SCOPE],
        "",
        "Explicitly not approved:",
        *[f"- {value}" for value in TERMINALIZATION_EXCLUSIONS],
        "",
        "The terminal is procedural incident preservation, not canonical pricing evidence.",
        "A later D-135 fixed successor requires a separate offline source approval.",
        "This rendered template is not approval; a new exact user message is required.",
    ]
    return "\n".join(lines)


__all__ = [
    "D135PricingConsumedIncidentError",
    "GATE_PATH",
    "GATE_SCHEMA",
    "GATE_STATUS",
    "TERMINAL_PATH",
    "TERMINAL_SCHEMA",
    "TERMINAL_STATUS",
    "create_d135_procedural_terminal",
    "render_d135_terminalization_approval_template",
    "run_d135_corrected_offline_source_gate",
    "validate_d135_corrected_offline_source_gate",
    "validate_d135_procedural_terminal",
]
