"""D-105 deterministic memory rendering and index-build authorization source gate.

This module projects the three exact D-104 unindexed sources into plain text
that may later be shown to a model.  It freezes the rendering and prospective
budget/index-build contracts without importing an embedding model, creating a
runtime ``MemoryEntry``, writing an index, enabling retrieval, or calling a
provider/evaluator.
"""

from __future__ import annotations

import json
import os
import re
import tomllib
import unicodedata
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from patchloop.errors import ContractError
from patchloop.memory import d104_unindexed_sources as d104
from patchloop.util import canonical_json, sha256_bytes, sha256_text

GATE_SCHEMA_VERSION = "memory-render-index-authorization-source-gate-d105-v1"
RENDER_POLICY_VERSION = "model-facing-memory-render-d105-v1"
TOKEN_POLICY_VERSION = "provider-memory-delta-budget-d105-v1"
INDEX_PLAN_VERSION = "group-aware-index-build-plan-d105-v1"
RECORDED_AT = "2026-08-06T05:30:00Z"

DEFAULT_RENDER_DIRECTORY = Path("reports/memory-development/rendered/d105")
DEFAULT_GATE_PATH = Path(
    "reports/memory-development/d105-renderer-embedding-index-authorization-gate.json"
)

EXPECTED_D104_GATE_BYTES = 12_705
EXPECTED_D104_GATE_BODY_SHA = (
    "sha256:61e44eb5609c05c97b84602bbaa4eb7bff84dd33af227cef18592aa2b6a32c11"
)
EXPECTED_D104_GATE_FILE_SHA = (
    "sha256:8eeb26d6f5e0ff22658501afe54bd8cebe35896dc18b60f8f73355ec53190dd0"
)

OPENAI_MODEL_ID = "gpt-5.4-mini-2026-03-17"
MEMORY_TOKEN_LIMIT = 2_000
TOKEN_COUNT_ENDPOINT = "responses.input_tokens.count"
RENDER_SEPARATOR = "\n\n---\n\n"

EMBEDDING_MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_MODEL_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
EMBEDDING_MODEL_API_URL = "https://huggingface.co/api/models/sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_COMMIT_URL = (
    "https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/commit/"
    f"{EMBEDDING_MODEL_REVISION}"
)
EMBEDDING_REVISION_OBSERVED_AT = "2026-08-06T05:15:00Z"
EMBEDDING_UPSTREAM_LAST_MODIFIED = "2026-06-01T06:29:13Z"

IMPLEMENTATION_PATHS = (
    Path("patchloop/memory/d105_renderer_authorization.py"),
    Path("scripts/build_d105_renderer_authorization_gate.py"),
    Path("tests/test_d105_renderer_authorization.py"),
)

MODEL_VISIBLE_FIELDS = (
    "failure_pattern.failure_class",
    "failure_pattern.phase",
    "failure_pattern.description",
    "preconditions",
    "diagnostic_evidence",
    "recommended_actions",
    "do_not_apply_when",
    "applicable_languages",
)
MODEL_EXCLUDED_FIELDS = (
    "proposed_memory_id",
    "source_run_ids",
    "source_failure_ids",
    "evidence_ref_ids",
    "semantic_group_id",
    "semantic_group_fingerprint",
    "decision_hash",
    "template_hash",
    "source_id",
    "semantic_body_hash",
    "admission_seal",
    "confidence",
    "dedup_confidence",
    "validation_count",
    "local_paths",
)

_FULL_REVISION = re.compile(r"^[0-9a-f]{40}$")
_SAFE_VISIBLE_LINE = re.compile(r"^[\x20-\x7e]+$")
_MODEL_TEXT_FORBIDDEN = (
    re.compile(r"(?i)\bsha256:"),
    re.compile(r"(?i)\b(?:d104src|memgrp|run|fail)_[a-z0-9_]+\b"),
    re.compile(r"(?i)\b(?:source|failure|template|decision)_id\b"),
    re.compile(r"(?i)\bprivate(?:\.|[/\\]|[_ -](?:test|assertion))"),
    re.compile(r"(?i)\bhidden(?:[/\\]|[_ -](?:test|acceptance|assertion))"),
    re.compile(r"(?i)\breference(?:\.patch|[/\\]|[_ -](?:patch|solution))"),
    re.compile(r"(?i)diff\s+--git"),
    re.compile(r"(?m)^\s*@@(?:\s|$)"),
    re.compile(r"```"),
    re.compile(r"(?m)^\s*(?:async\s+)?def\s+[A-Za-z_]\w*\s*\("),
    re.compile(r"(?m)^\s*class\s+[A-Za-z_]\w*"),
)


