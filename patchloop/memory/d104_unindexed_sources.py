"""D-104 exact unindexed memory-rule source materialization.

The D-103 seal admits three D-100 projected templates.  This module copies
those exact sealed templates and their provenance into strict, portable source
records.  It deliberately does not invent ``MemoryEntry.index_version``, call
the legacy per-failure builder, create embeddings, build or freeze an index, or
enable retrieval/core experiments.
"""

from __future__ import annotations

import json
import os
import re
import unicodedata
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, ValidationError

from patchloop.contracts import D100ProjectedEntry, StrictModel
from patchloop.errors import ContractError
from patchloop.memory import d103_exact_candidate_admission as d103
from patchloop.util import canonical_json, sha256_bytes, sha256_text

SOURCE_SCHEMA_VERSION = "unindexed-memory-entry-source-d104-v1"
SOURCE_COLLECTION_SCHEMA_VERSION = "unindexed-memory-source-collection-d104-v1"
GATE_SCHEMA_VERSION = "unindexed-memory-source-materialization-gate-d104-v1"
SOURCE_PROJECTION_POLICY = "d103-seal-admitted-template-exact-v1"
MATERIALIZED_AT = "2026-08-06T04:00:00Z"

DEFAULT_SOURCE_DIRECTORY = Path("reports/memory-development/sources/d104")
DEFAULT_GATE_PATH = Path(
    "reports/memory-development/d104-three-rule-source-materialization-gate.json"
)

EXPECTED_D103_GATE_BYTES = 5_315
EXPECTED_D103_GATE_BODY_SHA = (
    "sha256:4a542cd571ffc0b94b6f95e106fd2371425dd66f82cfa6091cc602905036fb1f"
)
EXPECTED_D103_GATE_FILE_SHA = (
    "sha256:4602a579d7c11dd300e2f9bede38e8a6d7bf21c78a8fbfc255550b7d86f3d354"
)

SOURCE_IMPLEMENTATION_PATHS = (
    Path("patchloop/memory/d104_unindexed_sources.py"),
    Path("scripts/build_d104_unindexed_sources.py"),
    Path("tests/test_d104_unindexed_sources.py"),
)

_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
_SOURCE_ID = re.compile(r"^d104src_[0-9a-f]{64}$")
_COLLECTION_ID = re.compile(r"^d104collection_[0-9a-f]{64}$")
_CONTROL_OR_DIRECTIONAL = re.compile(
    r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\u200b-\u200f\u202a-\u202e\u2060-\u2069\ufeff]"
)
_LEAK_PATTERNS = (
    re.compile(r"(?i)diff\s+--git\s"),
    re.compile(r"(?m)^\s*@@(?:\s|$)"),
    re.compile(r"(?mi)^\s*(?:\+\+\+|---)\s+(?:[ab]/|/dev/null)"),
    re.compile(r"(?mi)^\s*(?:index\s+[0-9a-f]+\.\.[0-9a-f]+|new file mode|deleted file mode)"),
    re.compile(r"```"),
    re.compile(r"(?m)^\s*(?:async\s+)?def\s+[A-Za-z_]\w*\s*\("),
    re.compile(r"(?m)^\s*class\s+[A-Za-z_]\w*(?:\([^)]*\))?\s*:"),
    re.compile(r"(?i)\breference(?:[-_/ ]?(?:patch|solution))?\b(?:\.patch)?"),
    re.compile(r"(?i)\b(?:solution|gold|golden|answer)[-_/ ]?patch\b"),
    re.compile(r"(?i)(?:^|[/\\])(?:reference|solution|golden?|answers?)(?:[/\\]|$)"),
    re.compile(r"(?i)\bprivate\.(?:ya?ml|json|py)\b"),
    re.compile(r"(?i)\btask-private-v\d+\b"),
    re.compile(r"(?i)\.patchloop-hidden(?:[/\\]|$)"),
    re.compile(r"(?i)(?:^|[/\\])(?:hidden|private)(?:[/\\]|$)"),
    re.compile(
        r"(?i)\b(?:hidden[_ -]?tests?|test[_ -]?hidden|hidden[_ -]?check|"
        r"hidden[_ -]?acceptance|private[_ -]?assertion|acceptance[_ -]?assertion)\b"
    ),
    re.compile(r"(?i)\b(?:known[-_ ]?bad|bad[-_ ]?patch|evaluator[_ -]?(?:payload|assertion))\b"),
    re.compile(r"(?i)\b(?:OPENAI_API_KEY|[A-Z][A-Z0-9_]*(?:TOKEN|SECRET|PASSWORD|API_KEY))\s*[:=]"),
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._-]{12,}\b"),
    re.compile(r"(?i)\b(?:sk-(?:proj-)?|github_pat_|ghp_)[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"(?i)\b[A-Z]:/Users/"),
    re.compile(r"(?i)(?:^|\s)/(?:home|Users)/[^/\s]+/"),
    re.compile(r"(?i)(?:^|[/\\])\.env(?:$|[/\\.])"),
)


