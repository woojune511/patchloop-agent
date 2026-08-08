"""D-099 public-evidence review and semantic-deduplication proposal.

This module deliberately does not import the mutable memory review/index store.
Portable validation needs only checked-in public artifacts.  The optional raw
audit is explicit and operates on a disposable SQLite/WAL copy.
"""

from __future__ import annotations

import gc
import json
import re
import shutil
import sqlite3
import tempfile
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from patchloop.contracts import (
    D099ReviewProposal,
    DatasetRole,
)
from patchloop.dataset import load_dataset_manifest
from patchloop.errors import ContractError
from patchloop.runtime import repository_root
from patchloop.task_loader import load_public_task
from patchloop.util import canonical_json, ensure_within, sha256_bytes, sha256_json, sha256_text

SCHEMA_VERSION = "memory-public-review-proposal-d099-v1"
RECORDED_AT = "2026-08-05T11:01:05Z"
SOURCE_REPORT_PATH = "reports/live-pilot/dev-no-memory-condition-neutral-3000k-20260805-r1.json"
SOURCE_REPORT_BYTES = 117_209
SOURCE_REPORT_FILE_SHA = "sha256:ad87fa8c540552da62d964a430c29b032097b5cabbe78f0102c23cf36330b2dc"
SOURCE_REPORT_BODY_SHA = "sha256:e35cab52597c3ec6e884f074f9acf346dec65301e22d11edc2de56db7be9eacf"
SOURCE_REPORT_ID = "d098_e35cab52597c3ec6e884f074f9acf346dec65301e22d11edc2de56db7be9eacf"
SOURCE_REPORT_SCHEMA = "condition-neutral-no-memory-baseline-d098-evidence-v1"
EXPERIMENT_ID = "dev-no-memory-condition-neutral-3000k-20260805-r1"
EXECUTION_HASH = "sha256:1a5aaccc4f95f71d285e0e0a9c8ccb27f82e235fbff465ef30f095401fde25f4"
SUITE_HASH = "sha256:e32000918e96e6773986e99d5aa9dc29a9a91fc4f0a89f5e63adde69f78267ed"
SCHEDULE_HASH = "sha256:2ecbf257117481bfa31d62454221af243cc541470a91abeefdcae1f0912a552d"
DATASET_MANIFEST_HASH = "sha256:cf608ca1a35cb270f2e4cadcf0b34912256ef1c9cd3c0757a89692f8a5fdf786"

# These exact values make rehashed semantic tampering fail on a clean checkout.
EXPECTED_SEMANTIC_BODY_HASH: str | None = (
    "sha256:63c74999242f6217f2a81c9c2dc22d618d2be137948580f93401341c4ea49574"
)
EXPECTED_PROPOSAL_FILE_SHA: str | None = (
    "sha256:24e34b02a66fc132d333bb51614a10786d38bc188b5550432a5f21f435f21493"
)
EXPECTED_PROPOSAL_BYTES: int | None = 77_942

DEFAULT_PROPOSAL_PATH = Path(
    "reports/memory-development/d099-public-evidence-review-dedup-proposal.json"
)
PATCH_ARTIFACT_ROOT = Path("reports/memory-development/artifacts/d099")


class D099ReviewError(ContractError):
    """Stable contract failure for the D-099 review boundary."""


def _coordinates(*items: tuple[str, int]) -> tuple[tuple[str, int], ...]:
    return items


SOURCE_SPECS: tuple[dict[str, Any], ...] = (
    {
        "run_id": "run_575da4ead3334551",
        "failure_record_id": "fail_0f5c0cd58af05907ba3285e4e7ef069e",
        "task_id": "pyfakefs-makedirs-parent-traversal",
        "repetition": 1,
        "semantic_group_id": "platform-emulation-matrix-gap",
        "assessment": (
            "The submitted change preserves a final directory outcome but does not "
            "demonstrate the complete public traversal matrix across intermediate and "
            "leaf components, path types, creation modes, and platform modes."
        ),
        "causal_confidence": 0.72,
        "evidence": _coordinates(
            ("public_inspection", 314),
            ("mutation", 486),
            ("visible_check", 506),
            ("diff", 512),
            ("review", 518),
            ("submission", 521),
            ("generic_outcome", 524),
        ),
    },
    {
        "run_id": "run_74364afdc3d94f9c",
        "failure_record_id": "fail_6b7b036074a2590d97db1afdfe90a89d",
        "task_id": "pyfakefs-makedirs-parent-traversal",
        "repetition": 2,
        "semantic_group_id": "platform-emulation-matrix-gap",
        "assessment": (
            "The submitted change narrows traversal handling but leaves the public "
            "string and bytes path variants coupled to platform-specific component "
            "handling without complete matrix evidence."
        ),
        "causal_confidence": 0.76,
        "evidence": _coordinates(
            ("public_inspection", 7),
            ("mutation", 134),
            ("visible_check", 151),
            ("diff", 157),
            ("review", 163),
            ("submission", 166),
            ("generic_outcome", 169),
        ),
    },
    {
        "run_id": "run_5ffc2e1c58784e17",
        "failure_record_id": "fail_2cf07eaf03315e54908197f76180394b",
        "task_id": "hf-hub-xet-endpoint-propagation",
        "repetition": 1,
        "semantic_group_id": "request-context-propagation-gap",
        "assessment": (
            "The submitted change adds request endpoint context at one metadata path "
            "without public evidence that every caller and every relative, default, "
            "foreign-origin, and implicit-endpoint branch preserves that context."
        ),
        "causal_confidence": 0.86,
        "evidence": _coordinates(
            ("public_inspection", 36),
            ("public_inspection", 60),
            ("mutation", 78),
            ("visible_check", 93),
            ("diff", 99),
            ("review", 105),
            ("submission", 108),
            ("generic_outcome", 111),
        ),
    },
    {
        "run_id": "run_88f96fae3d2442e6",
        "failure_record_id": "fail_8edc6a7fd4f3506f92a149698e55da6e",
        "task_id": "hf-hub-xet-endpoint-propagation",
        "repetition": 2,
        "semantic_group_id": "request-context-propagation-gap",
        "assessment": (
            "The submitted change propagates endpoint context through more public "
            "callers, but the trace does not establish complete call-graph and route-"
            "ownership coverage required by the public contract."
        ),
        "causal_confidence": 0.88,
        "evidence": _coordinates(
            ("public_inspection", 31),
            ("public_inspection", 493),
            ("mutation", 696),
            ("visible_check", 701),
            ("diff", 707),
            ("review", 713),
            ("submission", 716),
            ("generic_outcome", 719),
        ),
    },
    {
        "run_id": "run_3dc602aab8964d77",
        "failure_record_id": "fail_dac1b9595479551688a9613db9462927",
        "task_id": "anyio-interrupt-runner-cleanup",
        "repetition": 2,
        "semantic_group_id": "interrupt-lifecycle-unresolved",
        "assessment": (
            "The submitted change alters cancellation handling and runner ownership, "
            "but one observation is insufficient to promote a general lifecycle rule "
            "covering propagation, non-resumption, and exactly-once cleanup."
        ),
        "causal_confidence": 0.58,
        "evidence": _coordinates(
            ("public_inspection", 238),
            ("public_inspection", 247),
            ("mutation", 1087),
            ("visible_check", 1092),
            ("diff", 1098),
            ("review", 1104),
            ("submission", 1107),
            ("generic_outcome", 1110),
        ),
    },
    {
        "run_id": "run_59aac91defac456b",
        "failure_record_id": "fail_19d13b555e5f5e21b89c0dde9e593ec8",
        "task_id": "loguru-invalid-format-feedback",
        "repetition": 1,
        "semantic_group_id": "diagnostic-contract-unresolved",
        "assessment": (
            "The submitted diagnostic path can itself be interpreted as formatting "
            "syntax, while the public contract also spans static, dynamic, colored, "
            "catch, and patcher-provided record paths; a general rule remains pending."
        ),
        "causal_confidence": 0.82,
        "evidence": _coordinates(
            ("public_inspection", 28),
            ("mutation", 52),
            ("visible_check", 67),
            ("visible_check", 71),
            ("visible_check", 74),
            ("diff", 79),
            ("review", 85),
            ("submission", 88),
            ("generic_outcome", 91),
        ),
    },
    {
        "run_id": "run_cc179262fa664600",
        "failure_record_id": "fail_bcf0bf2e95765d42b925742d955da82e",
        "task_id": "loguru-invalid-format-feedback",
        "repetition": 2,
        "semantic_group_id": "diagnostic-contract-unresolved",
        "assessment": (
            "The second submitted diagnostic follows the same public formatting "
            "boundary and repeats the risk that explanatory placeholder syntax creates "
            "a secondary error instead of useful feedback."
        ),
        "causal_confidence": 0.86,
        "evidence": _coordinates(
            ("public_inspection", 17),
            ("public_inspection", 23),
            ("mutation", 125),
            ("visible_check", 130),
            ("visible_check", 134),
            ("visible_check", 137),
            ("diff", 142),
            ("review", 148),
            ("submission", 151),
            ("generic_outcome", 154),
        ),
    },
    {
        "run_id": "run_ac3ae1a7009a4e8b",
        "failure_record_id": "fail_f90fa668a6945abe98ef6dd5e4761a97",
        "task_id": "tox-cross-section-empty-substitution",
        "repetition": 2,
        "semantic_group_id": "exception-origin-state-conflation",
        "assessment": (
            "The submitted change handles lookup absence and post-lookup transformation "
            "inside one exception boundary, conflating a missing source with an existing "
            "value that resolves to an empty state."
        ),
        "causal_confidence": 0.92,
        "evidence": _coordinates(
            ("public_inspection", 171),
            ("public_inspection", 174),
            ("mutation", 181),
            ("visible_check", 188),
            ("diff", 194),
            ("review", 200),
            ("submission", 203),
            ("generic_outcome", 206),
        ),
    },
    {
        "run_id": "run_d5c2e22b485a4578",
        "failure_record_id": "fail_ab3918ee4a3c5f34bc9d04a8f0970c00",
        "task_id": "tox-cross-section-empty-substitution",
        "repetition": 1,
        "semantic_group_id": "exception-origin-state-conflation",
        "assessment": (
            "The byte-identical submitted change repeats the same public exception-"
            "origin conflation between absent lookup state and an empty transformed value."
        ),
        "causal_confidence": 0.92,
        "evidence": _coordinates(
            ("public_inspection", 75),
            ("public_inspection", 78),
            ("public_inspection", 81),
            ("mutation", 88),
            ("visible_check", 95),
            ("diff", 101),
            ("review", 107),
            ("submission", 110),
            ("generic_outcome", 113),
        ),
    },
)


