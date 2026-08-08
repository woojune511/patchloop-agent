"""Seal an append-only authorization candidate after the consumed D-119 failure.

D-120 never edits, resumes, repairs, or reruns D-119.  It binds the exact
three-file partial state, records the narrow cleanup-observation contract bug,
and proposes D-121 implementation, offline tests, readiness evidence, and an
execution-authorization candidate.  Even exact D-120 approval would not permit
the fresh D-121 run; that requires a later exact D-121 approval.  D-120 does
not invoke Docker, open either opaque benchmark object, or call a runtime agent.
"""

from __future__ import annotations

import json
import os
import re
import stat
import unicodedata
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from patchloop.errors import ContractError
from patchloop.runtime import repository_root
from patchloop.util import canonical_json, sha256_bytes

MILESTONE = "D-120"

D119_PARTIAL_SPECS: tuple[dict[str, Any], ...] = (
    {
        "role": "approval-receipt",
        "path": "reports/memory-development/d119-cutoff-isolation-approval-receipt.json",
        "id_field": "receipt_id",
        "identifier": (
            "d119approval_671af8d6e7cbd44ef0793c1bf1bf53f3f5f8e3fcbfd26e04906cb4abdea50cce"
        ),
        "semantic_body_hash": (
            "sha256:671af8d6e7cbd44ef0793c1bf1bf53f3f5f8e3fcbfd26e04906cb4abdea50cce"
        ),
        "file_bytes": 5_299,
        "file_sha256": ("sha256:625cd6487fffe50b2429e011c67da222ec0da020dbf62d65a911fa83da3f550c"),
    },
    {
        "role": "preflight",
        "path": "reports/memory-development/d119-cutoff-isolation-preflight.json",
        "id_field": "preflight_id",
        "identifier": (
            "d119preflight_85dcbc49bec53797904f080d0e6922b521a9f6f232902e122895090e5f886dd1"
        ),
        "semantic_body_hash": (
            "sha256:85dcbc49bec53797904f080d0e6922b521a9f6f232902e122895090e5f886dd1"
        ),
        "file_bytes": 11_229,
        "file_sha256": ("sha256:57f59fc29054276947851abdfe3dbf0040fe10cef5624946e66dc84a698fb18a"),
    },
)

D119_JOURNAL_SPEC = {
    "path": "reports/memory-development/d119-isolation-execution.jsonl",
    "file_bytes": 2_075,
    "file_sha256": "sha256:fadda3b86b2ad954a1d233b0dbf11d67b8a9a86f3db6704eab555eec5f2a4950",
    "record_count": 4,
    "head_hash": "sha256:4bd08521b13431251449d79cb2847a93fc947cf2ce6e6b319e71f728cc74bd46",
}

D119_ABSENT_OUTPUTS = (
    "reports/memory-development/d119-external-anchor-evidence.json",
    "reports/memory-development/d119-isolation-evidence.json",
    "reports/memory-development/d119-cutoff-isolation-source-gate.json",
)

D119_IMPLEMENTATION_SPECS: tuple[dict[str, Any], ...] = (
    {
        "path": "patchloop/memory/d119_cutoff_isolation_qualification.py",
        "file_bytes": 79_260,
        "file_sha256": "sha256:8428dc47241ee8698eb8edc075521d4fa2044f9e793325771df2fab0c917312b",
    },
    {
        "path": "scripts/run_d119_cutoff_isolation_qualification.py",
        "file_bytes": 1_906,
        "file_sha256": "sha256:fff81e5c6d8218f1102c5ff5bd485513db56ce3a2fe205faa219e708c8acc21b",
    },
    {
        "path": "tests/test_d119_cutoff_isolation_qualification.py",
        "file_bytes": 32_427,
        "file_sha256": "sha256:f2c4f3b50980d4697aca81967d5d19e2021df455dc320d5ddffdd3458d761650",
    },
)

D119_EXECUTION_TUPLE = {
    "authorized_action_hash": (
        "sha256:be673eec0b6cf5cde23db0f19c050d82867a1a4a497a28124f61ca47e24278c2"
    ),
    "docker_cli_file_bytes": 43_095_472,
    "docker_cli_file_sha256": (
        "sha256:8985cd8ac002c3240b5aa48fe401fcb55dca5d849b537e3c835564e8e8c49a70"
    ),
    "immutable_image_id": (
        "sha256:1144b4be9927ac5882401185c326003383630eac9db84102ee3d71c06e261cac"
    ),
    "dockerfile_sha256": (
        "sha256:f310b88e8a2769b83202c3fb7a5cb776142c70a6d45935b648db258d3bc2d944"
    ),
    "probe_runner_sha256": (
        "sha256:ed07d48a2e2129645aa0ae4765d0f248750125eb685bf55767a21db636e15509"
    ),
    "profile_hash": "sha256:82511cd9e7e25be999955e260f009204703ef5dcdbc2340897d821c4f52cf6a5",
    "source_fingerprint": (
        "sha256:912c8ad78849f7f674756ab9d4084ed92e3c8a535bc04a6b89a7a14f7170a53f"
    ),
    "ordered_sources": [
        {
            "source_id": "swe-bench-dev-f5351",
            "path": (
                ".patchloop/external-evidence/d118/swe-bench-f5351/data/dev-00000-of-00001.parquet"
            ),
            "file_bytes": 1_382_594,
            "file_sha256": (
                "sha256:d758d54540aa4140d0274ed0cc93b8288aa6f323c3c603e2557e7666a47fc41b"
            ),
            "probe_source_sha256": (
                "sha256:76dac3eec570730dc9fa9b1ce1cc4344b42971ffc4339b22caf4a569c65bd2bc"
            ),
        },
        {
            "source_id": "swe-gym-train-26a6",
            "path": (
                ".patchloop/external-evidence/d118/swe-gym-26a6/data/train-00000-of-00001.parquet"
            ),
            "file_bytes": 43_644_473,
            "file_sha256": (
                "sha256:60569cea74bb281f7a5579467436a2bc1932c6e0c5f2f7fa0d084392abd9ad97"
            ),
            "probe_source_sha256": (
                "sha256:39e64b76b26d8c53e2e128a1ef5c6e09354ca009d1b45157dc9cd0028a493dc7"
            ),
        },
    ],
}