class D104SourceError(ContractError):
    """Stable, non-echoing D-104 source validation error."""


class D104AdmissionSealBinding(StrictModel):
    path: str
    schema_version: Literal["memory-group-admission-seal-d101-v1"]
    seal_id: str = Field(pattern=r"^d101seal_[0-9a-f]{64}$")
    semantic_body_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    file_bytes: int = Field(ge=1)
    file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class D104SourceAuthority(StrictModel):
    source_record_materialized: Literal[True]
    unindexed_source_record: Literal[True]
    source_schema_validated: Literal[True]
    source_provenance_validated: Literal[True]
    source_leak_scan_passed: Literal[True]
    actual_memory_entry_created: Literal[False]
    index_version_assigned: Literal[False]
    rendered_memory_created: Literal[False]
    embedding_created: Literal[False]
    memory_index_build_authorized: Literal[False]
    memory_index_built: Literal[False]
    memory_index_frozen: Literal[False]
    retrieval_ready: Literal[False]
    core_campaign_unlocked: Literal[False]
    analysis_ready: Literal[False]


class D104SourceBody(StrictModel):
    milestone: Literal["D-104"]
    evidence_kind: Literal["sealed-group-unindexed-memory-source"]
    materialized_at: Literal["2026-08-06T04:00:00Z"]
    source_collection_id: str = Field(pattern=r"^d104collection_[0-9a-f]{64}$")
    source_projection_policy: Literal["d103-seal-admitted-template-exact-v1"]
    admission_seal: D104AdmissionSealBinding
    projected_entry: D100ProjectedEntry
    leak_scan_passed: Literal[True]
    authority: D104SourceAuthority


class D104SourceRecord(StrictModel):
    schema_version: Literal["unindexed-memory-entry-source-d104-v1"]
    source_id: str = Field(pattern=r"^d104src_[0-9a-f]{64}$")
    semantic_body_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    semantic_body: D104SourceBody


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise D104SourceError(message)


def _is_linklike(path: Path) -> bool:
    if path.is_symlink():
        return True
    is_junction = getattr(os.path, "isjunction", None)
    return bool(is_junction(path)) if is_junction is not None else False


def _lexical(path: str | Path, *, repository: Path) -> Path:
    selected = Path(path)
    return selected.absolute() if selected.is_absolute() else (repository / selected).absolute()


def _require_unlinked_components(path: Path, *, label: str) -> None:
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        _require(
            not _is_linklike(current),
            f"D-104 {label} cannot contain a link or junction",
        )


def _repo_root(repository: str | Path | None) -> Path:
    selected = (
        Path(repository).absolute()
        if repository is not None
        else Path(__file__).absolute().parents[2]
    )
    _require_unlinked_components(selected, label="repository root")
    resolved = selected.resolve()
    _require(resolved.is_dir(), "D-104 repository root is unavailable")
    return resolved


def _resolved(
    path: str | Path,
    *,
    repository: Path,
    label: str = "path",
    require_within_repository: bool = False,
) -> Path:
    selected = _lexical(path, repository=repository)
    _require_unlinked_components(selected, label=label)
    resolved = selected.resolve()
    if require_within_repository:
        try:
            resolved.relative_to(repository)
        except ValueError as exc:
            raise D104SourceError(f"D-104 {label} must stay within the repository") from exc
    return resolved