GROUP_SPECS: tuple[dict[str, Any], ...] = (
    {
        "semantic_group_id": "platform-emulation-matrix-gap",
        "representative_run_id": "run_575da4ead3334551",
        "relation": "semantic-cluster",
        "merge_rationale": (
            "Both repetitions address the same public traversal contract and leave "
            "different portions of its platform and path-type matrix under-validated."
        ),
        "dedup_confidence": 0.74,
        "disposition": "candidate",
        "proposed_rule": {
            "failure_class": "PLATFORM_EMULATION_MATRIX_GAP",
            "phase": "IMPLEMENT",
            "description": (
                "An emulation fix validates a final outcome without preserving the "
                "observable intermediate semantics across the public platform matrix."
            ),
            "preconditions": [
                "The task emulates platform behavior with observable intermediate "
                "and leaf effects.",
                "The public contract names more than one path type, platform mode, "
                "or error branch.",
            ],
            "diagnostic_evidence": [
                "Enumerate intermediate and leaf effects separately before changing normalization.",
                "Build a public matrix for platform mode, path type, creation mode, "
                "existing state, and error state.",
            ],
            "recommended_actions": [
                "Implement the smallest change that preserves every matrix cell "
                "named by the public contract.",
                "Run the registered regression and add targeted public reasoning "
                "evidence for uncovered cells.",
            ],
            "do_not_apply_when": [
                "The public contract has no observable intermediate behavior.",
                "All named platform and path-type branches intentionally share "
                "identical semantics.",
            ],
            "applicable_languages": ["python"],
            "confidence": 0.74,
            "admission_decision": "not_made",
        },
    },
    {
        "semantic_group_id": "request-context-propagation-gap",
        "representative_run_id": "run_5ffc2e1c58784e17",
        "relation": "semantic-cluster",
        "merge_rationale": (
            "Both repetitions modify endpoint-aware metadata behavior but do not show "
            "complete coverage of every public call-graph edge and route ownership case."
        ),
        "dedup_confidence": 0.94,
        "disposition": "candidate",
        "proposed_rule": {
            "failure_class": "CONTEXT_PROPAGATION_GAP",
            "phase": "IMPLEMENT",
            "description": (
                "Request-scoped context is added at a leaf while one or more public "
                "callers or ownership branches still use an implicit default."
            ),
            "preconditions": [
                "Behavior depends on context selected by a caller rather than a "
                "process-wide default.",
                "The public contract requires preservation through multiple access paths.",
            ],
            "diagnostic_evidence": [
                "Enumerate every caller-to-leaf edge that can create or transform "
                "the affected value.",
                "Separate relative, default-origin, foreign-origin, custom, and "
                "implicit-default cases.",
            ],
            "recommended_actions": [
                "Thread the context explicitly through every required edge without "
                "rewriting foreign ownership.",
                "Verify every public route class and each caller that omits explicit context.",
            ],
            "do_not_apply_when": [
                "The value is intentionally process-global and the public contract "
                "confirms that policy.",
                "Only one construction path exists and no caller-specific context can vary.",
            ],
            "applicable_languages": ["python"],
            "confidence": 0.88,
            "admission_decision": "not_made",
        },
    },
    {
        "semantic_group_id": "interrupt-lifecycle-unresolved",
        "representative_run_id": "run_3dc602aab8964d77",
        "relation": "single",
        "merge_rationale": (
            "Only one eligible completed submission exists, so no cross-run semantic "
            "deduplication evidence is available for a reusable lifecycle rule."
        ),
        "dedup_confidence": 1.0,
        "disposition": "hold",
        "unresolved_reason": (
            "Public code suggests cancellation-consumption and owner-task cleanup risk, "
            "but one run does not establish a general rule across resume, propagation, "
            "and exactly-once cleanup states."
        ),
        "next_review_actions": [
            "Review the public lifecycle as an explicit owner, worker, future, and "
            "fixture state machine.",
            "Seek independent public evidence for interrupt propagation, "
            "non-resumption, and cleanup cardinality.",
        ],
    },
    {
        "semantic_group_id": "diagnostic-contract-unresolved",
        "representative_run_id": "run_59aac91defac456b",
        "relation": "semantic-cluster",
        "merge_rationale": (
            "Both repetitions introduce a similar secondary diagnostic-formatting risk, "
            "but the broader reusable boundary across all public formatter modes "
            "remains unresolved."
        ),
        "dedup_confidence": 0.96,
        "disposition": "hold",
        "unresolved_reason": (
            "The repeated patch defect is concrete, while the correct general memory rule "
            "for static, dynamic, colored, catch, and custom-record paths still needs review."
        ),
        "next_review_actions": [
            "Separate primary formatting failure from construction of the diagnostic message.",
            "Review every public formatter mode and both catch behaviors before "
            "proposing a general rule.",
        ],
    },
    {
        "semantic_group_id": "exception-origin-state-conflation",
        "representative_run_id": "run_ac3ae1a7009a4e8b",
        "relation": "exact-duplicate",
        "merge_rationale": (
            "Both repetitions submitted the same patch bytes and share the same public "
            "lookup-versus-transformation exception boundary."
        ),
        "dedup_confidence": 1.0,
        "disposition": "candidate",
        "proposed_rule": {
            "failure_class": "SEMANTIC_STATE_CONFLATION",
            "phase": "IMPLEMENT",
            "description": (
                "One exception boundary treats source lookup failure and later value "
                "transformation failure as the same semantic state."
            ),
            "preconditions": [
                "The public contract distinguishes a missing source from an existing "
                "empty or transformed value.",
                "Lookup and transformation can raise the same exception type for "
                "different reasons.",
            ],
            "diagnostic_evidence": [
                "Trace lookup, filtering, substitution, defaulting, and caller "
                "fallback as separate stages.",
                "Exercise missing, existing-empty, matching, defaulted, caller-context, "
                "and fallback cases.",
            ],
            "recommended_actions": [
                "Narrow exception handling to the operation whose absence semantics it represents.",
                "Preserve the distinct empty and default states through later transformations.",
            ],
            "do_not_apply_when": [
                "The public API intentionally defines lookup and transformation "
                "failure as identical.",
                "The operations cannot produce distinguishable semantic states.",
            ],
            "applicable_languages": ["python"],
            "confidence": 0.92,
            "admission_decision": "not_made",
        },
    },
)