D120_IMPLEMENTATION_PATHS = (
    Path("patchloop/memory/d120_d119_cleanup_correction_authorization.py"),
    Path("scripts/build_d120_d119_cleanup_correction_authorization.py"),
    Path("tests/test_d120_d119_cleanup_correction_authorization.py"),
)

OUTPUT_PATHS = {
    "preflight": Path("reports/memory-development/d120-d119-partial-failure-preflight.json"),
    "candidate": Path(
        "reports/memory-development/d120-d119-cleanup-correction-authorization-candidate.json"
    ),
    "source_gate": Path("reports/memory-development/d120-d119-cleanup-correction-source-gate.json"),
}

D121_PREPARATION_PATHS = (
    "patchloop/memory/d121_hash_only_isolation_successor.py",
    "scripts/run_d121_hash_only_isolation_successor.py",
    "tests/test_d121_hash_only_isolation_successor.py",
    "reports/memory-development/d121-isolation-successor-preparation-approval-receipt.json",
    "reports/memory-development/d121-isolation-successor-readiness-preflight.json",
    "reports/memory-development/d121-isolation-successor-execution-authorization-candidate.json",
    "reports/memory-development/d121-isolation-successor-authorization-source-gate.json",
)

D121_PROSPECTIVE_RUN_OUTPUT_PATHS = (
    "reports/memory-development/d121-isolation-successor-execution-approval-receipt.json",
    "reports/memory-development/d121-isolation-successor-execution.jsonl",
    "reports/memory-development/d121-isolation-successor-evidence.json",
    "reports/memory-development/d121-isolation-successor-completion-gate.json",
)

_D119_DECLARED_PATHS = (
    *(spec["path"] for spec in D119_PARTIAL_SPECS),
    D119_JOURNAL_SPEC["path"],
    *D119_ABSENT_OUTPUTS,
    *(spec["path"] for spec in D119_IMPLEMENTATION_SPECS),
)

_SHA256 = re.compile(r"sha256:[0-9a-f]{64}\Z")