def _read_stable(path: Path, *, label: str) -> bytes:
    _require(not _is_linklike(path), f"D-104 {label} cannot be a link or junction")
    try:
        first = path.read_bytes()
        second = path.read_bytes()
    except OSError as exc:
        raise D104SourceError(f"D-104 {label} is unavailable") from exc
    _require(first == second, f"D-104 {label} changed while being read")
    return first


def _read_exact(
    path: str | Path,
    *,
    repository: Path,
    expected_bytes: int,
    expected_sha256: str,
    label: str,
) -> tuple[Path, bytes]:
    selected = _resolved(
        path,
        repository=repository,
        label=label,
        require_within_repository=True,
    )
    content = _read_stable(selected, label=label)
    _require(len(content) == expected_bytes, f"D-104 {label} byte count drifted")
    _require(sha256_bytes(content) == expected_sha256, f"D-104 {label} file hash drifted")
    return selected, content


def _parse_json(content: bytes, *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise D104SourceError(f"D-104 {label} JSON is invalid") from exc
    _require(isinstance(payload, dict), f"D-104 {label} JSON root is invalid")
    return payload


def _source_binding(path: Path, *, repository: Path) -> dict[str, Any]:
    selected = _resolved(
        path,
        repository=repository,
        label="source implementation",
        require_within_repository=True,
    )
    content = _read_stable(selected, label="source implementation")
    return {
        "path": selected.relative_to(repository).as_posix(),
        "file_bytes": len(content),
        "file_sha256": sha256_bytes(content),
    }


def _normalize_text(value: str) -> str:
    return unicodedata.normalize("NFKC", value).replace("\\", "/")


def validate_d104_text_leak_safe(value: str, *, label: str = "source text") -> None:
    """Reject leak- or code-shaped text without echoing the matched value."""

    normalized = _normalize_text(value)
    if _CONTROL_OR_DIRECTIONAL.search(normalized) or any(
        pattern.search(normalized) for pattern in _LEAK_PATTERNS
    ):
        raise D104SourceError(f"D-104 {label} leak scan failed")


def _template_text_values(projected: D100ProjectedEntry) -> list[str]:
    template = projected.template
    pattern = template.failure_pattern
    return [
        pattern.failure_class,
        pattern.phase.value,
        pattern.description,
        *template.preconditions,
        *template.diagnostic_evidence,
        *template.recommended_actions,
        *template.do_not_apply_when,
        *template.applicable_languages,
    ]


def _validate_projected_entry(projected: D100ProjectedEntry) -> None:
    template_payload = projected.template.model_dump(mode="json")
    _require(
        sha256_text(canonical_json(template_payload)) == projected.template_hash,
        "D-104 projected template hash drifted",
    )
    _require(
        projected.template.validation_count == 0,
        "D-104 source validation count must remain zero",
    )
    for value in _template_text_values(projected):
        validate_d104_text_leak_safe(value)


def _load_exact_d103(
    *,
    repository: Path,
    d103_gate_path: str | Path = d103.DEFAULT_GATE_PATH,
    seal_path: str | Path = d103.DEFAULT_SEAL_PATH,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    gate, gate_content = _read_exact(
        d103_gate_path,
        repository=repository,
        expected_bytes=EXPECTED_D103_GATE_BYTES,
        expected_sha256=EXPECTED_D103_GATE_FILE_SHA,
        label="D-103 gate",
    )
    gate_result = d103.validate_d103_exact_admission_gate(gate, repository=repository)
    _require(
        gate_result["semantic_body_hash"] == EXPECTED_D103_GATE_BODY_SHA,
        "D-104 D-103 gate identity drifted",
    )

    seal, seal_content = _read_exact(
        seal_path,
        repository=repository,
        expected_bytes=d103.EXPECTED_SEAL_BYTES,
        expected_sha256=d103.EXPECTED_SEAL_FILE_SHA,
        label="D-103 admission seal",
    )
    admission_result = d103.validate_d103_exact_admission(
        repository=repository,
        seal_path=seal,
    )
    seal_payload = _parse_json(seal_content, label="D-103 admission seal")
    _require(
        gate_content == _read_stable(gate, label="D-103 gate"),
        "D-104 D-103 gate changed during validation",
    )
    _require(
        seal_content == _read_stable(seal, label="D-103 admission seal"),
        "D-104 D-103 admission seal changed during validation",
    )
    return gate_result, admission_result, seal_payload


def _seal_binding(seal_payload: dict[str, Any]) -> D104AdmissionSealBinding:
    content = (json.dumps(seal_payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    return D104AdmissionSealBinding(
        path=d103.DEFAULT_SEAL_PATH.as_posix(),
        schema_version=seal_payload["schema_version"],
        seal_id=seal_payload["seal_id"],
        semantic_body_hash=seal_payload["semantic_body_hash"],
        file_bytes=len(content),
        file_sha256=sha256_bytes(content),
    )


def _collection_id(admitted_entries: list[dict[str, Any]], seal_payload: dict[str, Any]) -> str:
    basis = {
        "schema_version": SOURCE_COLLECTION_SCHEMA_VERSION,
        "d103_gate_semantic_body_hash": EXPECTED_D103_GATE_BODY_SHA,
        "admission_seal_semantic_body_hash": seal_payload["semantic_body_hash"],
        "ordered_template_hashes": [entry["template_hash"] for entry in admitted_entries],
    }
    digest = sha256_text(canonical_json(basis)).removeprefix("sha256:")
    return f"d104collection_{digest}"


def encode_d104_source(source: D104SourceRecord | dict[str, Any]) -> bytes:
    payload = source.model_dump(mode="json") if isinstance(source, D104SourceRecord) else source
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _source_record(
    *,
    projected: D100ProjectedEntry,
    collection_id: str,
    seal_binding: D104AdmissionSealBinding,
) -> D104SourceRecord:
    _validate_projected_entry(projected)
    body = D104SourceBody(
        milestone="D-104",
        evidence_kind="sealed-group-unindexed-memory-source",
        materialized_at=MATERIALIZED_AT,
        source_collection_id=collection_id,
        source_projection_policy=SOURCE_PROJECTION_POLICY,
        admission_seal=seal_binding,
        projected_entry=projected,
        leak_scan_passed=True,
        authority=D104SourceAuthority(
            source_record_materialized=True,
            unindexed_source_record=True,
            source_schema_validated=True,
            source_provenance_validated=True,
            source_leak_scan_passed=True,
            actual_memory_entry_created=False,
            index_version_assigned=False,
            rendered_memory_created=False,
            embedding_created=False,
            memory_index_build_authorized=False,
            memory_index_built=False,
            memory_index_frozen=False,
            retrieval_ready=False,
            core_campaign_unlocked=False,
            analysis_ready=False,
        ),
    )
    body_hash = sha256_text(canonical_json(body.model_dump(mode="json")))
    return D104SourceRecord(
        schema_version=SOURCE_SCHEMA_VERSION,
        source_id=f"d104src_{body_hash.removeprefix('sha256:')}",
        semantic_body_hash=body_hash,
        semantic_body=body,
    )


def _expected_sources(
    *,
    repository: Path,
    d103_gate_path: str | Path = d103.DEFAULT_GATE_PATH,
    seal_path: str | Path = d103.DEFAULT_SEAL_PATH,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    gate_result, admission_result, seal_payload = _load_exact_d103(
        repository=repository,
        d103_gate_path=d103_gate_path,
        seal_path=seal_path,
    )
    seal_body = seal_payload["semantic_body"]
    admitted_raw = seal_body["admitted_entries"]
    _require(len(admitted_raw) == 3, "D-104 admitted source count drifted")
    collection_id = _collection_id(admitted_raw, seal_payload)
    _require(_COLLECTION_ID.fullmatch(collection_id) is not None, "D-104 collection ID is invalid")
    seal_binding = _seal_binding(seal_payload)

    records: list[dict[str, Any]] = []
    for order, raw in enumerate(admitted_raw, start=1):
        try:
            projected = D100ProjectedEntry.model_validate(raw)
        except ValidationError as exc:
            raise D104SourceError("D-104 sealed projected entry schema is invalid") from exc
        source = _source_record(
            projected=projected,
            collection_id=collection_id,
            seal_binding=seal_binding,
        )
        source_content = encode_d104_source(source)
        logical_path = DEFAULT_SOURCE_DIRECTORY / f"{projected.template.proposed_memory_id}.json"
        records.append(
            {
                "order": order,
                "logical_path": logical_path,
                "source": source,
                "content": source_content,
                "projected_entry": projected,
            }
        )

    expected_groups = [row["semantic_group_id"] for row in d103.EXPECTED_ADMITTED_GROUPS]
    actual_groups = [record["projected_entry"].provenance.semantic_group_id for record in records]
    _require(actual_groups == expected_groups, "D-104 admitted source order drifted")
    held_groups = [
        decision["semantic_group_id"]
        for decision in seal_body["effective_decisions"]
        if decision["decision"] == "continue_hold"
    ]
    _require(
        held_groups == list(d103.EXPECTED_HELD_GROUPS),
        "D-104 held group boundary drifted",
    )

    source_runs = [
        run_id for record in records for run_id in record["projected_entry"].template.source_run_ids
    ]
    source_failures = [
        failure_id
        for record in records
        for failure_id in record["projected_entry"].provenance.source_failure_ids
    ]
    _require(
        len(source_runs) == len(set(source_runs)) == 6,
        "D-104 source run provenance is not exact and unique",
    )
    _require(
        len(source_failures) == len(set(source_failures)) == 6,
        "D-104 source failure provenance is not exact and unique",
    )
    predecessor = {
        "path": d103.DEFAULT_GATE_PATH.as_posix(),
        "schema_version": gate_result["schema_version"],
        "gate_id": gate_result["gate_id"],
        "semantic_body_hash": gate_result["semantic_body_hash"],
        "file_bytes": gate_result["gate_file_bytes"],
        "file_sha256": gate_result["gate_file_sha256"],
    }
    source_set = {
        "source_collection_id": collection_id,
        "admission_seal": seal_binding.model_dump(mode="json"),
        "held_group_ids": held_groups,
        "admission_result": admission_result,
    }
    return predecessor, source_set, records


def write_d104_new_exact(
    path: str | Path,
    content: bytes,
    *,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    """Exclusively create a source artifact, allowing only exact retries."""

    selected = Path(path)
    repo = _repo_root(repository) if repository is not None else None
    if repo is not None:
        selected = _resolved(
            selected,
            repository=repo,
            label="source output",
            require_within_repository=True,
        )
    selected.parent.mkdir(parents=True, exist_ok=True)
    if repo is not None:
        selected = _resolved(
            selected,
            repository=repo,
            label="source output",
            require_within_repository=True,
        )
    try:
        with selected.open("xb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        return {
            "created": True,
            "idempotent_retry": False,
            "file_bytes": len(content),
            "file_sha256": sha256_bytes(content),
        }
    except FileExistsError:
        existing = _read_stable(selected, label="existing source output")
        _require(existing == content, "D-104 output exists with different exact bytes")
        return {
            "created": False,
            "idempotent_retry": True,
            "file_bytes": len(existing),
            "file_sha256": sha256_bytes(existing),
        }


def materialize_d104_sources(
    *,
    repository: str | Path | None = None,
    source_directory: str | Path = DEFAULT_SOURCE_DIRECTORY,
) -> dict[str, Any]:
    """Write exactly three sealed, unindexed source records."""

    repo = _repo_root(repository)
    directory = _resolved(
        source_directory,
        repository=repo,
        label="source directory",
        require_within_repository=True,
    )
    _, source_set, records = _expected_sources(repository=repo)
    writes = []
    for record in records:
        target = directory / record["logical_path"].name
        write = write_d104_new_exact(target, record["content"], repository=repo)
        writes.append({"path": str(target), **write})
    validation = validate_d104_materialized_sources(
        repository=repo,
        source_directory=directory,
    )
    return {
        "source_collection_id": source_set["source_collection_id"],
        "writes": writes,
        **validation,
    }


def validate_d104_materialized_sources(
    *,
    repository: str | Path | None = None,
    source_directory: str | Path = DEFAULT_SOURCE_DIRECTORY,
) -> dict[str, Any]:
    """Read-only exact validation of the three materialized sources."""

    repo = _repo_root(repository)
    directory = _resolved(source_directory, repository=repo, label="source directory")
    _require(directory.is_dir(), "D-104 source directory is unavailable")
    predecessor, source_set, records = _expected_sources(repository=repo)
    expected_names = [record["logical_path"].name for record in records]
    actual_paths = sorted(directory.iterdir(), key=lambda path: path.name)
    _require(
        [path.name for path in actual_paths] == sorted(expected_names)
        and all(path.is_file() and not _is_linklike(path) for path in actual_paths),
        "D-104 source file set is incomplete or contains extras",
    )

    descriptors: list[dict[str, Any]] = []
    for record in records:
        selected = directory / record["logical_path"].name
        content = _read_stable(selected, label="materialized source")
        _require(content == record["content"], "D-104 materialized source exact bytes drifted")
        try:
            source = D104SourceRecord.model_validate_json(content)
        except ValidationError as exc:
            raise D104SourceError("D-104 materialized source schema is invalid") from exc
        _require(content == encode_d104_source(source), "D-104 source is not canonical JSON")
        body_hash = sha256_text(canonical_json(source.semantic_body.model_dump(mode="json")))
        _require(
            source.semantic_body_hash == body_hash
            and source.source_id == f"d104src_{body_hash.removeprefix('sha256:')}",
            "D-104 source content identity drifted",
        )
        _validate_projected_entry(source.semantic_body.projected_entry)
        projected = source.semantic_body.projected_entry
        descriptors.append(
            {
                "order": record["order"],
                "path": record["logical_path"].as_posix(),
                "source_id": source.source_id,
                "semantic_body_hash": source.semantic_body_hash,
                "file_bytes": len(content),
                "file_sha256": sha256_bytes(content),
                "semantic_group_id": projected.provenance.semantic_group_id,
                "semantic_group_fingerprint": projected.provenance.semantic_group_fingerprint,
                "decision_hash": projected.provenance.decision_hash,
                "template_hash": projected.template_hash,
                "proposed_memory_id": projected.template.proposed_memory_id,
                "target_schema": projected.template.target_schema,
                "source_run_ids": projected.template.source_run_ids,
                "source_failure_ids": projected.provenance.source_failure_ids,
                "evidence_ref_ids": projected.provenance.evidence_ref_ids,
                "dedup_confidence": projected.provenance.dedup_confidence,
                "validation_count": projected.template.validation_count,
            }
        )

    ordered_hashes = [descriptor["file_sha256"] for descriptor in descriptors]
    source_set_hash = sha256_text(
        canonical_json(
            {
                "source_collection_id": source_set["source_collection_id"],
                "ordered_source_file_hashes": ordered_hashes,
            }
        )
    )
    return {
        "d103_gate": predecessor,
        "admission_seal": source_set["admission_seal"],
        "source_collection_id": source_set["source_collection_id"],
        "source_set_hash": source_set_hash,
        "entries": descriptors,
        "held_group_ids": source_set["held_group_ids"],
        "materialized_rule_source_count": len(descriptors),
        "actual_memory_entry_count": 0,
        "schema_validation": "pass",
        "provenance_validation": "pass",
        "leak_scan": "pass",
    }


def build_d104_source_gate(
    *,
    repository: str | Path | None = None,
    source_directory: str | Path = DEFAULT_SOURCE_DIRECTORY,
) -> dict[str, Any]:
    """Build deterministic D-104 source-only authority evidence."""

    repo = _repo_root(repository)
    _require(
        _resolved(
            source_directory,
            repository=repo,
            label="source directory",
            require_within_repository=True,
        )
        == _resolved(
            DEFAULT_SOURCE_DIRECTORY,
            repository=repo,
            label="canonical source directory",
            require_within_repository=True,
        ),
        "D-104 gate must bind the canonical source directory",
    )
    evidence = validate_d104_materialized_sources(
        repository=repo,
        source_directory=source_directory,
    )
    body = {
        "milestone": "D-104",
        "evidence_kind": "three-rule-unindexed-source-materialization-gate",
        "recorded_at": MATERIALIZED_AT,
        **evidence,
        "source_projection_policy": SOURCE_PROJECTION_POLICY,
        "implementation_files": [
            _source_binding(path, repository=repo) for path in SOURCE_IMPLEMENTATION_PATHS
        ],
        "evidence_boundary": {
            "portable_validation_mode": True,
            "semantic_authoring_source": "exact-d103-seal-admitted-templates-only",
            "inherited_public_submitted_patch_integrity_revalidated": True,
            "public_patch_text_copied_into_sources": False,
            "new_rule_semantics_authored_from_patch_text": False,
            "raw_sqlite_or_event_bodies_read": False,
            "raw_trace_or_search_read_artifact_bodies_read": False,
            "private_task_or_hidden_test_bodies_read": False,
            "reference_solution_patch_read": False,
            "evaluator_payload_bodies_read": False,
            "provider_request_or_response_bodies_read": False,
        },
        "authority": {
            "d103_exact_admission_revalidated": True,
            "admitted_rule_count": 3,
            "materialized_rule_source_count": 3,
            "admitted_source_set_complete": True,
            "held_group_count": 2,
            "held_group_materialized_count": 0,
            "full_five_group_review_finalized": False,
            "source_schema_validated": True,
            "source_provenance_validated": True,
            "source_leak_scan_passed": True,
            "source_validation_count": 0,
            "memory_admission_unlocked": True,
            "memory_index_source_authoring_unlocked": True,
            "actual_memory_entry_count": 0,
            "render_policy_frozen": False,
            "rendered_memory_count": 0,
            "embedding_count": 0,
            "d104_created_index_count": 0,
            "legacy_failure_memory_builder_connected": False,
            "historical_index_state_inspected": False,
            "historical_index_state_modified": False,
            "memory_index_build_authorized": False,
            "memory_index_built": False,
            "memory_index_frozen": False,
            "retrieval_ready": False,
            "core_campaign_unlocked": False,
            "analysis_ready": False,
            "memory_effect_established": False,
            "negative_transfer_established": False,
            "exact_hidden_cause_established": False,
            "provider_calls_made": 0,
            "evaluator_calls_made": 0,
            "added_model_cost_usd": 0,
        },
        "next_gate": (
            "deterministic-model-facing-renderer-token-budget-and-pinned-embedding-"
            "index-build-authorization"
        ),
    }
    body_hash = sha256_text(canonical_json(body))
    return {
        "schema_version": GATE_SCHEMA_VERSION,
        "gate_id": f"d104_{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": body,
    }


def encode_d104_gate(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def validate_d104_source_gate(
    gate_path: str | Path = DEFAULT_GATE_PATH,
    *,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    """Read-only exact rebuild of the checked-in D-104 gate."""

    repo = _repo_root(repository)
    selected = _resolved(gate_path, repository=repo, label="source materialization gate")
    content = _read_stable(selected, label="source materialization gate")
    try:
        parsed = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise D104SourceError("D-104 source materialization gate JSON is invalid") from exc
    expected = build_d104_source_gate(repository=repo)
    expected_content = encode_d104_gate(expected)
    _require(content == expected_content, "D-104 gate exact bytes drifted")
    _require(parsed == expected, "D-104 gate semantic content drifted")
    authority = expected["semantic_body"]["authority"]
    return {
        "ok": True,
        "schema_version": expected["schema_version"],
        "gate_id": expected["gate_id"],
        "semantic_body_hash": expected["semantic_body_hash"],
        "gate_file_bytes": len(content),
        "gate_file_sha256": sha256_bytes(content),
        "source_collection_id": expected["semantic_body"]["source_collection_id"],
        "source_set_hash": expected["semantic_body"]["source_set_hash"],
        "materialized_rule_source_count": authority["materialized_rule_source_count"],
        "actual_memory_entry_count": authority["actual_memory_entry_count"],
        "held_group_count": authority["held_group_count"],
        "memory_index_build_authorized": authority["memory_index_build_authorized"],
        "core_campaign_unlocked": authority["core_campaign_unlocked"],
        "gate_validation": "pass",
    }