EXPECTED_GROUP_MEMBERS = {
    group_id: tuple(
        (source["run_id"], source["failure_record_id"])
        for source in SOURCE_SPECS
        if source["semantic_group_id"] == group_id
    )
    for group_id in (group["semantic_group_id"] for group in GROUP_SPECS)
}

EXPECTED_EXCLUDED_RESOLVED = (
    {
        "run_id": "run_3fe55fd3847d4a4d",
        "task_id": "pdm-ignore-active-venv-resolution",
        "repetition": 1,
        "outcome_kind": "resolved",
        "reason": "resolved",
    },
    {
        "run_id": "run_92bf10d2a6b14601",
        "task_id": "pdm-ignore-active-venv-resolution",
        "repetition": 2,
        "outcome_kind": "resolved",
        "reason": "resolved",
    },
)
EXPECTED_EXCLUDED_BUDGET = (
    {
        "run_id": "run_7ecb4b2489c34982",
        "task_id": "anyio-interrupt-runner-cleanup",
        "repetition": 1,
        "outcome_kind": "agent_failure",
        "reason": "canonical_pre_provider_budget",
    },
)

_PROPOSAL_LEAK_PATTERNS = (
    re.compile(r"(?i)diff --git\s"),
    re.compile(r"@@(?:\s|$)"),
    re.compile(r"(?i)(?:\+\+\+|---)\s+[ab]/"),
    re.compile(r"```"),
    re.compile(r"(?i)\breference\.patch\b"),
    re.compile(r"(?i)\bprivate\.ya?ml\b"),
    re.compile(r"(?i)\.patchloop-hidden(?:[/\\]|$)"),
    re.compile(r"(?i)(?:^|[/\\])hidden(?:[/\\]|_tests?(?:[/\\]|\.))"),
    re.compile(r"(?i)\bOPENAI_API_KEY\s*[:=]"),
    re.compile(r"(?i)\b(?:Bearer\s+|sk-(?:proj-)?)[A-Za-z0-9_-]{12,}"),
    re.compile(r"(?m)^\s*(?:async\s+)?def\s+[A-Za-z_]\w*\s*\("),
    re.compile(r"(?m)^\s*class\s+[A-Za-z_]\w*(?:\([^)]*\))?\s*:"),
    re.compile(r"(?i)[A-Z]:\\Users\\"),
)
_PATCH_LEAK_PATTERNS = (
    re.compile(rb"(?i)\.patchloop-hidden(?:[/\\]|$)"),
    re.compile(rb"(?i)\breference\.patch\b"),
    re.compile(rb"(?i)\bprivate\.ya?ml\b"),
    re.compile(rb"(?i)\bOPENAI_API_KEY\s*[:=]"),
    re.compile(rb"(?i)\b(?:Bearer\s+|sk-(?:proj-)?)[A-Za-z0-9_-]{12,}"),
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise D099ReviewError(message)


def _load_json_object(content: bytes, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise D099ReviewError(f"{label} is not valid JSON") from exc
    if not isinstance(value, dict):
        raise D099ReviewError(f"{label} must be a JSON object")
    return value


def _descriptor(path: Path, *, relative_to: Path) -> dict[str, Any]:
    try:
        content = path.read_bytes()
        relative = path.resolve().relative_to(relative_to.resolve()).as_posix()
    except (OSError, ValueError) as exc:
        raise D099ReviewError("D-099 public artifact is unavailable") from exc
    return {"path": relative, "bytes": len(content), "sha256": sha256_bytes(content)}


def _load_source_report(repo_root: Path) -> tuple[dict[str, Any], bytes]:
    path = repo_root / SOURCE_REPORT_PATH
    try:
        content = path.read_bytes()
    except OSError as exc:
        raise D099ReviewError("D-098 source seal is unavailable") from exc
    _require(len(content) == SOURCE_REPORT_BYTES, "D-098 source seal byte count drifted")
    _require(sha256_bytes(content) == SOURCE_REPORT_FILE_SHA, "D-098 source seal hash drifted")
    report = _load_json_object(content, label="D-098 source seal")
    _require(report.get("schema_version") == SOURCE_REPORT_SCHEMA, "D-098 schema drifted")
    _require(report.get("report_id") == SOURCE_REPORT_ID, "D-098 report identity drifted")
    _require(
        report.get("semantic_body_hash") == SOURCE_REPORT_BODY_SHA,
        "D-098 recorded semantic hash drifted",
    )
    body = report.get("semantic_body")
    _require(isinstance(body, dict), "D-098 semantic body is unavailable")
    _require(
        sha256_text(canonical_json(body)) == SOURCE_REPORT_BODY_SHA,
        "D-098 semantic body hash does not recompute",
    )
    return report, content


def _report_artifact_map(body: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    artifacts = body.get("raw_local_artifacts")
    _require(isinstance(artifacts, list), "D-098 raw artifact projection is unavailable")
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            raise D099ReviewError("D-098 raw artifact projection is invalid")
        role = artifact.get("role")
        run_id = artifact.get("run_id")
        if isinstance(role, str) and isinstance(run_id, str):
            key = (role, run_id)
            _require(key not in result, "D-098 raw artifact identity is duplicated")
            result[key] = artifact
    return result


def _validate_report_population(body: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    experiment = body.get("experiment")
    environment = body.get("environment")
    baseline = body.get("baseline_admission")
    candidate_set = body.get("memory_review_candidates")
    _require(isinstance(experiment, dict), "D-098 experiment projection is unavailable")
    _require(isinstance(environment, dict), "D-098 environment projection is unavailable")
    _require(isinstance(baseline, dict), "D-098 baseline admission is unavailable")
    _require(isinstance(candidate_set, dict), "D-098 candidate set is unavailable")
    _require(
        experiment.get("experiment_id") == EXPERIMENT_ID
        and experiment.get("execution_hash") == EXECUTION_HASH
        and experiment.get("suite_hash") == SUITE_HASH
        and experiment.get("schedule_hash") == SCHEDULE_HASH,
        "D-098 campaign identity drifted",
    )
    _require(
        (environment.get("dataset") or {}).get("manifest_hash") == DATASET_MANIFEST_HASH,
        "D-098 dataset identity drifted",
    )
    _require(
        baseline.get("passed") is True
        and baseline.get("comparison_denominator_eligible") is True
        and baseline.get("memory_review_eligible") is True
        and baseline.get("memory_admission_unlocked") is False,
        "D-098 review eligibility boundary drifted",
    )
    candidates = candidate_set.get("candidates")
    _require(
        candidate_set.get("schema_version") == "memory-review-candidate-set-v1"
        and candidate_set.get("candidate_count") == 9
        and isinstance(candidates, list)
        and len(candidates) == 9,
        "D-098 candidate set drifted",
    )
    expected_pairs = [(source["run_id"], source["failure_record_id"]) for source in SOURCE_SPECS]
    actual_pairs = [
        (candidate.get("run_id"), candidate.get("failure_record_id"))
        for candidate in candidates
        if isinstance(candidate, dict)
    ]
    _require(actual_pairs == expected_pairs, "D-098 candidate order or membership drifted")
    _require(
        candidate_set.get("excluded_budget_run_ids") == ["run_7ecb4b2489c34982"],
        "D-098 budget exclusion drifted",
    )
    _require(
        candidate_set.get("excluded_resolved_count") == 2,
        "D-098 resolved exclusion count drifted",
    )
    return tuple(candidates)


def _public_dataset_bindings(repo_root: Path) -> dict[str, dict[str, Any]]:
    manifest, manifest_hash, _ = load_dataset_manifest(repo_root / "data/dataset-manifest.yaml")
    _require(manifest_hash == DATASET_MANIFEST_HASH, "frozen dataset manifest hash drifted")
    result: dict[str, dict[str, Any]] = {}
    expected_tasks = {source["task_id"] for source in SOURCE_SPECS}
    for entry in manifest.tasks:
        if entry.task_id not in expected_tasks:
            continue
        _require(entry.role == DatasetRole.MEMORY_DEVELOPMENT, "D-099 source role drifted")
        _require(entry.task_version == 1, "D-099 task version drifted")
        public_path = ensure_within(repo_root, f"{entry.path}/public.yaml")
        public = load_public_task(public_path)
        _require(public.task_id == entry.task_id, "D-099 public task identity drifted")
        _require(
            sha256_json(public.model_dump(mode="json")) == entry.public_spec_hash,
            "D-099 public task semantic hash drifted",
        )
        result[entry.task_id] = {
            "descriptor": _descriptor(public_path, relative_to=repo_root),
            "public_spec_hash": entry.public_spec_hash,
        }
    _require(set(result) == expected_tasks, "D-099 public task coverage drifted")
    return result


def _proposal_text(body: dict[str, Any]) -> str:
    parts: list[str] = []
    for source in body["sources"]:
        parts.append(source["assessment"])
    for group in body["groups"]:
        parts.append(group["merge_rationale"])
        proposed = group.get("proposed_rule")
        if proposed is not None:
            parts.extend(
                [
                    proposed["failure_class"],
                    proposed["description"],
                    *proposed["preconditions"],
                    *proposed["diagnostic_evidence"],
                    *proposed["recommended_actions"],
                    *proposed["do_not_apply_when"],
                ]
            )
        else:
            parts.append(group["unresolved_reason"])
            parts.extend(group["next_review_actions"])
    parts.append(body["next_gate"])
    return "\n".join(parts)


def _require_leak_safe_text(body: dict[str, Any]) -> None:
    text = _proposal_text(body)
    if any(pattern.search(text) for pattern in _PROPOSAL_LEAK_PATTERNS):
        raise D099ReviewError("D-099 proposal text leak scan failed")


def _require_leak_safe_patch(content: bytes) -> None:
    if any(pattern.search(content) for pattern in _PATCH_LEAK_PATTERNS):
        raise D099ReviewError("D-099 submitted patch leak scan failed")


def _state_bundle_fingerprint(state_path: Path) -> dict[str, dict[str, Any] | None]:
    fingerprint: dict[str, dict[str, Any] | None] = {}
    for suffix in ("", "-wal", "-shm"):
        path = Path(f"{state_path}{suffix}")
        if not path.exists():
            fingerprint[suffix or "database"] = None
            continue
        stat = path.stat()
        fingerprint[suffix or "database"] = {
            "bytes": stat.st_size,
            "mtime_ns": stat.st_mtime_ns,
            "sha256": sha256_bytes(path.read_bytes()),
        }
    return fingerprint


def _copy_state_snapshot(state_path: Path, destination: Path) -> Path:
    _require(state_path.is_file(), "D-099 raw state database is unavailable")
    snapshot = destination / state_path.name
    shutil.copy2(state_path, snapshot)
    wal = Path(f"{state_path}-wal")
    if wal.is_file():
        shutil.copy2(wal, Path(f"{snapshot}-wal"))
    return snapshot


def _artifact_path(runtime: Path, digest: str) -> Path:
    hex_digest = digest.removeprefix("sha256:")
    _require(len(hex_digest) == 64, "D-099 event artifact identity is invalid")
    return runtime / "artifacts" / "objects" / "sha256" / hex_digest[:2] / hex_digest[2:]


def _require_artifact(runtime: Path, digest: str, expected_bytes: int | None = None) -> int:
    path = _artifact_path(runtime, digest)
    try:
        content = path.read_bytes()
    except OSError as exc:
        raise D099ReviewError("D-099 selected public artifact is unavailable") from exc
    _require(sha256_bytes(content) == digest, "D-099 selected public artifact hash drifted")
    if expected_bytes is not None:
        _require(len(content) == expected_bytes, "D-099 selected public artifact size drifted")
    return len(content)


def _artifact_hash_from_path(value: Any) -> str:
    _require(isinstance(value, str), "D-099 event artifact path is unavailable")
    normalized = value.replace("\\", "/")
    match = re.search(r"/objects/sha256/([0-9a-f]{2})/([0-9a-f]{62})$", normalized)
    _require(match is not None, "D-099 event artifact path is not content-addressed")
    return f"sha256:{match.group(1)}{match.group(2)}"


def _event_ref(
    *,
    runtime: Path,
    event: dict[str, Any],
    role: str,
    submitted_patch_sha: str,
    submitted_patch_bytes: int,
    failure_record_id: str,
) -> dict[str, Any]:
    payload = event.get("payload")
    _require(isinstance(payload, dict), "D-099 selected event payload is invalid")
    event_type = event.get("type")
    expected_types = {
        "public_inspection": "ToolSucceeded",
        "mutation": "PatchApplied",
        "visible_check": "ToolSucceeded",
        "diff": "ToolSucceeded",
        "review": "ReviewRecorded",
        "submission": "SubmissionAccepted",
        "generic_outcome": "FailureTagged",
    }
    _require(event_type == expected_types[role], "D-099 selected event type is unsafe")
    artifact_hash: str | None = None
    artifact_bytes: int | None = None
    check_id: str | None = None
    if role == "public_inspection":
        _require(
            payload.get("tool") in {"search_files", "read_file"},
            "D-099 public inspection tool is not allowed",
        )
        result_artifact = payload.get("result_artifact")
        _require(isinstance(result_artifact, dict), "D-099 inspection artifact is missing")
        artifact_hash = result_artifact.get("content_hash")
        artifact_bytes = result_artifact.get("size_bytes")
        _require(
            isinstance(artifact_hash, str) and type(artifact_bytes) is int,
            "D-099 inspection artifact binding is invalid",
        )
        _require_artifact(runtime, artifact_hash, artifact_bytes)
    elif role == "visible_check":
        _require(
            payload.get("tool") == "run_check" and payload.get("passed") is True,
            "D-099 visible-check evidence drifted",
        )
        check_id = payload.get("check_id")
        _require(isinstance(check_id, str), "D-099 visible check ID is unavailable")
        _require(
            payload.get("worktree_diff_hash") == submitted_patch_sha,
            "D-099 visible check patch binding drifted",
        )
        artifact_hash = _artifact_hash_from_path(payload.get("artifact_path"))
        artifact_bytes = _require_artifact(runtime, artifact_hash)
    elif role == "diff":
        _require(payload.get("tool") == "get_diff", "D-099 diff evidence tool drifted")
        _require(
            payload.get("worktree_diff_hash") == submitted_patch_sha
            and payload.get("patch_hash") == submitted_patch_sha,
            "D-099 diff patch binding drifted",
        )
        artifact_hash = _artifact_hash_from_path(payload.get("artifact_path"))
        artifact_bytes = _require_artifact(runtime, artifact_hash)
    elif role in {"mutation", "review"}:
        _require(
            payload.get("worktree_diff_hash") == submitted_patch_sha,
            "D-099 mutation/review patch binding drifted",
        )
        artifact_hash = submitted_patch_sha
        artifact_bytes = _require_artifact(runtime, artifact_hash, submitted_patch_bytes)
    elif role == "submission":
        artifact = payload.get("submitted_patch_artifact")
        _require(isinstance(artifact, dict), "D-099 submission artifact is missing")
        _require(
            payload.get("worktree_diff_hash") == submitted_patch_sha
            and artifact.get("content_hash") == submitted_patch_sha
            and artifact.get("size_bytes") == submitted_patch_bytes,
            "D-099 submission patch binding drifted",
        )
        artifact_hash = submitted_patch_sha
        artifact_bytes = _require_artifact(runtime, artifact_hash, submitted_patch_bytes)
    else:
        _require(
            payload.get("failure_id") == failure_record_id
            and payload.get("primary_cause") == "hidden-acceptance-failure",
            "D-099 generic outcome binding drifted",
        )

    projected = {
        "role": role,
        "sequence": event.get("sequence"),
        "event_id": event.get("event_id"),
        "event_type": event_type,
        "event_hash": sha256_text(canonical_json(event)),
        "artifact_hash": artifact_hash,
        "artifact_bytes": artifact_bytes,
        "check_id": check_id,
    }
    ref_id = sha256_text(canonical_json(projected))
    return {"evidence_ref_id": ref_id, **projected}


def _load_selected_events(
    state_path: Path,
    source_specs: Iterable[dict[str, Any]],
) -> dict[str, dict[int, dict[str, Any]]]:
    result: dict[str, dict[int, dict[str, Any]]] = {}
    uri = f"file:{state_path.as_posix()}?mode=ro"
    try:
        connection = sqlite3.connect(uri, uri=True)
        connection.execute("PRAGMA query_only=ON")
        for source in source_specs:
            sequences = [sequence for _, sequence in source["evidence"]]
            placeholders = ",".join("?" for _ in sequences)
            rows = connection.execute(
                "SELECT event_json FROM events WHERE run_id = ? "
                f"AND sequence IN ({placeholders}) ORDER BY sequence",
                (source["run_id"], *sequences),
            ).fetchall()
            events = [
                _load_json_object(row[0].encode("utf-8"), label="D-099 event") for row in rows
            ]
            _require(
                [event.get("sequence") for event in events] == sequences,
                f"D-099 selected event sequence drifted for {source['run_id']}",
            )
            result[source["run_id"]] = {event["sequence"]: event for event in events}
    except sqlite3.Error as exc:
        raise D099ReviewError("D-099 raw event snapshot is unavailable") from exc
    finally:
        if "connection" in locals():
            connection.close()
    return result


def _copy_public_patch(source: Path, destination: Path) -> None:
    try:
        content = source.read_bytes()
    except OSError as exc:
        raise D099ReviewError("D-099 submitted patch source is unavailable") from exc
    _require_leak_safe_patch(content)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.tmp")
    try:
        temporary.write_bytes(content)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def _build_body(
    *,
    repo_root: Path,
    runtime: Path,
    materialize_patches: bool,
) -> dict[str, Any]:
    report, _ = _load_source_report(repo_root)
    report_body = report["semantic_body"]
    candidates = _validate_report_population(report_body)
    candidate_by_run = {candidate["run_id"]: candidate for candidate in candidates}
    artifact_map = _report_artifact_map(report_body)
    public_bindings = _public_dataset_bindings(repo_root)

    state_path = runtime / "state.sqlite3"
    before = _state_bundle_fingerprint(state_path)
    with tempfile.TemporaryDirectory(prefix="patchloop-d099-") as temporary:
        snapshot = _copy_state_snapshot(state_path, Path(temporary))
        selected_events = _load_selected_events(snapshot, SOURCE_SPECS)
    gc.collect()
    after = _state_bundle_fingerprint(state_path)
    _require(before == after, "D-099 raw state changed during review audit")

    sources: list[dict[str, Any]] = []
    for spec in SOURCE_SPECS:
        run_id = spec["run_id"]
        candidate = candidate_by_run[run_id]
        _require(
            candidate.get("task_id") == spec["task_id"]
            and candidate.get("repetition") == spec["repetition"]
            and candidate.get("failure_record_id") == spec["failure_record_id"],
            f"D-099 source identity drifted for {run_id}",
        )
        patch_record = artifact_map.get(("submitted-patch", run_id))
        failure_record = artifact_map.get(("failure-record", run_id))
        qualification_record = artifact_map.get(("qualification", run_id))
        _require(
            all(
                isinstance(value, dict)
                for value in (patch_record, failure_record, qualification_record)
            ),
            f"D-099 D-098 artifact binding is missing for {run_id}",
        )
        raw_patch_path = runtime / "runs" / run_id / "submitted.patch"
        try:
            raw_patch = raw_patch_path.read_bytes()
        except OSError as exc:
            raise D099ReviewError(f"D-099 submitted patch is unavailable for {run_id}") from exc
        _require(
            len(raw_patch) == patch_record["bytes"]
            and sha256_bytes(raw_patch) == patch_record["sha256"],
            f"D-099 submitted patch drifted for {run_id}",
        )
        _require_leak_safe_patch(raw_patch)
        portable_patch_path = repo_root / PATCH_ARTIFACT_ROOT / f"{run_id}.submitted.patch"
        if materialize_patches:
            _copy_public_patch(raw_patch_path, portable_patch_path)
        portable_patch = _descriptor(portable_patch_path, relative_to=repo_root)
        _require(
            portable_patch["bytes"] == patch_record["bytes"]
            and portable_patch["sha256"] == patch_record["sha256"],
            f"D-099 portable submitted patch drifted for {run_id}",
        )
        refs = [
            _event_ref(
                runtime=runtime,
                event=selected_events[run_id][sequence],
                role=role,
                submitted_patch_sha=patch_record["sha256"],
                submitted_patch_bytes=patch_record["bytes"],
                failure_record_id=spec["failure_record_id"],
            )
            for role, sequence in spec["evidence"]
        ]
        public = public_bindings[spec["task_id"]]
        sources.append(
            {
                "run_id": run_id,
                "failure_record_id": spec["failure_record_id"],
                "task_id": spec["task_id"],
                "repetition": spec["repetition"],
                "public_spec": public["descriptor"],
                "public_spec_hash": public["public_spec_hash"],
                "failure_record_sha256": failure_record["sha256"],
                "qualification_hash": candidate["qualification_hash"],
                "qualification_file_sha256": qualification_record["sha256"],
                "source_evidence_hash": candidate["source_evidence_hash"],
                "submitted_patch": portable_patch,
                "semantic_group_id": spec["semantic_group_id"],
                "assessment": spec["assessment"],
                "causal_confidence": spec["causal_confidence"],
                "evidence_refs": refs,
            }
        )

    source_by_run = {source["run_id"]: source for source in sources}
    groups: list[dict[str, Any]] = []
    for spec in GROUP_SPECS:
        member_pairs = EXPECTED_GROUP_MEMBERS[spec["semantic_group_id"]]
        evidence_ref_ids = [
            ref["evidence_ref_id"]
            for run_id, _ in member_pairs
            for ref in source_by_run[run_id]["evidence_refs"]
        ]
        group = {
            **spec,
            "members": [
                {"run_id": run_id, "failure_record_id": failure_id}
                for run_id, failure_id in member_pairs
            ],
            "evidence_ref_ids": evidence_ref_ids,
            "admission_decision": "not_made",
        }
        group.setdefault("proposed_rule", None)
        group.setdefault("unresolved_reason", None)
        group.setdefault("next_review_actions", [])
        fingerprint_body = {
            key: value for key, value in group.items() if key != "semantic_fingerprint"
        }
        group["semantic_fingerprint"] = sha256_text(canonical_json(fingerprint_body))
        groups.append(group)

    candidate_groups = [group for group in groups if group["disposition"] == "candidate"]
    hold_groups = [group for group in groups if group["disposition"] == "hold"]
    candidate_runs = {member["run_id"] for group in candidate_groups for member in group["members"]}
    hold_runs = {member["run_id"] for group in hold_groups for member in group["members"]}
    candidate_order_projection = [
        {
            key: candidate[key]
            for key in (
                "run_id",
                "task_id",
                "repetition",
                "failure_record_id",
                "qualification_hash",
                "source_evidence_hash",
            )
        }
        for candidate in candidates
    ]
    group_partition_projection = [
        {
            "semantic_group_id": group["semantic_group_id"],
            "members": group["members"],
            "representative_run_id": group["representative_run_id"],
            "relation": group["relation"],
            "disposition": group["disposition"],
        }
        for group in groups
    ]
    body = {
        "milestone": "D-099",
        "evidence_kind": "formal-non-admitting-public-review-dedup",
        "recorded_at": RECORDED_AT,
        "producer": {
            "kind": "maintainer-assisted",
            "method": "d099-public-evidence-review-v1",
            "model_id": None,
            "response_artifact_hash": None,
        },
        "source_seal": {
            "path": SOURCE_REPORT_PATH,
            "bytes": SOURCE_REPORT_BYTES,
            "sha256": SOURCE_REPORT_FILE_SHA,
            "schema_version": SOURCE_REPORT_SCHEMA,
            "report_id": SOURCE_REPORT_ID,
            "semantic_body_hash": SOURCE_REPORT_BODY_SHA,
        },
        "campaign": {
            "experiment_id": EXPERIMENT_ID,
            "execution_hash": EXECUTION_HASH,
            "suite_hash": SUITE_HASH,
            "schedule_hash": SCHEDULE_HASH,
            "dataset_manifest_hash": DATASET_MANIFEST_HASH,
        },
        "evidence_boundary": {
            "policy": "agent-visible-public-evidence-v2",
            "allowed_sources": [
                "public task specification",
                "agent-visible search and read artifacts",
                "agent-submitted task-failure patch",
                "registered visible-check result summary",
                "diff review and submission lifecycle metadata",
                "generic official task-failure outcome",
            ],
            "prohibited_semantic_sources": [
                "private task specification",
                "acceptance assertion name or output",
                "reference solution patch",
                "evaluator evidence payload",
                "provider request or response body",
                "credential value",
            ],
            "opaque_integrity_bindings": [
                "qualification hash",
                "source evidence hash",
                "failure record file hash",
            ],
            "generic_outcome_only": True,
            "private_task_body_interpreted": False,
            "hidden_test_body_interpreted": False,
            "reference_patch_body_interpreted": False,
            "evaluator_payload_body_interpreted": False,
            "provider_request_or_response_body_interpreted": False,
        },
        "sources": sources,
        "groups": groups,
        "population_partition": {
            "source_row_count": 12,
            "review_source_count": 9,
            "semantic_group_count": 5,
            "candidate_group_count": len(candidate_groups),
            "candidate_source_count": len(candidate_runs),
            "hold_group_count": len(hold_groups),
            "hold_source_count": len(hold_runs),
            "excluded_resolved": list(EXPECTED_EXCLUDED_RESOLVED),
            "excluded_budget": list(EXPECTED_EXCLUDED_BUDGET),
            "candidate_order_hash": sha256_text(canonical_json(candidate_order_projection)),
            "group_partition_hash": sha256_text(canonical_json(group_partition_projection)),
        },
        "build_validation": {
            "source_seal_verified": True,
            "dataset_manifest_and_public_specs_verified": True,
            "selected_public_event_refs_verified": sum(
                len(source["evidence_refs"]) for source in sources
            ),
            "portable_submitted_patches_verified": 9,
            "proposal_text_leak_scan_passed": True,
            "submitted_patch_leak_scan_passed": True,
            "original_runtime_state_unchanged": True,
            "raw_source_audit_performed": True,
        },
        "authority": {
            "proposal_only": True,
            "human_admission_status": "pending",
            "group_approval_completed": False,
            "admitted_memory_rule_count": 0,
            "d099_review_history_written": False,
            "memory_admission_unlocked": False,
            "memory_index_build_authorized": False,
            "d099_memory_index_built": False,
            "d099_memory_index_frozen": False,
            "historical_memory_artifacts_modified": False,
            "core_campaign_unlocked": False,
            "analysis_ready": False,
            "automatic_agent_self_review_observed": False,
            "exact_hidden_failure_cause_established": False,
            "agent_architecture_defect_established": False,
            "harness_defect_established": False,
            "provider_calls_made": 0,
            "evaluator_calls_made": 0,
            "added_model_cost_usd": 0,
        },
        "next_gate": (
            "Record append-only human decisions at the semantic-group level, then "
            "implement a group-aware proposal consumer; do not write per-failure "
            "review history or build an index from this proposal."
        ),
    }
    _require_leak_safe_text(body)
    try:
        D099ReviewProposal.model_validate(
            {
                "schema_version": SCHEMA_VERSION,
                "proposal_id": "d099_" + ("0" * 64),
                "semantic_body_hash": "sha256:" + ("0" * 64),
                "semantic_body": body,
            }
        )
    except ValidationError as exc:
        raise D099ReviewError("D-099 generated proposal violates its schema") from exc
    return body


def build_d099_review_proposal(
    *,
    repo_root: str | Path | None = None,
    root: str | Path | None = None,
    materialize_patches: bool = False,
) -> dict[str, Any]:
    """Build the exact proposal from raw public evidence without writing memory state."""

    repository = Path(repo_root) if repo_root is not None else repository_root()
    runtime = Path(root) if root is not None else repository / ".patchloop"
    _require(runtime.is_dir(), "D-099 raw runtime is unavailable")
    body = _build_body(
        repo_root=repository,
        runtime=runtime,
        materialize_patches=materialize_patches,
    )
    body_hash = sha256_text(canonical_json(body))
    proposal = {
        "schema_version": SCHEMA_VERSION,
        "proposal_id": f"d099_{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": body,
    }
    if EXPECTED_SEMANTIC_BODY_HASH is not None:
        _require(body_hash == EXPECTED_SEMANTIC_BODY_HASH, "D-099 semantic body drifted")
    try:
        D099ReviewProposal.model_validate(proposal)
    except ValidationError as exc:
        raise D099ReviewError("D-099 generated proposal validation failed") from exc
    return proposal


def write_d099_review_proposal(
    output: str | Path | None = None,
    *,
    repo_root: str | Path | None = None,
    root: str | Path | None = None,
) -> Path:
    """Materialize portable patch copies and the canonical D-099 proposal."""

    repository = Path(repo_root) if repo_root is not None else repository_root()
    selected = Path(output) if output is not None else repository / DEFAULT_PROPOSAL_PATH
    if not selected.is_absolute():
        selected = repository / selected
    proposal = build_d099_review_proposal(
        repo_root=repository,
        root=root,
        materialize_patches=True,
    )
    content = (json.dumps(proposal, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    if EXPECTED_PROPOSAL_FILE_SHA is not None:
        _require(sha256_bytes(content) == EXPECTED_PROPOSAL_FILE_SHA, "D-099 file hash drifted")
    if EXPECTED_PROPOSAL_BYTES is not None:
        _require(len(content) == EXPECTED_PROPOSAL_BYTES, "D-099 file byte count drifted")
    selected.parent.mkdir(parents=True, exist_ok=True)
    temporary = selected.with_name(f".{selected.name}.tmp")
    try:
        temporary.write_bytes(content)
        temporary.replace(selected)
    finally:
        temporary.unlink(missing_ok=True)
    return selected


def _validate_exact_groups(proposal: D099ReviewProposal) -> None:
    body = proposal.semantic_body
    _require(len(body.sources) == 9, "D-099 source count drifted")
    _require(len(body.groups) == 5, "D-099 semantic group count drifted")
    actual_sources = [
        (source.run_id, source.failure_record_id, source.semantic_group_id)
        for source in body.sources
    ]
    expected_sources = [
        (source["run_id"], source["failure_record_id"], source["semantic_group_id"])
        for source in SOURCE_SPECS
    ]
    _require(actual_sources == expected_sources, "D-099 source order or grouping drifted")
    expected_group_projection = [
        {
            "semantic_group_id": group["semantic_group_id"],
            "members": [
                {"run_id": run_id, "failure_record_id": failure_id}
                for run_id, failure_id in EXPECTED_GROUP_MEMBERS[group["semantic_group_id"]]
            ],
            "representative_run_id": group["representative_run_id"],
            "relation": group["relation"],
            "disposition": group["disposition"],
        }
        for group in GROUP_SPECS
    ]
    actual_group_projection = [
        {
            "semantic_group_id": group.semantic_group_id,
            "members": [member.model_dump(mode="json") for member in group.members],
            "representative_run_id": group.representative_run_id,
            "relation": group.relation,
            "disposition": group.disposition,
        }
        for group in body.groups
    ]
    _require(
        actual_group_projection == expected_group_projection,
        "D-099 semantic group partition drifted",
    )
    all_source_pairs = {(run_id, failure_id) for run_id, failure_id, _ in actual_sources}
    all_group_pairs = {
        (member.run_id, member.failure_record_id)
        for group in body.groups
        for member in group.members
    }
    _require(all_source_pairs == all_group_pairs, "D-099 groups do not exactly cover sources")
    source_ref_ids = {
        ref.evidence_ref_id for source in body.sources for ref in source.evidence_refs
    }
    group_ref_ids = {ref_id for group in body.groups for ref_id in group.evidence_ref_ids}
    _require(source_ref_ids == group_ref_ids, "D-099 groups do not exactly cover evidence")
    for source in body.sources:
        for ref in source.evidence_refs:
            projected = ref.model_dump(mode="json")
            recorded_ref_id = projected.pop("evidence_ref_id")
            _require(
                sha256_text(canonical_json(projected)) == recorded_ref_id,
                "D-099 evidence reference identity drifted",
            )
    for group in body.groups:
        projected = group.model_dump(mode="json")
        recorded_fingerprint = projected.pop("semantic_fingerprint")
        _require(
            sha256_text(canonical_json(projected)) == recorded_fingerprint,
            "D-099 semantic group fingerprint drifted",
        )

    population = body.population_partition
    candidate_order_projection = [
        {
            "run_id": source.run_id,
            "task_id": source.task_id,
            "repetition": source.repetition,
            "failure_record_id": source.failure_record_id,
            "qualification_hash": source.qualification_hash,
            "source_evidence_hash": source.source_evidence_hash,
        }
        for source in body.sources
    ]
    _require(
        sha256_text(canonical_json(candidate_order_projection))
        == population.candidate_order_hash,
        "D-099 candidate order hash drifted",
    )
    _require(
        sha256_text(canonical_json(actual_group_projection))
        == population.group_partition_hash,
        "D-099 group partition hash drifted",
    )


def _validate_portable_bindings(
    proposal: D099ReviewProposal,
    *,
    repository: Path,
) -> None:
    report, _ = _load_source_report(repository)
    report_body = report["semantic_body"]
    candidates = _validate_report_population(report_body)
    candidate_by_run = {candidate["run_id"]: candidate for candidate in candidates}
    artifact_map = _report_artifact_map(report_body)
    public_bindings = _public_dataset_bindings(repository)
    rows = report_body.get("runs")
    _require(isinstance(rows, list) and len(rows) == 12, "D-098 row population drifted")
    rows_by_run = {row.get("run_id"): row for row in rows if isinstance(row, dict)}

    for source in proposal.semantic_body.sources:
        candidate = candidate_by_run.get(source.run_id)
        _require(isinstance(candidate, dict), "D-099 source is not a D-098 candidate")
        _require(
            candidate.get("failure_record_id") == source.failure_record_id
            and candidate.get("task_id") == source.task_id
            and candidate.get("repetition") == source.repetition
            and candidate.get("qualification_hash") == source.qualification_hash
            and candidate.get("source_evidence_hash") == source.source_evidence_hash,
            "D-099 source-to-D-098 binding drifted",
        )
        row = rows_by_run.get(source.run_id)
        _require(isinstance(row, dict), "D-099 source row is unavailable")
        result = row.get("result") or {}
        qualification = row.get("qualification") or {}
        _require(
            row.get("terminal_branch") == "official_evaluator"
            and result.get("outcome_kind") == "task_failure"
            and result.get("official") is True
            and qualification.get("qualified") is True
            and qualification.get("memory_candidate_eligible") is True,
            "D-099 source eligibility drifted",
        )
        public = public_bindings[source.task_id]
        _require(
            source.public_spec.model_dump(mode="json") == public["descriptor"]
            and source.public_spec_hash == public["public_spec_hash"],
            "D-099 public specification binding drifted",
        )
        patch_record = artifact_map.get(("submitted-patch", source.run_id))
        failure_record = artifact_map.get(("failure-record", source.run_id))
        qualification_record = artifact_map.get(("qualification", source.run_id))
        _require(
            isinstance(patch_record, dict)
            and isinstance(failure_record, dict)
            and isinstance(qualification_record, dict),
            "D-099 D-098 artifact record is unavailable",
        )
        _require(
            source.submitted_patch.bytes == patch_record.get("bytes")
            and source.submitted_patch.sha256 == patch_record.get("sha256")
            and source.failure_record_sha256 == failure_record.get("sha256")
            and source.qualification_file_sha256 == qualification_record.get("sha256"),
            "D-099 opaque source artifact binding drifted",
        )
        patch_path = ensure_within(repository, source.submitted_patch.path)
        try:
            patch = patch_path.read_bytes()
        except OSError as exc:
            raise D099ReviewError("D-099 portable submitted patch is unavailable") from exc
        _require(
            len(patch) == source.submitted_patch.bytes
            and sha256_bytes(patch) == source.submitted_patch.sha256,
            "D-099 portable submitted patch hash drifted",
        )
        _require_leak_safe_patch(patch)

    population = proposal.semantic_body.population_partition
    _require(
        [item.model_dump(mode="json") for item in population.excluded_resolved]
        == list(EXPECTED_EXCLUDED_RESOLVED),
        "D-099 resolved exclusion partition drifted",
    )
    _require(
        [item.model_dump(mode="json") for item in population.excluded_budget]
        == list(EXPECTED_EXCLUDED_BUDGET),
        "D-099 budget exclusion partition drifted",
    )
    candidate_groups = [
        group for group in proposal.semantic_body.groups if group.disposition == "candidate"
    ]
    hold_groups = [group for group in proposal.semantic_body.groups if group.disposition == "hold"]
    candidate_sources = sum(len(group.members) for group in candidate_groups)
    hold_sources = sum(len(group.members) for group in hold_groups)
    _require(
        (
            population.candidate_group_count,
            population.candidate_source_count,
            population.hold_group_count,
            population.hold_source_count,
        )
        == (3, 6, 2, 3),
        "D-099 candidate/hold population drifted",
    )
    _require(
        (len(candidate_groups), candidate_sources, len(hold_groups), hold_sources) == (3, 6, 2, 3),
        "D-099 candidate/hold group algebra drifted",
    )


def validate_d099_review_proposal(
    proposal_path: str | Path,
    *,
    repository: str | Path | None = None,
    root: str | Path | None = None,
    require_raw_evidence: bool = False,
) -> dict[str, Any]:
    """Validate D-099 without admitting a rule or touching memory/runtime state."""

    repo_root = Path(repository) if repository is not None else repository_root()
    selected = Path(proposal_path)
    if not selected.is_absolute():
        selected = repo_root / selected
    try:
        content = selected.read_bytes()
        proposal = D099ReviewProposal.model_validate_json(content)
    except (OSError, ValidationError) as exc:
        raise D099ReviewError("D-099 proposal validation failed") from exc
    body_payload = proposal.semantic_body.model_dump(mode="json")
    body_hash = sha256_text(canonical_json(body_payload))
    _require(body_hash == proposal.semantic_body_hash, "D-099 semantic body hash mismatch")
    _require(
        proposal.proposal_id == f"d099_{body_hash.removeprefix('sha256:')}",
        "D-099 proposal identity mismatch",
    )
    if EXPECTED_SEMANTIC_BODY_HASH is not None:
        _require(body_hash == EXPECTED_SEMANTIC_BODY_HASH, "D-099 exact semantic body drifted")
    if EXPECTED_PROPOSAL_FILE_SHA is not None:
        _require(
            sha256_bytes(content) == EXPECTED_PROPOSAL_FILE_SHA, "D-099 exact file hash drifted"
        )
    if EXPECTED_PROPOSAL_BYTES is not None:
        _require(len(content) == EXPECTED_PROPOSAL_BYTES, "D-099 exact file byte count drifted")

    _require_leak_safe_text(body_payload)
    _validate_exact_groups(proposal)
    _validate_portable_bindings(proposal, repository=repo_root)
    raw_status = "not_requested"
    if require_raw_evidence:
        runtime = Path(root) if root is not None else repo_root / ".patchloop"
        _require(runtime.is_dir(), "D-099 raw evidence was required but is unavailable")
        rebuilt = build_d099_review_proposal(
            repo_root=repo_root,
            root=runtime,
            materialize_patches=False,
        )
        _require(
            canonical_json(rebuilt) == canonical_json(proposal.model_dump(mode="json")),
            "D-099 raw evidence does not exactly rebuild the proposal",
        )
        raw_status = "pass"

    return {
        "ok": True,
        "schema_version": proposal.schema_version,
        "proposal_id": proposal.proposal_id,
        "semantic_body_hash": proposal.semantic_body_hash,
        "source_experiment_id": proposal.semantic_body.campaign.experiment_id,
        "review_source_count": len(proposal.semantic_body.sources),
        "semantic_group_count": len(proposal.semantic_body.groups),
        "candidate_group_count": proposal.semantic_body.population_partition.candidate_group_count,
        "candidate_source_count": (
            proposal.semantic_body.population_partition.candidate_source_count
        ),
        "hold_group_count": proposal.semantic_body.population_partition.hold_group_count,
        "hold_source_count": proposal.semantic_body.population_partition.hold_source_count,
        "selected_public_event_refs": (
            proposal.semantic_body.build_validation.selected_public_event_refs_verified
        ),
        "portable_submitted_patches": 9,
        "proposal_leak_scan": "pass",
        "submitted_patch_leak_scan": "pass",
        "raw_evidence_validation": raw_status,
        "human_admission_status": proposal.semantic_body.authority.human_admission_status,
        "admitted_memory_rule_count": 0,
        "d099_review_history_written": False,
        "memory_admission_unlocked": False,
        "d099_memory_index_built": False,
        "d099_memory_index_frozen": False,
        "historical_memory_artifacts_modified": False,
        "core_campaign_unlocked": False,
        "provider_calls_made": 0,
        "evaluator_calls_made": 0,
        "added_model_cost_usd": 0,
    }