class D120AuthorizationError(ContractError):
    """Raised when the partial D-119 evidence or D-120 contract drifts."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise D120AuthorizationError(message)


def _canonical_bytes(value: Any) -> bytes:
    return canonical_json(value).encode("utf-8")


def _pretty_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def _repo_root(repository: str | Path | None) -> Path:
    selected = Path(repository) if repository is not None else repository_root()
    try:
        root = selected.resolve(strict=True)
    except OSError as exc:
        raise D120AuthorizationError("D-120 repository root cannot be resolved") from exc
    _require(root.is_dir(), "D-120 repository root must be a directory")
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


def _resolved(
    repository: Path,
    relative: str | Path,
    *,
    must_exist: bool,
    label: str,
) -> Path:
    selected = Path(relative)
    _require(not selected.is_absolute(), f"D-120 {label} must be repository-relative")
    _require(".." not in selected.parts, f"D-120 {label} traverses a parent")
    for part in selected.parts:
        _require(":" not in part, f"D-120 {label} uses an alternate data stream")
        _require(not part.endswith((".", " ")), f"D-120 {label} is ambiguous on Windows")
    logical = repository / selected
    cursor = repository
    for part in selected.parts:
        cursor /= part
        _require(not _is_linklike(cursor), f"D-120 {label} traverses a link or junction")
    try:
        if must_exist:
            resolved = logical.resolve(strict=True)
        else:
            resolved = logical.parent.resolve(strict=True) / logical.name
        resolved.relative_to(repository)
    except (OSError, ValueError) as exc:
        raise D120AuthorizationError(f"D-120 {label} escapes the repository") from exc
    return resolved


def _read_stable(path: Path, *, label: str) -> bytes:
    _require(path.is_file(), f"D-120 {label} is missing")
    before = path.stat()
    with path.open("rb", buffering=0) as handle:
        opened = os.fstat(handle.fileno())
        _require(
            (before.st_dev, before.st_ino) == (opened.st_dev, opened.st_ino),
            f"D-120 {label} identity changed before read",
        )
        content = handle.read()
        after_fd = os.fstat(handle.fileno())
    after_path = path.stat()
    identity = lambda value: (  # noqa: E731
        value.st_dev,
        value.st_ino,
        value.st_size,
        value.st_mtime_ns,
    )
    _require(
        identity(before) == identity(opened) == identity(after_fd) == identity(after_path),
        f"D-120 {label} changed during read",
    )
    return content


def _declared_path_contract(repository: Path) -> dict[str, Any]:
    """Fail closed on aliases across the immutable, candidate, and successor paths."""

    groups = {
        "d119_immutable_or_absent": [Path(value) for value in _D119_DECLARED_PATHS],
        "d120_candidate": [*D120_IMPLEMENTATION_PATHS, *OUTPUT_PATHS.values()],
        "d121_preparation_new_only": [Path(value) for value in D121_PREPARATION_PATHS],
        "d121_prospective_run_outputs_not_authorized": [
            Path(value) for value in D121_PROSPECTIVE_RUN_OUTPUT_PATHS
        ],
    }
    normalized_owner: dict[str, tuple[str, str]] = {}
    inode_owner: dict[tuple[int, int], tuple[str, str]] = {}
    rendered: dict[str, list[str]] = {}
    for group, paths in groups.items():
        rendered[group] = []
        for relative in paths:
            logical = relative.as_posix()
            normalized = unicodedata.normalize("NFKC", logical).casefold()
            _require(
                normalized not in normalized_owner,
                f"D-120 declared path aliases {normalized_owner.get(normalized)}",
            )
            normalized_owner[normalized] = (group, logical)
            candidate = repository / relative
            if group.startswith("d121_"):
                _require(
                    not candidate.exists() and not _is_linklike(candidate),
                    f"D-120 {group} path must be absent before D-121 authorization",
                )
            resolved = _resolved(
                repository,
                relative,
                must_exist=candidate.exists(),
                label=f"{group} declared path",
            )
            if candidate.exists():
                _require(resolved.is_file(), f"D-120 {group} declared path is not a file")
                info = resolved.stat()
                identity = (info.st_dev, info.st_ino)
                _require(
                    identity not in inode_owner,
                    f"D-120 declared path inode aliases {inode_owner.get(identity)}",
                )
                inode_owner[identity] = (group, logical)
            rendered[group].append(logical)
    return {
        "normalization": "unicode-nfkc-casefold-posix",
        "alternate_data_streams_forbidden": True,
        "symlink_junction_or_reparse_traversal_forbidden": True,
        "casefold_and_normalized_aliases_absent": True,
        "existing_inode_aliases_absent": True,
        "sets_pairwise_disjoint": True,
        "all_d121_paths_absent_before_authorization": True,
        "path_sets": rendered,
        "d121_preparation_mutation_whitelist": list(D121_PREPARATION_PATHS),
        "d121_prospective_run_outputs_authorized": False,
    }


def _parse_json(content: bytes, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise D120AuthorizationError(f"D-120 {label} is not JSON") from exc
    _require(isinstance(value, dict), f"D-120 {label} root must be an object")
    _require(content == _pretty_bytes(value), f"D-120 {label} bytes are not canonical")
    return value


def _binding(path: str | Path, content: bytes, **identity: Any) -> dict[str, Any]:
    return {
        "path": Path(path).as_posix(),
        **identity,
        "file_bytes": len(content),
        "file_sha256": sha256_bytes(content),
    }


def _envelope(
    *, schema_version: str, id_field: str, id_prefix: str, body: Mapping[str, Any]
) -> dict[str, Any]:
    body_hash = sha256_bytes(_canonical_bytes(body))
    return {
        "schema_version": schema_version,
        id_field: f"{id_prefix}{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": dict(body),
    }


def _validate_envelope(
    value: Mapping[str, Any],
    *,
    schema_version: str,
    id_field: str,
    id_prefix: str,
    label: str,
) -> None:
    _require(
        set(value) == {"schema_version", id_field, "semantic_body_hash", "semantic_body"},
        f"D-120 {label} root fields differ",
    )
    _require(value["schema_version"] == schema_version, f"D-120 {label} schema differs")
    body = value["semantic_body"]
    _require(isinstance(body, dict), f"D-120 {label} body must be an object")
    body_hash = sha256_bytes(_canonical_bytes(body))
    _require(value["semantic_body_hash"] == body_hash, f"D-120 {label} body hash differs")
    _require(
        value[id_field] == f"{id_prefix}{body_hash.removeprefix('sha256:')}",
        f"D-120 {label} identifier differs",
    )


def _parse_timestamp(value: Any, *, label: str) -> datetime:
    _require(isinstance(value, str) and value.endswith("Z"), f"D-120 {label} time invalid")
    try:
        parsed = datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except ValueError as exc:
        raise D120AuthorizationError(f"D-120 {label} time invalid") from exc
    _require(parsed.utcoffset() == UTC.utcoffset(parsed), f"D-120 {label} time must be UTC")
    return parsed


def _validate_d119_journal(content: bytes) -> dict[str, Any]:
    _require(content.endswith(b"\n"), "D-120 D-119 journal lacks final LF")
    rows: list[dict[str, Any]] = []
    previous = "sha256:" + "0" * 64
    for sequence, raw in enumerate(content.splitlines()):
        try:
            row = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise D120AuthorizationError("D-120 D-119 journal row is invalid") from exc
        _require(isinstance(row, dict), "D-120 D-119 journal row must be an object")
        _require(raw == _canonical_bytes(row), "D-120 D-119 journal row is not canonical")
        _require(row.get("sequence") == sequence, "D-120 D-119 journal sequence differs")
        _require(
            row.get("previous_record_hash") == previous,
            "D-120 D-119 journal chain differs",
        )
        claimed = row.get("record_hash")
        _require(isinstance(claimed, str) and _SHA256.fullmatch(claimed), "journal hash invalid")
        body = {key: value for key, value in row.items() if key != "record_hash"}
        _require(claimed == sha256_bytes(_canonical_bytes(body)), "journal row hash differs")
        previous = claimed
        rows.append(row)
    _require(content == b"".join(_canonical_bytes(row) + b"\n" for row in rows), "journal drift")
    _require(len(rows) == 4, "D-120 D-119 journal record count differs")
    _require(
        [row["event"] for row in rows]
        == [
            "ExecutionClaimed",
            "ImageIdentityVerified",
            "IsolationSessionStarted",
            "ExecutionFailed",
        ],
        "D-120 D-119 journal event sequence differs",
    )
    _require(
        rows[2]["data"]
        == {
            "input_file_sha256": (
                "sha256:d758d54540aa4140d0274ed0cc93b8288aa6f323c3c603e2557e7666a47fc41b"
            ),
            "probe_source_sha256": (
                "sha256:76dac3eec570730dc9fa9b1ce1cc4344b42971ffc4339b22caf4a569c65bd2bc"
            ),
            "source_id": "swe-bench-dev-f5351",
        },
        "D-120 D-119 started session differs",
    )
    _require(
        rows[3]["data"]
        == {"automatic_retry_allowed": False, "error_type": "D119QualificationError"},
        "D-120 D-119 failure record differs",
    )
    times = [_parse_timestamp(row["recorded_at"], label="journal") for row in rows]
    _require(
        all(left <= right for left, right in zip(times, times[1:], strict=False)),
        "D-120 D-119 journal chronology differs",
    )
    return {
        "path": D119_JOURNAL_SPEC["path"],
        "record_count": len(rows),
        "head_hash": previous,
        "file_bytes": len(content),
        "file_sha256": sha256_bytes(content),
        "events": [row["event"] for row in rows],
        "execution_claimed_at": rows[0]["recorded_at"],
        "failed_at": rows[-1]["recorded_at"],
    }


def _exact_file_state(
    repository: Path, specs: Sequence[Mapping[str, Any]], *, label: str
) -> list[dict[str, Any]]:
    rows = []
    for spec in specs:
        path = _resolved(repository, spec["path"], must_exist=True, label=label)
        content = _read_stable(path, label=label)
        _require(len(content) == spec["file_bytes"], f"D-120 {label} bytes differ")
        _require(sha256_bytes(content) == spec["file_sha256"], f"D-120 {label} SHA differs")
        rows.append(dict(spec))
    return rows


def _execution_tuple_from_d119_preflight(body: Mapping[str, Any]) -> dict[str, Any]:
    docker = body.get("docker_cli_binding")
    profile = body.get("isolation_profile")
    source_state = body.get("source_pre_state")
    sessions = body.get("session_plan")
    _require(isinstance(docker, dict), "D-119 Docker binding is missing")
    _require(isinstance(profile, dict), "D-119 isolation profile is missing")
    _require(isinstance(source_state, dict), "D-119 source state is missing")
    _require(isinstance(sessions, list) and len(sessions) == 2, "D-119 sessions differ")
    ordered_sources = []
    for session in sessions:
        _require(isinstance(session, dict), "D-119 session row differs")
        ordered_sources.append(
            {
                "source_id": session.get("source_id"),
                "path": session.get("path"),
                "file_bytes": session.get("file_bytes"),
                "file_sha256": session.get("file_sha256"),
                "probe_source_sha256": session.get("probe_source_sha256"),
            }
        )
    return {
        "authorized_action_hash": body.get("authorized_action_hash"),
        "docker_cli_file_bytes": docker.get("file_bytes"),
        "docker_cli_file_sha256": docker.get("file_sha256"),
        "immutable_image_id": profile.get("immutable_image_id"),
        "dockerfile_sha256": profile.get("dockerfile_sha256"),
        "probe_runner_sha256": profile.get("probe_runner_sha256"),
        "profile_hash": profile.get("profile_hash"),
        "source_fingerprint": source_state.get("fingerprint"),
        "ordered_sources": ordered_sources,
    }


def _d119_partial_context(repository: Path) -> dict[str, Any]:
    declared_paths = _declared_path_contract(repository)
    artifacts = []
    d119_preflight_body: Mapping[str, Any] | None = None
    for spec in D119_PARTIAL_SPECS:
        path = _resolved(repository, spec["path"], must_exist=True, label=spec["role"])
        content = _read_stable(path, label=spec["role"])
        value = _parse_json(content, label=spec["role"])
        _require(len(content) == spec["file_bytes"], "D-119 partial artifact bytes differ")
        _require(sha256_bytes(content) == spec["file_sha256"], "D-119 artifact SHA differs")
        _require(value[spec["id_field"]] == spec["identifier"], "D-119 artifact ID differs")
        _require(
            value["semantic_body_hash"] == spec["semantic_body_hash"],
            "D-119 artifact body SHA differs",
        )
        if spec["role"] == "preflight":
            d119_preflight_body = value["semantic_body"]
        artifacts.append(dict(spec))
    _require(d119_preflight_body is not None, "D-119 exact preflight body is missing")
    observed_execution_tuple = _execution_tuple_from_d119_preflight(d119_preflight_body)
    _require(
        _canonical_bytes(observed_execution_tuple) == _canonical_bytes(D119_EXECUTION_TUPLE),
        "D-119 execution tuple differs",
    )
    journal_path = _resolved(
        repository, D119_JOURNAL_SPEC["path"], must_exist=True, label="journal"
    )
    journal_content = _read_stable(journal_path, label="journal")
    _require(len(journal_content) == D119_JOURNAL_SPEC["file_bytes"], "journal bytes differ")
    _require(
        sha256_bytes(journal_content) == D119_JOURNAL_SPEC["file_sha256"],
        "journal SHA differs",
    )
    journal = _validate_d119_journal(journal_content)
    _require(journal["head_hash"] == D119_JOURNAL_SPEC["head_hash"], "journal head differs")
    for relative in D119_ABSENT_OUTPUTS:
        path = _resolved(repository, relative, must_exist=False, label="absent D-119 output")
        _require(not path.exists() and not _is_linklike(path), "D-119 partial state changed")
    d119_implementation = _exact_file_state(
        repository, D119_IMPLEMENTATION_SPECS, label="D-119 implementation"
    )
    return {
        "status": "PARTIAL_CONSUMED_FAILED",
        "artifacts_present": artifacts,
        "journal": journal,
        "artifacts_absent": list(D119_ABSENT_OUTPUTS),
        "d119_implementation": d119_implementation,
        "d119_execution_tuple": observed_execution_tuple,
        "declared_path_contract": declared_paths,
        "durable_completed_session_count": 0,
        "sealed_probe_outcome_count": 0,
        "probe_outcome": "UNSEALED_UNKNOWN",
        "same_d119_retry_resume_or_repair_allowed": False,
    }


def _d120_implementation_state(repository: Path) -> dict[str, Any]:
    rows = []
    for relative in D120_IMPLEMENTATION_PATHS:
        path = _resolved(repository, relative, must_exist=True, label="D-120 implementation")
        content = _read_stable(path, label="D-120 implementation")
        rows.append(_binding(relative, content))
    return {
        "files": rows,
        "fingerprint": sha256_bytes(_canonical_bytes(rows)),
    }


def _diagnosis_contract() -> dict[str, Any]:
    return {
        "failure_class": "HARNESS_CLEANUP_EVIDENCE_VALIDATOR_ERROR",
        "failure_stage": "cleanup-postcondition-output-representation-mismatch",
        "proof_grade": "source-consistent-self-attested-diagnosis-not-portable-proof",
        "d119_journal_evidence": {
            "failure_event": "ExecutionFailed",
            "recorded_error_type": "D119QualificationError",
            "cleanup_detail_recorded": False,
            "probe_result_recorded": False,
        },
        "source_derived_finding": {
            "function": "_execute_session",
            "d119_module_file_sha256": D119_IMPLEMENTATION_SPECS[0]["file_sha256"],
            "accepted_inspect_return_code": "nonzero",
            "incorrect_additional_predicate": "removed_inspect.stdout == b-empty",
            "cleanup_exception_can_mask_earlier_primary_exception": True,
        },
        "actual_execution_operator_observation": {
            "evidence_kind": "self-attested-operator-observation-not-journal-evidence",
            "exception_message": "removed-container inspect emitted stdout",
            "raw_command_transcript_available": False,
            "raw_removed_inspect_stdout_available": False,
            "portable_replay_proof": False,
        },
        "current_cli_observation": {
            "evidence_kind": "current-read-only-self-attested-reproduction",
            "missing_container_id_kind": "synthetic-64-zero-hex",
            "inspect_exit_code": 1,
            "stdout_presentation": "empty-json-array-lf",
            "stdout_bytes": 3,
            "stdout_sha256": (
                "sha256:37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570"
            ),
            "stderr_shape": "error: no such object: <container-id>\\n",
            "original_d119_journal_contains_this_observation": False,
        },
        "classification_boundary": {
            "container_removal_failure_established": False,
            "docker_isolation_failure_established": False,
            "source_hash_failure_established": False,
            "first_probe_success_established": False,
            "first_probe_outcome": "UNSEALED_UNKNOWN",
            "hash_only_isolation_profile_verified": False,
            "second_session_started": False,
        },
    }


def _future_action() -> dict[str, Any]:
    return {
        "action": "implement-test-and-prepare-d121-execution-authorization-candidate",
        "unchanged_d119_execution_tuple": D119_EXECUTION_TUPLE,
        "execution_tuple_reverification_required_before_any_later_run": True,
        "unchanged_probe_image_profile_source_tuple": True,
        "planned_behavioral_changes": [
            "fresh-d121-container-label-and-name-namespace",
            "cleanup-no-row-presentation-normalization",
            "exact-id-and-label-wide-residual-inventories",
            "primary-probe-outcome-preserved-before-cleanup-validation",
            "expanded-cleanup-and-session-journal-events",
        ],
        "relationship_to_d119": {
            "fresh_successor_run_planned": True,
            "d119_retry": False,
            "d119_resume": False,
            "d119_repair": False,
            "d119_partial_artifacts_and_implementation_immutable": True,
        },
        "new_paths": list(D121_PREPARATION_PATHS),
        "mutation_whitelist": list(D121_PREPARATION_PATHS),
        "prospective_run_output_paths_not_authorized": list(D121_PROSPECTIVE_RUN_OUTPUT_PATHS),
        "container_namespace": {
            "label": "io.patchloop.managed=d121-isolation-successor",
            "name_prefix": "patchloop-d121-",
            "disjoint_from_d119_and_d120": True,
            "disjointness_validated_by": "d120-declared-path-contract",
        },
        "d120_approval_authorizes": {
            "d121_new_only_implementation": True,
            "offline_tests": True,
            "no_start_exact_docker_readiness_preflight": True,
            "execution_authorization_candidate_preparation": True,
        },
        "d120_approval_does_not_authorize": {
            "docker_container_start": True,
            "opaque_source_read": True,
            "d121_successor_execution": True,
        },
        "prospective_execution_contract": {
            "fresh_run_count": 1,
            "session_count": 2,
            "both_exact_d119_sources_rerun": True,
            "automatic_retry_count": 0,
            "failure_remains_consumed": True,
        },
        "cleanup_observation_contract": {
            "primary_probe_outcome_captured_before_cleanup": True,
            "cleanup_outcome_captured_without_masking_primary": True,
            "required_events_in_order": [
                "ProbeResultValidated",
                "ContainerRemovalVerified",
                "IsolationSessionCompleted",
            ],
            "exact_id_rm_return_code": 0,
            "exact_id_rm_argv": [
                "<exact-pinned-docker-cli>",
                "rm",
                "--force",
                "<exact-container-id>",
            ],
            "post_remove_inspect_return_code": "nonzero",
            "post_remove_inspect_argv": [
                "<exact-pinned-docker-cli>",
                "inspect",
                "<exact-container-id>",
            ],
            "accepted_no_row_stdout_exact_bytes": [
                {"presentation": "empty-bytes", "hex": ""},
                {"presentation": "empty-json-array", "hex": "5b5d"},
                {"presentation": "empty-json-array-lf", "hex": "5b5d0a"},
                {"presentation": "empty-json-array-crlf", "hex": "5b5d0d0a"},
            ],
            "arbitrary_stdout_forbidden": True,
            "exact_id_inventory_argv": [
                "<exact-pinned-docker-cli>",
                "ps",
                "--all",
                "--quiet",
                "--no-trunc",
                "--filter",
                "id=<exact-container-id>",
            ],
            "successor_label_inventory_argv": [
                "<exact-pinned-docker-cli>",
                "ps",
                "--all",
                "--quiet",
                "--no-trunc",
                "--filter",
                "label=io.patchloop.managed=d121-isolation-successor",
            ],
            "observation_order_before_validation": [
                "remove-by-exact-id",
                "inspect-by-exact-id",
                "exact-id-inventory",
                "successor-label-inventory",
            ],
            "exact_id_inventory_must_be_empty": True,
            "successor_label_inventory_must_be_empty": True,
            "both_inventories_execute_even_if_presentation_validation_fails": True,
            "raw_stderr_persisted": False,
            "bounded_stderr_size_and_sha_persisted": True,
        },
        "success_boundary": {
            "hash_only_isolation_profile_verified_may_become_true": True,
            "trusted_cutoff_anchor_verified_remains_false": True,
            "record_projection_isolation_verified_remains_false": True,
            "independence_remains_false": True,
            "retrieval_agent_and_core_remain_closed": True,
        },
    }


def _authority() -> dict[str, Any]:
    return {
        "partial_failure_sealed": True,
        "cleanup_failure_diagnosis_recorded": True,
        "root_cause_source_consistent_and_self_attested": True,
        "root_cause_portably_proved": False,
        "cleanup_correction_candidate_ready": True,
        "exact_candidate_user_approval_received": False,
        "d119_mutation_authorized": False,
        "d119_retry_resume_or_repair_authorized": False,
        "successor_implementation_authorized": False,
        "successor_execution_authorization_candidate_preparation_authorized": False,
        "fresh_successor_run_authorized": False,
        "successor_run_count": 0,
        "opaque_source_read_count": 0,
        "record_container_parse_count": 0,
        "record_field_read_count": 0,
        "pool_selection_acquisition_or_freeze_authorized": False,
        "issue_labeling_or_review_authorized": False,
        "matcher_classifier_or_calibration_authorized": False,
        "score_policy_or_index_mutation_authorized": False,
        "retrieval_or_runtime_injection_authorized": False,
        "agent_provider_evaluator_or_core_authorized": False,
        "docker_or_network_call_count_during_candidate_build_self_attested": 0,
        "subprocess_or_socket_instrumented_during_materialization": False,
        "focused_test_forbidden_boundary_guards_defined": True,
        "added_model_cost_usd": 0,
    }


def _preflight_body(
    *, recorded_at: str, context: Mapping[str, Any], implementation: Mapping[str, Any]
) -> dict[str, Any]:
    diagnosis = _diagnosis_contract()
    action = _future_action()
    return {
        "milestone": MILESTONE,
        "evidence_kind": "append-only-d119-partial-failure-and-cleanup-contract-audit",
        "recorded_at": recorded_at,
        "d119_partial_state": dict(context),
        "diagnosis": diagnosis,
        "prospective_d121_action": action,
        "prospective_d121_action_hash": sha256_bytes(_canonical_bytes(action)),
        "d120_implementation_state": dict(implementation),
        "evidence_boundary": {
            "d119_files_mutated": False,
            "opaque_source_files_opened": False,
            "docker_or_network_invoked_self_attested": False,
            "materialization_subprocess_or_socket_instrumentation": False,
            "zero_call_claim_evidence_kind": "source-path-static-audit-and-focused-test-guards",
            "operator_observation_is_not_d119_journal_evidence": True,
            "root_cause_portable_proof_claimed": False,
            "probe_success_claimed": False,
        },
        "authority": _authority(),
    }


def _candidate_body(
    *, recorded_at: str, preflight: Mapping[str, Any], preflight_binding: Mapping[str, Any]
) -> dict[str, Any]:
    action = preflight["semantic_body"]["prospective_d121_action"]
    return {
        "milestone": MILESTONE,
        "evidence_kind": "d119-cleanup-correction-authorization-candidate",
        "recorded_at": recorded_at,
        "preflight": dict(preflight_binding),
        "candidate_status": "awaiting-exact-user-approval",
        "failure_status": "PARTIAL_CONSUMED_FAILED",
        "probe_outcome": "UNSEALED_UNKNOWN",
        "proposed_action": action,
        "proposed_action_hash": sha256_bytes(_canonical_bytes(action)),
        "approval_contract": {
            "exact_candidate_id_required": True,
            "exact_semantic_body_sha_required": True,
            "exact_file_sha_required": True,
            "d120_approval_authorizes_only_d121_implementation_test_readiness_and_candidate": True,
            "d121_execution_requires_separate_exact_candidate_approval": True,
            "approval_does_not_authorize_d119_mutation_or_retry": True,
        },
        "authority": _authority(),
    }


def _gate_body(
    *,
    recorded_at: str,
    context: Mapping[str, Any],
    implementation: Mapping[str, Any],
    preflight_binding: Mapping[str, Any],
    candidate_binding: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "milestone": MILESTONE,
        "evidence_kind": "d119-cleanup-correction-authorization-source-gate",
        "recorded_at": recorded_at,
        "d119_partial_state": dict(context),
        "preflight": dict(preflight_binding),
        "candidate": dict(candidate_binding),
        "d120_implementation_state": dict(implementation),
        "qualification": {
            "partial_failure_exactly_bound": True,
            "cleanup_failure_diagnosis_source_consistent_and_self_attested": True,
            "cleanup_root_cause_portably_proved": False,
            "first_probe_outcome": "UNSEALED_UNKNOWN",
            "durable_completed_session_count": 0,
            "d121_implementation_and_execution_candidate_plan_ready": True,
            "successor_execution_ready": False,
        },
        "authority": _authority(),
        "next_gate": "exact-d120-candidate-id-body-sha-file-sha-user-approval",
    }


def _output_state(repository: Path) -> str:
    present = [
        key
        for key, relative in OUTPUT_PATHS.items()
        if (repository / relative).exists() or _is_linklike(repository / relative)
    ]
    if not present:
        return "empty"
    if len(present) == len(OUTPUT_PATHS):
        return "complete"
    return "partial"


def _write_new(repository: Path, relative: Path, payload: Mapping[str, Any]) -> None:
    path = _resolved(repository, relative, must_exist=False, label="D-120 output")
    _require(not path.exists() and not _is_linklike(path), "D-120 output collision")
    content = _pretty_bytes(payload)
    with path.open("xb") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
    _require(_read_stable(path, label="D-120 output") == content, "D-120 output reread differs")


def _build_expected(
    *,
    context: Mapping[str, Any],
    implementation: Mapping[str, Any],
    preflight_recorded_at: str,
    candidate_recorded_at: str,
    gate_recorded_at: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    d119_failed_at = _parse_timestamp(context["journal"]["failed_at"], label="D-119 failure")
    artifact_times = [
        _parse_timestamp(preflight_recorded_at, label="D-120 preflight"),
        _parse_timestamp(candidate_recorded_at, label="D-120 candidate"),
        _parse_timestamp(gate_recorded_at, label="D-120 gate"),
    ]
    _require(
        d119_failed_at <= artifact_times[0],
        "D-120 preflight predates the sealed D-119 failure",
    )
    _require(
        all(left <= right for left, right in zip(artifact_times, artifact_times[1:], strict=False)),
        "D-120 artifact chronology differs",
    )
    preflight = _envelope(
        schema_version="d119-partial-failure-preflight-d120-v1",
        id_field="preflight_id",
        id_prefix="d120preflight_",
        body=_preflight_body(
            recorded_at=preflight_recorded_at,
            context=context,
            implementation=implementation,
        ),
    )
    preflight_content = _pretty_bytes(preflight)
    preflight_binding = _binding(
        OUTPUT_PATHS["preflight"],
        preflight_content,
        preflight_id=preflight["preflight_id"],
        semantic_body_hash=preflight["semantic_body_hash"],
    )
    candidate = _envelope(
        schema_version="d119-cleanup-correction-authorization-candidate-d120-v1",
        id_field="candidate_id",
        id_prefix="d120cleanupcandidate_",
        body=_candidate_body(
            recorded_at=candidate_recorded_at,
            preflight=preflight,
            preflight_binding=preflight_binding,
        ),
    )
    candidate_content = _pretty_bytes(candidate)
    candidate_binding = _binding(
        OUTPUT_PATHS["candidate"],
        candidate_content,
        candidate_id=candidate["candidate_id"],
        semantic_body_hash=candidate["semantic_body_hash"],
    )
    gate = _envelope(
        schema_version="d119-cleanup-correction-source-gate-d120-v1",
        id_field="gate_id",
        id_prefix="d120_",
        body=_gate_body(
            recorded_at=gate_recorded_at,
            context=context,
            implementation=implementation,
            preflight_binding=preflight_binding,
            candidate_binding=candidate_binding,
        ),
    )
    return preflight, candidate, gate


def run_d120_cleanup_correction_candidate(
    *, repository: str | Path | None = None
) -> dict[str, Any]:
    """Materialize or validate the append-only D-120 candidate."""

    repo = _repo_root(repository)
    state = _output_state(repo)
    if state == "complete":
        return validate_d120_source_gate(repository=repo)
    _require(state == "empty", "partial D-120 output state is not repairable")
    context_pre = _d119_partial_context(repo)
    implementation_pre = _d120_implementation_state(repo)
    now = datetime.now(UTC)
    times = [
        now.isoformat().replace("+00:00", "Z"),
        now.isoformat().replace("+00:00", "Z"),
        now.isoformat().replace("+00:00", "Z"),
    ]
    preflight, candidate, gate = _build_expected(
        context=context_pre,
        implementation=implementation_pre,
        preflight_recorded_at=times[0],
        candidate_recorded_at=times[1],
        gate_recorded_at=times[2],
    )
    _require(_d119_partial_context(repo) == context_pre, "D-119 changed before D-120 write")
    _require(
        _d120_implementation_state(repo) == implementation_pre,
        "D-120 implementation changed before write",
    )
    for key, payload in (
        ("preflight", preflight),
        ("candidate", candidate),
        ("source_gate", gate),
    ):
        _write_new(repo, OUTPUT_PATHS[key], payload)
    return validate_d120_source_gate(repository=repo)


def validate_d120_source_gate(*, repository: str | Path | None = None) -> dict[str, Any]:
    """Validate the checked-in D-120 candidate without Docker or source reads."""

    repo = _repo_root(repository)
    _require(_output_state(repo) == "complete", "D-120 output state is incomplete")
    context = _d119_partial_context(repo)
    implementation = _d120_implementation_state(repo)
    specs = (
        (
            "preflight",
            "preflight_id",
            "d120preflight_",
            "d119-partial-failure-preflight-d120-v1",
        ),
        (
            "candidate",
            "candidate_id",
            "d120cleanupcandidate_",
            "d119-cleanup-correction-authorization-candidate-d120-v1",
        ),
        (
            "source_gate",
            "gate_id",
            "d120_",
            "d119-cleanup-correction-source-gate-d120-v1",
        ),
    )
    values: dict[str, dict[str, Any]] = {}
    contents: dict[str, bytes] = {}
    for key, id_field, prefix, schema_version in specs:
        path = _resolved(repo, OUTPUT_PATHS[key], must_exist=True, label=key)
        content = _read_stable(path, label=key)
        value = _parse_json(content, label=key)
        _validate_envelope(
            value,
            schema_version=schema_version,
            id_field=id_field,
            id_prefix=prefix,
            label=key,
        )
        values[key] = value
        contents[key] = content
    times = [
        values["preflight"]["semantic_body"]["recorded_at"],
        values["candidate"]["semantic_body"]["recorded_at"],
        values["source_gate"]["semantic_body"]["recorded_at"],
    ]
    parsed_times = [_parse_timestamp(value, label="D-120 artifact") for value in times]
    _require(
        all(left <= right for left, right in zip(parsed_times, parsed_times[1:], strict=False)),
        "D-120 artifact chronology differs",
    )
    expected = _build_expected(
        context=context,
        implementation=implementation,
        preflight_recorded_at=times[0],
        candidate_recorded_at=times[1],
        gate_recorded_at=times[2],
    )
    for (key, *_), expected_value in zip(specs, expected, strict=True):
        _require(
            contents[key] == _pretty_bytes(expected_value),
            f"D-120 {key} expected payload differs",
        )
    _require(_d119_partial_context(repo) == context, "D-119 changed during validation")
    _require(
        _d120_implementation_state(repo) == implementation,
        "D-120 implementation changed during validation",
    )
    candidate = values["candidate"]
    gate = values["source_gate"]
    authority = gate["semantic_body"]["authority"]
    return {
        "status": "D119_PARTIAL_FAILURE_SEALED_D120_CANDIDATE_PENDING_APPROVAL",
        "candidate_id": candidate["candidate_id"],
        "candidate_semantic_body_hash": candidate["semantic_body_hash"],
        "candidate_file_bytes": len(contents["candidate"]),
        "candidate_file_sha256": sha256_bytes(contents["candidate"]),
        "gate_id": gate["gate_id"],
        "gate_semantic_body_hash": gate["semantic_body_hash"],
        "gate_file_bytes": len(contents["source_gate"]),
        "gate_file_sha256": sha256_bytes(contents["source_gate"]),
        "partial_failure_status": "PARTIAL_CONSUMED_FAILED",
        "probe_outcome": "UNSEALED_UNKNOWN",
        "cleanup_correction_candidate_ready": authority["cleanup_correction_candidate_ready"],
        "exact_candidate_user_approval_received": False,
        "successor_execution_authorization_candidate_preparation_authorized": False,
        "fresh_successor_run_authorized": False,
    }


__all__ = [
    "D120AuthorizationError",
    "run_d120_cleanup_correction_candidate",
    "validate_d120_source_gate",
]