class D105SourceError(ContractError):
    """Stable, non-echoing D-105 validation error."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise D105SourceError(message)


def _is_linklike(path: Path) -> bool:
    if path.is_symlink():
        return True
    is_junction = getattr(os.path, "isjunction", None)
    return bool(is_junction(path)) if is_junction is not None else False


def _require_unlinked_components(path: Path, *, label: str) -> None:
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        _require(
            not _is_linklike(current),
            f"D-105 {label} cannot contain a link or junction",
        )


def _repo_root(repository: str | Path | None) -> Path:
    selected = (
        Path(repository).absolute()
        if repository is not None
        else Path(__file__).absolute().parents[2]
    )
    _require_unlinked_components(selected, label="repository root")
    resolved = selected.resolve()
    _require(resolved.is_dir(), "D-105 repository root is unavailable")
    return resolved


def _lexical(path: str | Path, *, repository: Path) -> Path:
    selected = Path(path)
    return selected.absolute() if selected.is_absolute() else (repository / selected).absolute()


def _resolved(
    path: str | Path,
    *,
    repository: Path,
    label: str,
    require_within_repository: bool = False,
) -> Path:
    selected = _lexical(path, repository=repository)
    _require_unlinked_components(selected, label=label)
    resolved = selected.resolve()
    if require_within_repository:
        try:
            resolved.relative_to(repository)
        except ValueError as exc:
            raise D105SourceError(f"D-105 {label} must stay within the repository") from exc
    return resolved


def _require_exact_gate_path(
    path: str | Path,
    *,
    canonical: Path,
    repository: Path,
    label: str,
) -> None:
    selected = Path(path)
    if selected.is_absolute():
        expected = (repository / canonical).absolute()
        _require(selected == expected, f"D-105 gate must bind the exact canonical {label}")
    else:
        _require(
            selected.as_posix() == canonical.as_posix(),
            f"D-105 gate must bind the exact canonical {label}",
        )


def _read_stable(path: Path, *, label: str) -> bytes:
    _require(not _is_linklike(path), f"D-105 {label} cannot be a link or junction")
    try:
        first = path.read_bytes()
        second = path.read_bytes()
    except OSError as exc:
        raise D105SourceError(f"D-105 {label} is unavailable") from exc
    _require(first == second, f"D-105 {label} changed while being read")
    return first


def _file_binding(path: str | Path, *, repository: Path, label: str) -> dict[str, Any]:
    selected = _resolved(
        path,
        repository=repository,
        label=label,
        require_within_repository=True,
    )
    content = _read_stable(selected, label=label)
    return {
        "path": selected.relative_to(repository).as_posix(),
        "file_bytes": len(content),
        "file_sha256": sha256_bytes(content),
    }


def _parse_json(content: bytes, *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise D105SourceError(f"D-105 {label} JSON is invalid") from exc
    _require(isinstance(payload, dict), f"D-105 {label} JSON root is invalid")
    return payload


def _safe_visible(value: str, *, label: str) -> str:
    _require(isinstance(value, str), f"D-105 {label} is not text")
    _require(value == unicodedata.normalize("NFKC", value), f"D-105 {label} is not NFKC")
    _require("\r" not in value and "\n" not in value, f"D-105 {label} contains a newline")
    _require(_SAFE_VISIBLE_LINE.fullmatch(value) is not None, f"D-105 {label} is not ASCII")
    d104.validate_d104_text_leak_safe(value, label=f"D-105 {label}")
    _require(
        not any(pattern.search(value) for pattern in _MODEL_TEXT_FORBIDDEN),
        f"D-105 {label} contains model-excluded provenance or code shape",
    )
    return value


def _render_list(label: str, values: list[str]) -> list[str]:
    _require(values, f"D-105 {label} list is empty")
    return [f"- {_safe_visible(value, label=label)}" for value in values]


def _validate_source_integrity(source: d104.D104SourceRecord) -> None:
    _require(
        isinstance(source, d104.D104SourceRecord),
        "D-105 renderer input is not a D-104 source record",
    )
    body_hash = sha256_text(canonical_json(source.semantic_body.model_dump(mode="json")))
    _require(
        source.semantic_body_hash == body_hash
        and source.source_id == f"d104src_{body_hash.removeprefix('sha256:')}",
        "D-105 renderer source identity drifted",
    )
    projected = source.semantic_body.projected_entry
    template_hash = sha256_text(canonical_json(projected.template.model_dump(mode="json")))
    _require(
        projected.template_hash == template_hash,
        "D-105 renderer template identity drifted",
    )


def render_d105_entry(source: d104.D104SourceRecord) -> str:
    """Render one exact D-104 source using only allowlisted semantic fields."""

    _validate_source_integrity(source)
    projected = source.semantic_body.projected_entry
    template = projected.template
    pattern = template.failure_pattern
    lines = [
        "PATCHLOOP RELIABILITY MEMORY",
        (
            "Treat this as fallible process guidance. Verify it against the current public "
            "task and repository evidence; registered checks take precedence."
        ),
        "",
        f"Failure class: {_safe_visible(pattern.failure_class, label='failure class')}",
        f"Phase: {_safe_visible(pattern.phase.value, label='phase')}",
        f"Pattern: {_safe_visible(pattern.description, label='pattern')}",
        "",
        "Apply when:",
        *_render_list("precondition", template.preconditions),
        "",
        "Diagnostic evidence to seek:",
        *_render_list("diagnostic evidence", template.diagnostic_evidence),
        "",
        "Recommended actions:",
        *_render_list("recommended action", template.recommended_actions),
        "",
        "Do not apply when:",
        *_render_list("exclusion", template.do_not_apply_when),
        "",
        "Applicable languages:",
        *_render_list("language", template.applicable_languages),
    ]
    rendered = "\n".join(lines) + "\n"
    _require("\r" not in rendered, "D-105 rendered memory contains CR")
    try:
        rendered.encode("ascii")
    except UnicodeEncodeError as exc:
        raise D105SourceError("D-105 rendered memory is not ASCII") from exc
    d104.validate_d104_text_leak_safe(rendered, label="D-105 rendered memory")
    _require(
        not any(pattern.search(rendered) for pattern in _MODEL_TEXT_FORBIDDEN),
        "D-105 rendered memory contains model-excluded provenance or code shape",
    )
    return rendered


def encode_d105_render(rendered: str) -> bytes:
    _require(rendered.endswith("\n"), "D-105 rendered memory must end with LF")
    _require("\r" not in rendered, "D-105 rendered memory contains CR")
    try:
        return rendered.encode("ascii")
    except UnicodeEncodeError as exc:
        raise D105SourceError("D-105 rendered memory is not ASCII") from exc


def validate_d105_provider_budget_delta(
    input_tokens_before: int,
    input_tokens_after: int,
) -> int:
    """Validate a same-request-shape provider count delta against the 2k policy.

    This pure helper does not prove that its inputs came from the provider.  A
    future runtime receipt must bind both exact request hashes and both counts.
    """

    _require(
        isinstance(input_tokens_before, int)
        and not isinstance(input_tokens_before, bool)
        and isinstance(input_tokens_after, int)
        and not isinstance(input_tokens_after, bool),
        "D-105 provider token counts must be JSON integers",
    )
    _require(
        input_tokens_before >= 0 and input_tokens_after >= 0,
        "D-105 provider token counts cannot be negative",
    )
    delta = input_tokens_after - input_tokens_before
    _require(delta >= 0, "D-105 provider memory token delta cannot be negative")
    _require(delta <= MEMORY_TOKEN_LIMIT, "D-105 provider memory token delta exceeds budget")
    return delta


def _load_exact_d104(
    *,
    repository: Path,
    source_directory: str | Path = d104.DEFAULT_SOURCE_DIRECTORY,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    gate_path = _resolved(
        d104.DEFAULT_GATE_PATH,
        repository=repository,
        label="D-104 gate",
        require_within_repository=True,
    )
    gate_content = _read_stable(gate_path, label="D-104 gate")
    _require(len(gate_content) == EXPECTED_D104_GATE_BYTES, "D-105 D-104 gate byte count drifted")
    _require(
        sha256_bytes(gate_content) == EXPECTED_D104_GATE_FILE_SHA,
        "D-105 D-104 gate file hash drifted",
    )
    gate_result = d104.validate_d104_source_gate(repository=repository)
    _require(
        gate_result["semantic_body_hash"] == EXPECTED_D104_GATE_BODY_SHA,
        "D-105 D-104 gate identity drifted",
    )
    gate_payload = _parse_json(gate_content, label="D-104 gate")
    validation = d104.validate_d104_materialized_sources(
        repository=repository,
        source_directory=source_directory,
    )
    expected_entries = gate_payload["semantic_body"]["entries"]
    _require(validation["entries"] == expected_entries, "D-105 D-104 source descriptors drifted")
    _require(
        validation["source_collection_id"] == gate_payload["semantic_body"]["source_collection_id"]
        and validation["source_set_hash"] == gate_payload["semantic_body"]["source_set_hash"],
        "D-105 D-104 source set identity drifted",
    )

    directory = _resolved(source_directory, repository=repository, label="D-104 source directory")
    records: list[dict[str, Any]] = []
    for descriptor in expected_entries:
        selected = directory / Path(descriptor["path"]).name
        content = _read_stable(selected, label="D-104 source")
        _require(len(content) == descriptor["file_bytes"], "D-105 D-104 source byte count drifted")
        _require(
            sha256_bytes(content) == descriptor["file_sha256"],
            "D-105 D-104 source file hash drifted",
        )
        try:
            source = d104.D104SourceRecord.model_validate_json(content)
        except ValidationError as exc:
            raise D105SourceError("D-105 D-104 source schema is invalid") from exc
        records.append({"descriptor": descriptor, "source": source, "content": content})
    _require(len(records) == 3, "D-105 exact admitted source count drifted")
    return gate_result, gate_payload, records


def _expected_renders(
    *,
    repository: Path,
    source_directory: str | Path = d104.DEFAULT_SOURCE_DIRECTORY,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    gate_result, gate_payload, sources = _load_exact_d104(
        repository=repository,
        source_directory=source_directory,
    )
    records: list[dict[str, Any]] = []
    for source_record in sources:
        descriptor = source_record["descriptor"]
        source = source_record["source"]
        rendered = render_d105_entry(source)
        content = encode_d105_render(rendered)
        logical_path = DEFAULT_RENDER_DIRECTORY / f"{descriptor['proposed_memory_id']}.txt"
        records.append(
            {
                "order": descriptor["order"],
                "logical_path": logical_path,
                "source_descriptor": descriptor,
                "source": source,
                "rendered": rendered,
                "content": content,
            }
        )
    predecessor = {
        "path": d104.DEFAULT_GATE_PATH.as_posix(),
        "schema_version": gate_result["schema_version"],
        "gate_id": gate_result["gate_id"],
        "semantic_body_hash": gate_result["semantic_body_hash"],
        "file_bytes": gate_result["gate_file_bytes"],
        "file_sha256": gate_result["gate_file_sha256"],
        "source_collection_id": gate_payload["semantic_body"]["source_collection_id"],
        "source_set_hash": gate_payload["semantic_body"]["source_set_hash"],
    }
    return predecessor, records


def write_d105_new_exact(
    path: str | Path,
    content: bytes,
    *,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    """Exclusively create an artifact, allowing only an exact retry."""

    selected = Path(path)
    repo = _repo_root(repository) if repository is not None else None
    if repo is not None:
        selected = _resolved(
            selected,
            repository=repo,
            label="render output",
            require_within_repository=True,
        )
    selected.parent.mkdir(parents=True, exist_ok=True)
    if repo is not None:
        selected = _resolved(
            selected,
            repository=repo,
            label="render output",
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
        existing = _read_stable(selected, label="existing render output")
        _require(existing == content, "D-105 output exists with different exact bytes")
        return {
            "created": False,
            "idempotent_retry": True,
            "file_bytes": len(existing),
            "file_sha256": sha256_bytes(existing),
        }


def preflight_d105_exact_output(
    path: str | Path,
    content: bytes,
    *,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    """Check an output conflict without creating a directory or file."""

    selected = Path(path)
    if repository is not None:
        repo = _repo_root(repository)
        selected = _resolved(
            selected,
            repository=repo,
            label="prospective output",
            require_within_repository=True,
        )
    if not selected.exists():
        return {
            "exists": False,
            "exact": False,
            "file_bytes": 0,
            "file_sha256": None,
        }
    existing = _read_stable(selected, label="prospective existing output")
    _require(existing == content, "D-105 output exists with different exact bytes")
    return {
        "exists": True,
        "exact": True,
        "file_bytes": len(existing),
        "file_sha256": sha256_bytes(existing),
    }


def materialize_d105_renders(
    *,
    repository: str | Path | None = None,
    source_directory: str | Path = d104.DEFAULT_SOURCE_DIRECTORY,
    render_directory: str | Path = DEFAULT_RENDER_DIRECTORY,
) -> dict[str, Any]:
    """Write the exact three model-facing render artifacts."""

    repo = _repo_root(repository)
    directory = _resolved(
        render_directory,
        repository=repo,
        label="render directory",
        require_within_repository=True,
    )
    _require(
        _FULL_REVISION.fullmatch(EMBEDDING_MODEL_REVISION) is not None,
        "D-105 embedding revision must be a full immutable commit",
    )
    _locked_dependencies(repo)
    for implementation_path in IMPLEMENTATION_PATHS:
        _file_binding(
            implementation_path,
            repository=repo,
            label="D-105 implementation",
        )
    _, records = _expected_renders(repository=repo, source_directory=source_directory)
    targets = [(directory / record["logical_path"].name, record["content"]) for record in records]
    for target, content in targets:
        preflight_d105_exact_output(target, content, repository=repo)
    writes: list[dict[str, Any]] = []
    for target, content in targets:
        write = write_d105_new_exact(target, content, repository=repo)
        writes.append({"path": str(target), **write})
    validation = validate_d105_rendered_entries(
        repository=repo,
        source_directory=source_directory,
        render_directory=directory,
    )
    return {"writes": writes, **validation}


def _render_evidence(
    *,
    predecessor: dict[str, Any],
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    descriptors: list[dict[str, Any]] = []
    rendered_texts: list[str] = []
    for record in records:
        source_descriptor = record["source_descriptor"]
        content = record["content"]
        rendered_texts.append(record["rendered"])
        descriptors.append(
            {
                "order": source_descriptor["order"],
                "path": record["logical_path"].as_posix(),
                "proposed_memory_id": source_descriptor["proposed_memory_id"],
                "source_id": source_descriptor["source_id"],
                "source_file_sha256": source_descriptor["file_sha256"],
                "semantic_group_id": source_descriptor["semantic_group_id"],
                "template_hash": source_descriptor["template_hash"],
                "file_bytes": len(content),
                "file_sha256": sha256_bytes(content),
            }
        )

    bundle = RENDER_SEPARATOR.join(text.removesuffix("\n") for text in rendered_texts) + "\n"
    bundle_content = encode_d105_render(bundle)
    render_set_hash = sha256_text(
        canonical_json(
            {
                "d104_source_set_hash": predecessor["source_set_hash"],
                "ordered_render_file_hashes": [row["file_sha256"] for row in descriptors],
                "bundle_file_sha256": sha256_bytes(bundle_content),
            }
        )
    )
    return {
        "d104_gate": predecessor,
        "source_collection_id": predecessor["source_collection_id"],
        "source_set_hash": predecessor["source_set_hash"],
        "entries": descriptors,
        "render_set_hash": render_set_hash,
        "bundle": {
            "separator": RENDER_SEPARATOR,
            "file_bytes": len(bundle_content),
            "file_sha256": sha256_bytes(bundle_content),
            "includes_all_three_entries": True,
            "provider_exact_token_count": None,
        },
        "rendered_memory_count": len(descriptors),
        "render_validation": "pass",
        "leak_scan": "pass",
    }


def validate_d105_rendered_entries(
    *,
    repository: str | Path | None = None,
    source_directory: str | Path = d104.DEFAULT_SOURCE_DIRECTORY,
    render_directory: str | Path = DEFAULT_RENDER_DIRECTORY,
) -> dict[str, Any]:
    """Read-only exact validation of sources and their rendered artifacts."""

    repo = _repo_root(repository)
    predecessor, records = _expected_renders(
        repository=repo,
        source_directory=source_directory,
    )
    directory = _resolved(render_directory, repository=repo, label="render directory")
    _require(directory.is_dir(), "D-105 render directory is unavailable")
    expected_names = [record["logical_path"].name for record in records]
    actual_paths = sorted(directory.iterdir(), key=lambda path: path.name)
    _require(
        [path.name for path in actual_paths] == sorted(expected_names)
        and all(path.is_file() and not _is_linklike(path) for path in actual_paths),
        "D-105 render file set is incomplete or contains extras",
    )

    for record in records:
        selected = directory / record["logical_path"].name
        content = _read_stable(selected, label="rendered memory")
        _require(content == record["content"], "D-105 rendered memory exact bytes drifted")
        try:
            decoded = content.decode("ascii")
        except UnicodeDecodeError as exc:
            raise D105SourceError("D-105 rendered memory is not ASCII") from exc
        _require(decoded == record["rendered"], "D-105 rendered memory semantic text drifted")
        d104.validate_d104_text_leak_safe(decoded, label="D-105 rendered memory")
        _require(
            not any(pattern.search(decoded) for pattern in _MODEL_TEXT_FORBIDDEN),
            "D-105 rendered memory contains model-excluded provenance or code shape",
        )

    return _render_evidence(predecessor=predecessor, records=records)


def _locked_dependencies(repository: Path) -> dict[str, Any]:
    pyproject_binding = _file_binding("pyproject.toml", repository=repository, label="pyproject")
    lock_binding = _file_binding("uv.lock", repository=repository, label="dependency lock")
    pyproject_path = repository / "pyproject.toml"
    lock_path = repository / "uv.lock"
    try:
        pyproject = tomllib.loads(_read_stable(pyproject_path, label="pyproject").decode("utf-8"))
        parsed = tomllib.loads(_read_stable(lock_path, label="dependency lock").decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise D105SourceError("D-105 dependency configuration is invalid") from exc
    memory_extra = pyproject.get("project", {}).get("optional-dependencies", {}).get("memory")
    _require(
        memory_extra == ["sentence-transformers>=3.4,<6"],
        "D-105 memory dependency declaration drifted",
    )
    expected = {
        "sentence-transformers": "5.6.0",
        "huggingface-hub": "1.24.0",
        "tokenizers": "0.22.2",
        "torch": "2.13.0",
        "transformers": "5.14.1",
    }
    selected_rows = [row for row in parsed.get("package", []) if row.get("name") in expected]
    selected_names = [row.get("name") for row in selected_rows]
    _require(
        len(selected_rows) == len(expected) and len(selected_names) == len(set(selected_names)),
        "D-105 locked embedding dependency set is duplicated or incomplete",
    )
    packages = {row["name"]: row["version"] for row in selected_rows}
    _require(packages == expected, "D-105 locked embedding dependencies drifted")
    return {
        "install_command": "uv sync --locked --extra memory",
        "memory_extra": memory_extra,
        "pyproject": pyproject_binding,
        "lock": lock_binding,
        "packages": packages,
    }


def build_d105_render_authorization_gate(
    *,
    repository: str | Path | None = None,
    source_directory: str | Path = d104.DEFAULT_SOURCE_DIRECTORY,
    render_directory: str | Path = DEFAULT_RENDER_DIRECTORY,
    _validate_materialized: bool = True,
) -> dict[str, Any]:
    """Build deterministic, no-call D-105 renderer/authorization evidence."""

    repo = _repo_root(repository)
    _require(
        _FULL_REVISION.fullmatch(EMBEDDING_MODEL_REVISION) is not None,
        "D-105 embedding revision must be a full immutable commit",
    )
    _require(
        isinstance(_validate_materialized, bool),
        "D-105 materialized-render validation selector must be boolean",
    )
    _require_exact_gate_path(
        source_directory,
        canonical=d104.DEFAULT_SOURCE_DIRECTORY,
        repository=repo,
        label="source directory",
    )
    _require_exact_gate_path(
        render_directory,
        canonical=DEFAULT_RENDER_DIRECTORY,
        repository=repo,
        label="render directory",
    )
    _resolved(
        source_directory,
        repository=repo,
        label="source directory",
        require_within_repository=True,
    )
    _resolved(
        render_directory,
        repository=repo,
        label="render directory",
        require_within_repository=True,
    )
    if _validate_materialized:
        evidence = validate_d105_rendered_entries(
            repository=repo,
            source_directory=source_directory,
            render_directory=render_directory,
        )
    else:
        predecessor, records = _expected_renders(
            repository=repo,
            source_directory=source_directory,
        )
        evidence = _render_evidence(predecessor=predecessor, records=records)
    dependencies = _locked_dependencies(repo)
    body = {
        "milestone": "D-105",
        "evidence_kind": "deterministic-memory-render-and-index-build-authorization-source-gate",
        "recorded_at": RECORDED_AT,
        **evidence,
        "render_policy": {
            "schema_version": RENDER_POLICY_VERSION,
            "encoding": "ascii-subset-of-utf8",
            "normalization": "NFKC-input-required-no-transform",
            "newline": "LF",
            "trailing_newline_required": True,
            "entry_separator": RENDER_SEPARATOR,
            "field_order": list(MODEL_VISIBLE_FIELDS),
            "excluded_fields": list(MODEL_EXCLUDED_FIELDS),
            "whole_entry_only": True,
            "partial_truncation_allowed": False,
            "provenance_in_model_text": False,
        },
        "token_budget_policy": {
            "max_memory_delta_tokens": MEMORY_TOKEN_LIMIT,
            "provider_exact_budget_validated": False,
            "counter": TOKEN_COUNT_ENDPOINT,
            "same_request_shape_required": True,
        },
        "token_budget_evidence_boundary": {
            "schema_version": TOKEN_POLICY_VERSION,
            "provider_model": OPENAI_MODEL_ID,
            "baseline": "canonical-context-selected-memory-is-json-null",
            "with_memory": "same-canonical-context-selected-memory-is-exact-whole-entry-bundle",
            "delta_formula": "with_memory_input_tokens - baseline_input_tokens",
            "allowed_context_diff_json_pointers": ["/selected_memory"],
            "canonical_context_deep_diff_required": True,
            "baseline_selected_memory_value": None,
            "with_memory_selected_memory_must_match_render_bundle": True,
            "request_equal_after_context_slot_normalization": True,
            "both_context_hashes_required_in_future_receipt": True,
            "both_request_hashes_required_in_future_receipt": True,
            "headers_and_separators_included": True,
            "local_character_divided_by_four_used": False,
            "local_estimate_authoritative": False,
            "standalone_memory_count_equivalent_to_full_request_delta": False,
            "provider_count_receipt_present": False,
            "provider_call_made_for_d105": False,
        },
        "embedding_authorization_candidate": {
            "model_id": EMBEDDING_MODEL_ID,
            "revision": EMBEDDING_MODEL_REVISION,
            "normalize_embeddings": True,
            "trust_remote_code": False,
        },
        "embedding_revision_observation": {
            "model_api_url": EMBEDDING_MODEL_API_URL,
            "commit_url": EMBEDDING_COMMIT_URL,
            "observed_at": EMBEDDING_REVISION_OBSERVED_AT,
            "upstream_last_modified": EMBEDDING_UPSTREAM_LAST_MODIFIED,
            "revision_kind": "full-40-hex-commit",
            "license": "apache-2.0",
            "expected_vector_dimension": 384,
            "expected_dtype": "float32",
            "external_observation_not_signature": True,
            "model_snapshot_downloaded": False,
            "snapshot_file_hashes_verified": False,
            "vector_shape_verified": False,
        },
        "locked_embedding_dependencies": dependencies,
        "group_aware_index_build_plan": {
            "schema_version": INDEX_PLAN_VERSION,
            "input_source_schema": d104.SOURCE_SCHEMA_VERSION,
            "source_collection_id": evidence["source_collection_id"],
            "source_set_hash": evidence["source_set_hash"],
            "ordered_source_ids": [entry["source_id"] for entry in evidence["entries"]],
            "ordered_render_hashes": [entry["file_sha256"] for entry in evidence["entries"]],
            "one_entry_per_admitted_group": True,
            "held_group_ids": [
                "interrupt-lifecycle-unresolved",
                "diagnostic-contract-unresolved",
            ],
            "held_groups_allowed": False,
            "legacy_failure_builder_allowed": False,
            "deterministic_index_identity_required": True,
            "source_provenance_preserved_outside_model_text": True,
            "actual_builder_implemented": False,
            "locked_model_preflight_completed": False,
        },
        "implementation_files": [
            _file_binding(path, repository=repo, label="D-105 implementation")
            for path in IMPLEMENTATION_PATHS
        ],
        "evidence_boundary": {
            "semantic_authoring_source": "exact-d104-sealed-unindexed-sources-only",
            "sealed_rule_text_modified": False,
            "inherited_public_submitted_patch_integrity_revalidated": True,
            "public_submitted_patch_bodies_read_by_inherited_validator": True,
            "public_patch_text_copied_into_renders": False,
            "new_rule_semantics_authored_from_patch_text": False,
            "raw_trace_bodies_read": False,
            "private_or_evaluator_bodies_read": False,
            "provider_request_or_response_bodies_read": False,
            "embedding_model_imported": False,
            "embedding_model_downloaded": False,
            "package_initialization_imported_legacy_retrieval_and_store_modules": True,
            "legacy_memory_store_or_retrieval_api_called": False,
            "historical_index_state_inspected": False,
            "historical_index_state_modified": False,
        },
        "authority": {
            "d104_exact_gate_revalidated": True,
            "d104_source_set_revalidated": True,
            "admitted_rule_count": 3,
            "held_group_count": 2,
            "held_group_rendered_count": 0,
            "render_policy_frozen": True,
            "rendered_memory_count": 3,
            "token_budget_policy_frozen": True,
            "provider_exact_budget_validated": False,
            "embedding_revision_candidate_pinned": True,
            "embedding_snapshot_verified": False,
            "index_build_authorization_candidate": True,
            "user_index_build_approval_receipt_present": False,
            "memory_index_build_authorized": False,
            "actual_memory_entry_count": 0,
            "embedding_count": 0,
            "d105_created_index_count": 0,
            "memory_index_built": False,
            "memory_index_frozen": False,
            "retrieval_ready": False,
            "runtime_memory_injection_count": 0,
            "core_campaign_unlocked": False,
            "analysis_ready": False,
            "memory_effect_established": False,
            "negative_transfer_established": False,
            "provider_calls_made": 0,
            "evaluator_calls_made": 0,
            "added_model_cost_usd": 0,
        },
        "next_gate": (
            "exact-d105-gate-approval-locked-embedding-snapshot-preflight-and-"
            "group-aware-index-builder"
        ),
    }
    body_hash = sha256_text(canonical_json(body))
    return {
        "schema_version": GATE_SCHEMA_VERSION,
        "gate_id": f"d105_{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": body,
    }


def encode_d105_gate(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def preflight_d105_publication(
    gate_path: str | Path = DEFAULT_GATE_PATH,
    *,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    """Validate every prospective byte and conflict before publishing any output."""

    repo = _repo_root(repository)
    predecessor, records = _expected_renders(repository=repo)
    _render_evidence(predecessor=predecessor, records=records)
    for record in records:
        target = repo / record["logical_path"]
        preflight_d105_exact_output(target, record["content"], repository=repo)
    gate = build_d105_render_authorization_gate(
        repository=repo,
        _validate_materialized=False,
    )
    content = encode_d105_gate(gate)
    selected_gate = Path(gate_path) if Path(gate_path).is_absolute() else repo / gate_path
    preflight_d105_exact_output(selected_gate, content, repository=repo)
    return gate


def validate_d105_gate(
    gate_path: str | Path = DEFAULT_GATE_PATH,
    *,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    """Read-only exact rebuild of the checked-in D-105 source gate."""

    repo = _repo_root(repository)
    selected = _resolved(gate_path, repository=repo, label="D-105 gate")
    content = _read_stable(selected, label="D-105 gate")
    expected = build_d105_render_authorization_gate(repository=repo)
    expected_content = encode_d105_gate(expected)
    _require(content == expected_content, "D-105 gate exact bytes drifted")
    parsed = _parse_json(content, label="D-105 gate")
    _require(parsed == expected, "D-105 gate semantic content drifted")
    authority = expected["semantic_body"]["authority"]
    return {
        "ok": True,
        "schema_version": expected["schema_version"],
        "gate_id": expected["gate_id"],
        "semantic_body_hash": expected["semantic_body_hash"],
        "gate_file_bytes": len(content),
        "gate_file_sha256": sha256_bytes(content),
        "render_set_hash": expected["semantic_body"]["render_set_hash"],
        "rendered_memory_count": authority["rendered_memory_count"],
        "index_build_authorization_candidate": authority["index_build_authorization_candidate"],
        "memory_index_build_authorized": authority["memory_index_build_authorized"],
        "core_campaign_unlocked": authority["core_campaign_unlocked"],
        "gate_validation": "pass",
    }
