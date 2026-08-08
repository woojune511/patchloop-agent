"""Seal a public-only offline decision about the D-112 score-policy gap.

D-115 does not modify the scorer.  It validates the exact D-114 successor
evidence, reads the nine public D-112 score rows, and proves which policy-only
changes cannot satisfy the public diagnostic controls.  A counterfactual tuple
is retained only to specify what a future independently validated, abstaining
failure-class signal would need to support.  No hypothesis label is promoted
to a runtime input or acceptance ground truth.
"""

from __future__ import annotations

import json
import math
import os
import stat
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from patchloop.errors import ContractError
from patchloop.memory import d114_d112_validator_correction as d114
from patchloop.util import canonical_json, sha256_bytes, sha256_text

MILESTONE = "D-115"
PREFLIGHT_SCHEMA_VERSION = "score-policy-decision-analysis-d115-v1"
CANDIDATE_SCHEMA_VERSION = "score-policy-decision-candidate-d115-v1"
NEXT_ACTION_SCHEMA_VERSION = "public-failure-class-signal-contract-d115-v1"
SOURCE_GATE_SCHEMA_VERSION = "score-policy-decision-source-gate-d115-v1"

PREFLIGHT_RECORDED_AT = "2026-08-07T04:57:38Z"
CANDIDATE_RECORDED_AT = "2026-08-07T04:57:39Z"
GATE_RECORDED_AT = "2026-08-07T04:57:40Z"

DEFAULT_D114_RECEIPT_PATH = Path(
    "reports/memory-development/d114-d112-validator-correction-receipt.json"
)
DEFAULT_D114_GATE_PATH = Path("reports/memory-development/d114-d112-validator-correction-gate.json")
DEFAULT_D112_GATE_PATH = Path(
    "reports/memory-development/d112-retrieval-readiness-completion-gate.json"
)
DEFAULT_PREFLIGHT_PATH = Path(
    "reports/memory-development/d115-score-policy-decision-preflight.json"
)
DEFAULT_CANDIDATE_PATH = Path(
    "reports/memory-development/d115-score-policy-decision-candidate.json"
)
DEFAULT_SOURCE_GATE_PATH = Path(
    "reports/memory-development/d115-score-policy-decision-source-gate.json"
)

D115_IMPLEMENTATION_PATHS = (
    Path("patchloop/memory/d115_score_policy_decision.py"),
    Path("scripts/build_d115_score_policy_decision_candidate.py"),
    Path("tests/test_d115_score_policy_decision.py"),
)

EXPECTED_D114_RECEIPT_ID = (
    "d114approval_20d5025c5d72b156e8470812a0062da2d4d639aa2fa9848ef38da96a71112fd7"
)
EXPECTED_D114_RECEIPT_BODY_SHA = (
    "sha256:20d5025c5d72b156e8470812a0062da2d4d639aa2fa9848ef38da96a71112fd7"
)
EXPECTED_D114_RECEIPT_BYTES = 10_493
EXPECTED_D114_RECEIPT_FILE_SHA = (
    "sha256:1f494579e70d9e8a7f0d28439578afc3b3aa77c7735ac8bc4e81627cab70793b"
)
EXPECTED_D114_GATE_ID = "d114_8f378245c6965d59cd5e589a67cea203e502553e19fa9391b11a667db09271fb"
EXPECTED_D114_GATE_BODY_SHA = (
    "sha256:8f378245c6965d59cd5e589a67cea203e502553e19fa9391b11a667db09271fb"
)
EXPECTED_D114_GATE_BYTES = 15_686
EXPECTED_D114_GATE_FILE_SHA = (
    "sha256:c336004f12f187ab0bfb7946204f877c088703d25e809a8e79e9ec84d374be11"
)
EXPECTED_D112_GATE_ID = "d112_3242bed73c9a322ff1d346eba61cfec2f9eae3b57e4cc7e4d7b0e9a5456367b6"
EXPECTED_D112_GATE_BODY_SHA = (
    "sha256:3242bed73c9a322ff1d346eba61cfec2f9eae3b57e4cc7e4d7b0e9a5456367b6"
)
EXPECTED_D112_GATE_BYTES = 77_591
EXPECTED_D112_GATE_FILE_SHA = (
    "sha256:a7e691ae43c60405cbb10cd27caf3055eabaa96bb7fa6f2a02142d97aa903951"
)

PROBE_IDS = (
    "moto-implement-positive-hypothesis",
    "babel-implement-no-match-control",
    "moto-reproduce-phase-control",
)
HYPOTHESIZED_GROUP_ID = "platform-emulation-matrix-gap"
COMPONENT_KEYS = ("semantic", "failure_class", "phase", "language", "validation")
CURRENT_WEIGHTS = {
    "semantic": 0.35,
    "failure_class": 0.25,
    "phase": 0.15,
    "language": 0.15,
    "validation": 0.10,
}
CURRENT_THRESHOLD = 0.72
CONDITIONAL_WEIGHTS = {
    "semantic": 0.25,
    "failure_class": 0.40,
    "phase": 0.15,
    "language": 0.10,
    "validation": 0.10,
}
CONDITIONAL_THRESHOLD = 0.60
RENORMALIZED_WEIGHTS = {
    "semantic": 7 / 13,
    "failure_class": 0.0,
    "phase": 3 / 13,
    "language": 3 / 13,
    "validation": 0.0,
}

ROOT_KEYS = ("schema_version", "semantic_body_hash", "semantic_body")
PREFLIGHT_ROOT_KEYS = ("schema_version", "preflight_id", "semantic_body_hash", "semantic_body")
CANDIDATE_ROOT_KEYS = ("schema_version", "candidate_id", "semantic_body_hash", "semantic_body")
GATE_ROOT_KEYS = ("schema_version", "gate_id", "semantic_body_hash", "semantic_body")
PREFLIGHT_BODY_KEYS = (
    "milestone",
    "evidence_kind",
    "recorded_at",
    "d114_receipt",
    "d114_gate",
    "d112_gate",
    "input_scope",
    "current_policy",
    "public_score_matrix",
    "structural_findings",
    "policy_diagnostics",
    "decision",
    "evidence_boundary",
    "authority",
)
CANDIDATE_BODY_KEYS = (
    "milestone",
    "evidence_kind",
    "recorded_at",
    "preflight",
    "decision_status",
    "recommended_disposition",
    "conditional_policy_hypothesis",
    "proposed_next_action",
    "proposed_next_action_hash",
    "approval_contract",
    "authority",
)
GATE_BODY_KEYS = (
    "milestone",
    "evidence_kind",
    "recorded_at",
    "preflight",
    "candidate",
    "implementation_files",
    "protected_input_integrity",
    "qualification",
    "evidence_boundary",
    "authority",
    "next_gate",
)


class D115DecisionError(ContractError):
    """Raised when D-115 inputs, algebra, scope, or evidence drift."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise D115DecisionError(message)


def _repo_root(repository: str | Path | None) -> Path:
    selected = Path(repository) if repository is not None else Path(__file__).resolve().parents[2]
    try:
        return selected.resolve()
    except OSError as exc:
        raise D115DecisionError("D-115 repository root cannot be resolved") from exc


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
        raise D115DecisionError(f"D-115 {label} escapes or is missing") from exc
    current = candidate
    while current != repository:
        _require(not _is_linklike(current), f"D-115 {label} cannot use a link or junction")
        current = current.parent
    return selected


def _read_stable(path: Path, *, label: str) -> bytes:
    try:
        before = path.stat()
        content = path.read_bytes()
        after = path.stat()
    except OSError as exc:
        raise D115DecisionError(f"D-115 {label} cannot be read") from exc
    _require(
        (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns),
        f"D-115 {label} changed while being read",
    )
    return content


def _parse_json(content: bytes, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise D115DecisionError(f"D-115 {label} is not valid UTF-8 JSON") from exc
    _require(isinstance(value, dict), f"D-115 {label} root must be an object")
    return value


def _pretty_json(payload: Mapping[str, Any]) -> bytes:
    return (json.dumps(payload, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def _require_exact_keys(value: Any, expected: Sequence[str], *, label: str) -> None:
    _require(isinstance(value, dict), f"D-115 {label} must be an object")
    actual = set(value)
    wanted = set(expected)
    _require(
        actual == wanted,
        f"D-115 {label} key set mismatch: missing={sorted(wanted - actual)}, "
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
    _require(payload.get("semantic_body_hash") == body_hash, f"D-115 {label} body hash mismatch")
    _require(
        payload.get(id_field) == id_prefix + body_hash.removeprefix("sha256:"),
        f"D-115 {label} identifier mismatch",
    )
    return body


def _load_bound_json(
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
        f"D-115 {label} exact file binding mismatch",
    )
    return _parse_json(content, label=label), content


def _file_binding(relative: str | Path, *, repository: Path, label: str) -> dict[str, Any]:
    selected = _resolved(relative, repository=repository, label=label)
    content = _read_stable(selected, label=label)
    return {
        "path": selected.relative_to(repository).as_posix(),
        "file_bytes": len(content),
        "file_sha256": sha256_bytes(content),
    }


def _artifact_binding_from_content(
    relative: str | Path,
    *,
    repository: Path,
    content: bytes,
    payload: Mapping[str, Any],
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


def _protected_input_state(repository: Path) -> dict[str, Any]:
    specs = (
        (DEFAULT_D114_RECEIPT_PATH, EXPECTED_D114_RECEIPT_BYTES, EXPECTED_D114_RECEIPT_FILE_SHA),
        (DEFAULT_D114_GATE_PATH, EXPECTED_D114_GATE_BYTES, EXPECTED_D114_GATE_FILE_SHA),
        (DEFAULT_D112_GATE_PATH, EXPECTED_D112_GATE_BYTES, EXPECTED_D112_GATE_FILE_SHA),
        *(
            (Path(spec["path"]), int(spec["file_bytes"]), str(spec["file_sha256"]))
            for spec in d114.PROTECTED_FILE_SPECS
        ),
        *((path, None, None) for path in d114.D114_IMPLEMENTATION_PATHS),
    )
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for path, expected_bytes, expected_sha in specs:
        key = Path(path).as_posix()
        if key in seen:
            continue
        seen.add(key)
        binding = _file_binding(path, repository=repository, label="protected input")
        if expected_bytes is not None:
            _require(
                binding["file_bytes"] == expected_bytes and binding["file_sha256"] == expected_sha,
                f"D-115 protected input drifted: {key}",
            )
        rows.append(binding)
    return {"files": rows, "fingerprint": sha256_text(canonical_json(rows))}


def _implementation_bindings(repository: Path) -> list[dict[str, Any]]:
    return [
        _file_binding(path, repository=repository, label="D-115 implementation")
        for path in D115_IMPLEMENTATION_PATHS
    ]


def _load_exact_inputs(repository: Path) -> dict[str, Any]:
    d114_validation = d114.validate_d114_correction_evidence(repository=repository)
    _require(
        d114_validation["sealed_historical_validation"]["portable_score_replay_exact"] is True,
        "D-115 exact D-114 sealed replay prerequisite failed",
    )
    receipt, receipt_content = _load_bound_json(
        DEFAULT_D114_RECEIPT_PATH,
        repository=repository,
        expected_bytes=EXPECTED_D114_RECEIPT_BYTES,
        expected_sha=EXPECTED_D114_RECEIPT_FILE_SHA,
        label="D-114 receipt",
    )
    gate, gate_content = _load_bound_json(
        DEFAULT_D114_GATE_PATH,
        repository=repository,
        expected_bytes=EXPECTED_D114_GATE_BYTES,
        expected_sha=EXPECTED_D114_GATE_FILE_SHA,
        label="D-114 gate",
    )
    d112_gate, d112_content = _load_bound_json(
        DEFAULT_D112_GATE_PATH,
        repository=repository,
        expected_bytes=EXPECTED_D112_GATE_BYTES,
        expected_sha=EXPECTED_D112_GATE_FILE_SHA,
        label="D-112 gate",
    )
    _require(
        receipt["receipt_id"] == EXPECTED_D114_RECEIPT_ID
        and receipt["semantic_body_hash"] == EXPECTED_D114_RECEIPT_BODY_SHA,
        "D-115 exact D-114 receipt identity mismatch",
    )
    _require(
        gate["gate_id"] == EXPECTED_D114_GATE_ID
        and gate["semantic_body_hash"] == EXPECTED_D114_GATE_BODY_SHA,
        "D-115 exact D-114 gate identity mismatch",
    )
    _require(
        d112_gate["gate_id"] == EXPECTED_D112_GATE_ID
        and d112_gate["semantic_body_hash"] == EXPECTED_D112_GATE_BODY_SHA,
        "D-115 exact D-112 gate identity mismatch",
    )
    authority = gate["semantic_body"]["authority"]
    _require(
        authority["score_policy_correction_authorized"] is False
        and authority["score_weights_or_threshold_changed"] is False
        and authority["ranking_policy_changed"] is False
        and authority["retrieval_ready"] is False
        and authority["retrieval_experiment_authorized"] is False
        and authority["runtime_memory_injection_count"] == 0
        and authority["agent_runs"] == 0
        and authority["core_campaign_unlocked"] is False,
        "D-115 D-114 closed authority drifted",
    )
    return {
        "d114_validation": d114_validation,
        "d114_receipt": receipt,
        "d114_gate": gate,
        "d112_gate": d112_gate,
        "d114_receipt_binding": _artifact_binding_from_content(
            DEFAULT_D114_RECEIPT_PATH,
            repository=repository,
            content=receipt_content,
            payload=receipt,
            id_field="receipt_id",
        ),
        "d114_gate_binding": _artifact_binding_from_content(
            DEFAULT_D114_GATE_PATH,
            repository=repository,
            content=gate_content,
            payload=gate,
            id_field="gate_id",
        ),
        "d112_gate_binding": _artifact_binding_from_content(
            DEFAULT_D112_GATE_PATH,
            repository=repository,
            content=d112_content,
            payload=d112_gate,
            id_field="gate_id",
        ),
    }


def _validate_policy(weights: Mapping[str, Any], threshold: Any, *, label: str) -> None:
    _require_exact_keys(weights, COMPONENT_KEYS, label=f"{label} weights")
    _require(
        all(type(weights[key]) in (int, float) for key in COMPONENT_KEYS),
        f"D-115 {label} weights must be numeric",
    )
    _require(
        all(
            math.isfinite(float(weights[key])) and float(weights[key]) >= 0
            for key in COMPONENT_KEYS
        ),
        f"D-115 {label} weights must be finite and nonnegative",
    )
    _require(
        math.isclose(
            sum(float(weights[key]) for key in COMPONENT_KEYS),
            1.0,
            rel_tol=0,
            abs_tol=1e-12,
        ),
        f"D-115 {label} weights must sum to one",
    )
    _require(
        type(threshold) in (int, float)
        and math.isfinite(float(threshold))
        and 0 <= float(threshold) <= 1,
        f"D-115 {label} threshold must be within zero and one",
    )


def _public_matrix(d112_gate: Mapping[str, Any]) -> list[dict[str, Any]]:
    scoring = d112_gate["semantic_body"]["diagnostic_scoring"]
    contract = scoring["scoring_contract"]
    _require(contract["score_weights"] == CURRENT_WEIGHTS, "D-115 current weights drifted")
    _require(contract["selective_threshold"] == CURRENT_THRESHOLD, "D-115 threshold drifted")
    _require(scoring["score_row_count"] == 9, "D-115 score row count drifted")
    probes = scoring["probe_results"]
    _require(
        [probe["probe_id"] for probe in probes] == list(PROBE_IDS),
        "D-115 public probe order drifted",
    )
    rows: list[dict[str, Any]] = []
    for probe in probes:
        _require(
            probe["hypothesis_is_acceptance_criterion"] is False,
            "D-115 D-112 hypothesis was promoted to acceptance ground truth",
        )
        for candidate in probe["candidates"]:
            components = candidate["components"]
            _require_exact_keys(components, COMPONENT_KEYS, label="D-112 score components")
            recomputed = sum(CURRENT_WEIGHTS[key] * components[key] for key in COMPONENT_KEYS)
            _require(
                recomputed == candidate["final_score"],
                "D-115 D-112 current score row differs from recorded score",
            )
            rows.append(
                {
                    "probe_id": probe["probe_id"],
                    "task_id": probe["task_id"],
                    "phase": probe["phase"],
                    "hypothesis_kind": probe["hypothesis_kind"],
                    "hypothesized_group_id": probe["hypothesized_group_id"],
                    "hypothesis_is_acceptance_criterion": False,
                    "memory_id": candidate["memory_id"],
                    "semantic_group_id": candidate["semantic_group_id"],
                    "recorded_rank": candidate["rank"],
                    "components": dict(components),
                    "recorded_final_score": candidate["final_score"],
                }
            )
    _require(len(rows) == 9, "D-115 public score matrix shape drifted")
    return rows


def _evaluate_policy(
    rows: Sequence[Mapping[str, Any]],
    *,
    policy_id: str,
    weights: Mapping[str, float],
    threshold: float,
    class_overrides: Mapping[tuple[str, str], float] | None = None,
    runtime_observable: bool,
) -> dict[str, Any]:
    _validate_policy(weights, threshold, label=policy_id)
    override = class_overrides or {}
    probe_results: list[dict[str, Any]] = []
    for probe_id in PROBE_IDS:
        candidates: list[dict[str, Any]] = []
        probe_rows = [row for row in rows if row["probe_id"] == probe_id]
        for row in probe_rows:
            components = dict(row["components"])
            key = (probe_id, str(row["memory_id"]))
            if key in override:
                components["failure_class"] = override[key]
            weighted = {name: weights[name] * components[name] for name in COMPONENT_KEYS}
            final_score = sum(weighted[name] for name in COMPONENT_KEYS)
            candidates.append(
                {
                    "memory_id": row["memory_id"],
                    "semantic_group_id": row["semantic_group_id"],
                    "components": components,
                    "weighted_components": weighted,
                    "final_score": final_score,
                    "threshold_pass": final_score >= threshold,
                }
            )
        candidates.sort(key=lambda row: (-row["final_score"], row["memory_id"]))
        for rank, candidate in enumerate(candidates, start=1):
            candidate["rank"] = rank
        passing = [row["memory_id"] for row in candidates if row["threshold_pass"]]
        probe_results.append(
            {
                "probe_id": probe_id,
                "top_memory_id": candidates[0]["memory_id"],
                "top_group_id": candidates[0]["semantic_group_id"],
                "passing_memory_ids": passing,
                "no_match": not passing,
                "candidates": candidates,
            }
        )
    positive, negative, phase_control = probe_results
    hypothesized = next(
        row for row in positive["candidates"] if row["semantic_group_id"] == HYPOTHESIZED_GROUP_ID
    )
    return {
        "policy_id": policy_id,
        "weights": dict(weights),
        "threshold": threshold,
        "threshold_comparator": "greater-than-or-equal",
        "runtime_observable_inputs_only": runtime_observable,
        "probe_results": probe_results,
        "diagnostic_control_observations": {
            "moto_hypothesized_group_top": (positive["top_group_id"] == HYPOTHESIZED_GROUP_ID),
            "moto_hypothesized_group_passes": hypothesized["threshold_pass"],
            "moto_any_memory_passes": not positive["no_match"],
            "negative_control_no_match": negative["no_match"],
            "phase_control_no_match": phase_control["no_match"],
        },
    }


def _counterfactual_class_overrides(
    rows: Sequence[Mapping[str, Any]],
) -> dict[tuple[str, str], float]:
    overrides: dict[tuple[str, str], float] = {}
    for row in rows:
        value = float(
            row["probe_id"] in {PROBE_IDS[0], PROBE_IDS[2]}
            and row["semantic_group_id"] == HYPOTHESIZED_GROUP_ID
        )
        overrides[(str(row["probe_id"]), str(row["memory_id"]))] = value
    return overrides


def _policy_diagnostics(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    current = _evaluate_policy(
        rows,
        policy_id="current-policy-v1",
        weights=CURRENT_WEIGHTS,
        threshold=CURRENT_THRESHOLD,
        runtime_observable=True,
    )
    positive_rows = [row for row in rows if row["probe_id"] == PROBE_IDS[0]]
    hypothesized_row = next(
        row for row in positive_rows if row["semantic_group_id"] == HYPOTHESIZED_GROUP_ID
    )
    threshold_only = _evaluate_policy(
        rows,
        policy_id="threshold-only-at-moto-hypothesized-score",
        weights=CURRENT_WEIGHTS,
        threshold=float(hypothesized_row["recorded_final_score"]),
        runtime_observable=True,
    )
    renormalized = _evaluate_policy(
        rows,
        policy_id="active-component-renormalization-v1",
        weights=RENORMALIZED_WEIGHTS,
        threshold=CURRENT_THRESHOLD,
        runtime_observable=True,
    )
    overrides = _counterfactual_class_overrides(rows)
    class_only = _evaluate_policy(
        rows,
        policy_id="counterfactual-class-signal-current-weights",
        weights=CURRENT_WEIGHTS,
        threshold=CURRENT_THRESHOLD,
        class_overrides=overrides,
        runtime_observable=False,
    )
    conditional = _evaluate_policy(
        rows,
        policy_id="counterfactual-class-signal-conditional-tuple",
        weights=CONDITIONAL_WEIGHTS,
        threshold=CONDITIONAL_THRESHOLD,
        class_overrides=overrides,
        runtime_observable=False,
    )
    diagnostics = [current, threshold_only, renormalized, class_only, conditional]
    dispositions = {
        "current-policy-v1": "rejected-degenerate-moto-no-match",
        "threshold-only-at-moto-hypothesized-score": (
            "rejected-nonhypothesized-rank-and-negative-control-selection"
        ),
        "active-component-renormalization-v1": ("rejected-moto-no-match-and-rank-unchanged"),
        "counterfactual-class-signal-current-weights": (
            "rejected-counterfactual-and-moto-no-match"
        ),
        "counterfactual-class-signal-conditional-tuple": (
            "conditional-hypothesis-only-independent-signal-required"
        ),
    }
    for diagnostic in diagnostics:
        diagnostic["disposition"] = dispositions[diagnostic["policy_id"]]
    return diagnostics


def _structural_findings(
    rows: Sequence[Mapping[str, Any]], diagnostics: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    current = next(row for row in diagnostics if row["policy_id"] == "current-policy-v1")
    positive = current["probe_results"][0]
    negative = current["probe_results"][1]
    hypothesized = next(
        row for row in positive["candidates"] if row["semantic_group_id"] == HYPOTHESIZED_GROUP_ID
    )
    positive_top = positive["candidates"][0]
    negative_top = negative["candidates"][0]
    negative_lowest = negative["candidates"][-1]
    _require(
        all(row["components"]["failure_class"] == 0 for row in rows),
        "D-115 observed failure-class component is not uniformly zero",
    )
    _require(
        all(row["components"]["validation"] == 0 for row in rows),
        "D-115 observed validation component is not uniformly zero",
    )
    for probe_id in PROBE_IDS:
        probe_rows = [row for row in rows if row["probe_id"] == probe_id]
        _require(
            len({row["components"]["phase"] for row in probe_rows}) == 1
            and len({row["components"]["language"] for row in probe_rows}) == 1,
            f"D-115 nonsemantic component equality drifted: {probe_id}",
        )
    _require(hypothesized["rank"] == 3, "D-115 Moto hypothesized group rank drifted")
    _require(
        positive_top["final_score"] < negative_top["final_score"],
        "D-115 threshold-only separation premise drifted",
    )
    _require(
        hypothesized["final_score"] < negative_lowest["final_score"],
        "D-115 hypothesized-vs-negative dominance premise drifted",
    )
    return {
        "current_failure_class_component_all_zero": True,
        "current_validation_component_all_zero": True,
        "phase_and_language_equal_within_each_probe": True,
        "current_implement_python_theoretical_max_without_class_or_validation": 0.65,
        "current_threshold": CURRENT_THRESHOLD,
        "theoretical_max_below_threshold": CURRENT_THRESHOLD > 0.65,
        "moto_hypothesized_group_rank": hypothesized["rank"],
        "moto_hypothesized_group_score": hypothesized["final_score"],
        "moto_observed_top_nonhypothesized_group_score": positive_top["final_score"],
        "babel_top_score": negative_top["final_score"],
        "babel_lowest_score": negative_lowest["final_score"],
        "threshold_to_select_any_moto_must_be_at_most": positive_top["final_score"],
        "threshold_to_keep_babel_no_match_must_be_greater_than": negative_top["final_score"],
        "threshold_only_separation_interval_exists": False,
        "threshold_to_select_hypothesized_moto_selects_all_babel_entries": True,
        "nonnegative_current_feature_weights_can_make_hypothesized_group_top": False,
        "rank_reason": (
            "class-and-validation-zero-phase-and-language-equal-rank-is-semantic-only; "
            "zero-semantic-weight-still-does-not-put-hypothesized-memory-first-by-id"
        ),
        "hypothesis_labels_are_runtime_inputs": False,
        "hypothesis_labels_are_acceptance_ground_truth": False,
    }


def _conditional_policy_hypothesis(
    diagnostics: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    conditional = next(
        row
        for row in diagnostics
        if row["policy_id"] == "counterfactual-class-signal-conditional-tuple"
    )
    positive, negative, phase_control = conditional["probe_results"]
    positive_hypothesized = next(
        row for row in positive["candidates"] if row["semantic_group_id"] == HYPOTHESIZED_GROUP_ID
    )
    phase_hypothesized = next(
        row
        for row in phase_control["candidates"]
        if row["semantic_group_id"] == HYPOTHESIZED_GROUP_ID
    )
    return {
        "policy_id": conditional["policy_id"],
        "weights": dict(CONDITIONAL_WEIGHTS),
        "threshold": CONDITIONAL_THRESHOLD,
        "comparator": "greater-than-or-equal",
        "counterfactual_only": True,
        "corrected_policy_selected": False,
        "implementation_ready": False,
        "counterfactual_signal_assumptions": {
            "source": "d112-public-non-acceptance-hypothesis",
            "moto_implement_hypothesized_group_signal": 1.0,
            "moto_reproduce_signal_copied_from_implement_for_phase_control": True,
            "babel_all_groups_abstain": True,
            "runtime_classifier_observed": False,
            "true_relevance_established": False,
        },
        "required_signal": (
            "independent-deterministic-public-taxonomy-classifier-with-explicit-abstention"
        ),
        "forbidden_signal_sources": [
            "d112-hypothesized-group-id",
            "task-id-to-answer-lookup",
            "private-task-spec",
            "hidden-test",
            "reference-or-known-bad-patch",
            "held-out-result",
        ],
        "diagnostic_only_counterfactual_results": {
            "moto_implement_hypothesized_score": positive_hypothesized["final_score"],
            "moto_implement_hypothesized_pass": positive_hypothesized["threshold_pass"],
            "babel_top_score": negative["candidates"][0]["final_score"],
            "babel_no_match": negative["no_match"],
            "moto_reproduce_hypothesized_score": phase_hypothesized["final_score"],
            "moto_reproduce_no_match": phase_control["no_match"],
            "phase_delta": (
                positive_hypothesized["final_score"] - phase_hypothesized["final_score"]
            ),
        },
    }


def build_d115_preflight(*, repository: str | Path | None = None) -> dict[str, Any]:
    repo = _repo_root(repository)
    context = _load_exact_inputs(repo)
    rows = _public_matrix(context["d112_gate"])
    diagnostics = _policy_diagnostics(rows)
    findings = _structural_findings(rows, diagnostics)
    conditional = _conditional_policy_hypothesis(diagnostics)
    body = {
        "milestone": MILESTONE,
        "evidence_kind": "public-only-offline-score-policy-decision-analysis",
        "recorded_at": PREFLIGHT_RECORDED_AT,
        "d114_receipt": context["d114_receipt_binding"],
        "d114_gate": context["d114_gate_binding"],
        "d112_gate": context["d112_gate_binding"],
        "input_scope": {
            "public_probe_ids_in_order": list(PROBE_IDS),
            "score_row_count": 9,
            "observed_matrix_uses_stored_d112_components_only": True,
            "public_non_acceptance_hypothesis_used_for_counterfactual": True,
            "counterfactual_is_runtime_observable": False,
            "counterfactual_is_acceptance_evidence": False,
            "d114_sealed_historical_validation_required": True,
            "current_input_snapshot_rehydrated": False,
            "private_hidden_reference_or_known_bad_read": False,
            "raw_trace_or_patch_read": False,
            "held_out_result_read": False,
        },
        "current_policy": {
            "weights": dict(CURRENT_WEIGHTS),
            "threshold": CURRENT_THRESHOLD,
            "comparator": "greater-than-or-equal",
            "rank_order": "descending-score-then-ascending-memory-id",
        },
        "public_score_matrix": rows,
        "structural_findings": findings,
        "policy_diagnostics": diagnostics,
        "decision": {
            "recommended_disposition": (
                "defer-policy-mutation-and-author-public-only-relevance-calibration"
            ),
            "corrected_policy_selected": False,
            "score_policy_implementation_ready": False,
            "additional_public_relevance_evidence_required": True,
            "threshold_only_rejected": True,
            "current_feature_weight_only_rejected": True,
            "counterfactual_conditional_tuple": conditional,
            "next_required_contract": (
                "independent-abstaining-public-failure-class-signal-and-calibration"
            ),
        },
        "evidence_boundary": {
            "hypothesis_promoted_to_ground_truth": False,
            "hypothesis_used_to_construct_labeled_counterfactual": True,
            "diagnostic_controls_establish_true_relevance": False,
            "score_policy_or_threshold_changed": False,
            "failure_class_signal_changed": False,
            "memory_entry_index_or_marker_changed": False,
            "model_load_or_encode_count": 0,
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
        "authority": {
            "offline_score_policy_decision_candidate_ready": False,
            "corrected_policy_selected": False,
            "exact_candidate_user_approval_received": False,
            "score_policy_correction_authorized": False,
            "score_policy_correction_implemented": False,
            "retrieval_ready": False,
            "retrieval_experiment_authorized": False,
            "runtime_memory_injection_count": 0,
            "core_campaign_unlocked": False,
            "analysis_ready": False,
        },
    }
    body_hash = sha256_text(canonical_json(body))
    return {
        "schema_version": PREFLIGHT_SCHEMA_VERSION,
        "preflight_id": f"d115preflight_{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": body,
    }


def _output_binding(
    path: str | Path,
    *,
    repository: Path,
    payload: Mapping[str, Any],
    id_field: str,
) -> dict[str, Any]:
    content = _pretty_json(payload)
    selected = _resolved(path, repository=repository, label="D-115 output", must_exist=False)
    return {
        "path": selected.relative_to(repository).as_posix(),
        "file_bytes": len(content),
        "file_sha256": sha256_bytes(content),
        "schema_version": payload["schema_version"],
        id_field: payload[id_field],
        "semantic_body_hash": payload["semantic_body_hash"],
    }


def build_d115_candidate(
    preflight: Mapping[str, Any], *, repository: str | Path | None = None
) -> dict[str, Any]:
    repo = _repo_root(repository)
    _validate_envelope(
        preflight,
        root_keys=PREFLIGHT_ROOT_KEYS,
        body_keys=PREFLIGHT_BODY_KEYS,
        id_field="preflight_id",
        id_prefix="d115preflight_",
        label="D-115 preflight",
    )
    preflight_body = preflight["semantic_body"]
    _require(
        preflight_body["decision"]["corrected_policy_selected"] is False,
        "D-115 preflight unexpectedly selected a corrected policy",
    )
    conditional = preflight_body["decision"]["counterfactual_conditional_tuple"]
    proposed_next_action = {
        "schema_version": NEXT_ACTION_SCHEMA_VERSION,
        "action_kind": "prepare-public-failure-class-signal-contract-and-calibration-candidate",
        "future_milestone": "D-116",
        "public_development_inputs_only": True,
        "allowed_splits": ["dev-train", "dev-validation"],
        "held_out_access_allowed": False,
        "private_hidden_reference_or_known_bad_access_allowed": False,
        "hypothesized_group_id_as_classifier_input_allowed": False,
        "task_id_answer_lookup_allowed": False,
        "deterministic_abstention_required": True,
        "ambiguous_signal_must_abstain": True,
        "additional_public_negative_controls_required": True,
        "conditional_policy_tuple_may_be_evaluated_offline": True,
        "conditional_policy_tuple": conditional,
        "score_policy_mutation_allowed": False,
        "runtime_retrieval_allowed": False,
        "runtime_memory_injection_allowed": False,
        "agent_run_allowed": False,
        "provider_or_evaluator_call_allowed": False,
        "network_access_allowed": False,
        "core_campaign_allowed": False,
        "analysis_campaign_allowed": False,
    }
    body = {
        "milestone": MILESTONE,
        "evidence_kind": "offline-score-policy-decision-authorization-candidate",
        "recorded_at": CANDIDATE_RECORDED_AT,
        "preflight": _output_binding(
            DEFAULT_PREFLIGHT_PATH,
            repository=repo,
            payload=preflight,
            id_field="preflight_id",
        ),
        "decision_status": "policy-mutation-deferred",
        "recommended_disposition": (
            "defer-policy-mutation-and-author-public-only-relevance-calibration"
        ),
        "conditional_policy_hypothesis": conditional,
        "proposed_next_action": proposed_next_action,
        "proposed_next_action_hash": sha256_text(canonical_json(proposed_next_action)),
        "approval_contract": {
            "separate_user_message_required": True,
            "exact_candidate_id_required": True,
            "exact_semantic_body_hash_required": True,
            "exact_file_sha256_required": True,
            "generic_continue_message_is_approval": False,
            "approval_would_authorize_score_policy_mutation": False,
            "approval_would_authorize_retrieval_or_agent_run": False,
        },
        "authority": {
            "offline_score_policy_decision_candidate_ready": True,
            "corrected_policy_selected": False,
            "additional_public_relevance_evidence_required": True,
            "exact_candidate_user_approval_received": False,
            "public_failure_class_signal_contract_authorized": False,
            "score_policy_correction_authorized": False,
            "score_policy_correction_implemented": False,
            "score_weights_or_threshold_changed": False,
            "failure_class_signal_changed": False,
            "ranking_policy_changed": False,
            "retrieval_ready": False,
            "retrieval_experiment_authorized": False,
            "runtime_memory_injection_count": 0,
            "agent_runs": 0,
            "core_campaign_unlocked": False,
            "analysis_ready": False,
            "memory_effect_established": False,
            "negative_transfer_established": False,
        },
    }
    body_hash = sha256_text(canonical_json(body))
    return {
        "schema_version": CANDIDATE_SCHEMA_VERSION,
        "candidate_id": f"d115scoredecisioncandidate_{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": body,
    }


def build_d115_source_gate(
    preflight: Mapping[str, Any],
    candidate: Mapping[str, Any],
    *,
    repository: str | Path | None = None,
    protected_pre: Mapping[str, Any],
    protected_post: Mapping[str, Any],
) -> dict[str, Any]:
    repo = _repo_root(repository)
    _require(protected_pre == protected_post, "D-115 protected inputs changed during build")
    _require(
        candidate["semantic_body"]["authority"]["score_policy_correction_authorized"] is False,
        "D-115 candidate unexpectedly authorized policy correction",
    )
    body = {
        "milestone": MILESTONE,
        "evidence_kind": "offline-score-policy-decision-source-gate",
        "recorded_at": GATE_RECORDED_AT,
        "preflight": _output_binding(
            DEFAULT_PREFLIGHT_PATH,
            repository=repo,
            payload=preflight,
            id_field="preflight_id",
        ),
        "candidate": _output_binding(
            DEFAULT_CANDIDATE_PATH,
            repository=repo,
            payload=candidate,
            id_field="candidate_id",
        ),
        "implementation_files": _implementation_bindings(repo),
        "protected_input_integrity": {
            "pre_build": dict(protected_pre),
            "post_build": dict(protected_post),
            "fingerprints_equal": True,
        },
        "qualification": {
            "exact_d114_successor_evidence_validated": True,
            "exact_nine_d112_score_rows_recomputed": True,
            "public_probe_hypotheses_not_promoted_to_ground_truth": True,
            "threshold_only_impossibility_proved": True,
            "nonnegative_current_feature_weight_only_rank_correction_impossible": True,
            "counterfactual_tuple_labeled_non_runtime_and_non_authoritative": True,
            "corrected_policy_selected": False,
            "additional_public_relevance_evidence_required": True,
            "protected_inputs_unchanged": True,
        },
        "evidence_boundary": {
            "private_hidden_reference_or_known_bad_read": False,
            "raw_trace_or_patch_read": False,
            "held_out_result_read": False,
            "snapshot_rehydration_performed": False,
            "model_load_or_encode_count": 0,
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
        "authority": dict(candidate["semantic_body"]["authority"]),
        "next_gate": "exact-d115-candidate-triple-public-class-signal-contract-approval",
    }
    body_hash = sha256_text(canonical_json(body))
    return {
        "schema_version": SOURCE_GATE_SCHEMA_VERSION,
        "gate_id": f"d115_{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": body,
    }


def _write_exact(path: Path, content: bytes, *, repository: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _require(not _is_linklike(path.parent), "D-115 output parent cannot be a link or junction")
    if path.exists():
        _require(
            _read_stable(path, label="existing D-115 output") == content,
            "D-115 existing output differs from deterministic rebuild",
        )
        return
    try:
        with path.open("xb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as exc:
        raise D115DecisionError("D-115 output write failed") from exc
    _require(
        _read_stable(path, label="committed D-115 output") == content,
        "D-115 committed output read-back mismatch",
    )


def validate_d115_preflight(
    path: str | Path = DEFAULT_PREFLIGHT_PATH,
    *,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    repo = _repo_root(repository)
    selected = _resolved(path, repository=repo, label="D-115 preflight")
    content = _read_stable(selected, label="D-115 preflight")
    parsed = _parse_json(content, label="D-115 preflight")
    _validate_envelope(
        parsed,
        root_keys=PREFLIGHT_ROOT_KEYS,
        body_keys=PREFLIGHT_BODY_KEYS,
        id_field="preflight_id",
        id_prefix="d115preflight_",
        label="D-115 preflight",
    )
    expected = build_d115_preflight(repository=repo)
    _require(parsed == expected, "D-115 preflight full expected payload mismatch")
    _require(content == _pretty_json(expected), "D-115 preflight exact bytes drifted")
    return parsed


def validate_d115_candidate(
    path: str | Path = DEFAULT_CANDIDATE_PATH,
    *,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    repo = _repo_root(repository)
    selected = _resolved(path, repository=repo, label="D-115 candidate")
    content = _read_stable(selected, label="D-115 candidate")
    parsed = _parse_json(content, label="D-115 candidate")
    body = _validate_envelope(
        parsed,
        root_keys=CANDIDATE_ROOT_KEYS,
        body_keys=CANDIDATE_BODY_KEYS,
        id_field="candidate_id",
        id_prefix="d115scoredecisioncandidate_",
        label="D-115 candidate",
    )
    _require_exact_keys(
        body["authority"],
        (
            "offline_score_policy_decision_candidate_ready",
            "corrected_policy_selected",
            "additional_public_relevance_evidence_required",
            "exact_candidate_user_approval_received",
            "public_failure_class_signal_contract_authorized",
            "score_policy_correction_authorized",
            "score_policy_correction_implemented",
            "score_weights_or_threshold_changed",
            "failure_class_signal_changed",
            "ranking_policy_changed",
            "retrieval_ready",
            "retrieval_experiment_authorized",
            "runtime_memory_injection_count",
            "agent_runs",
            "core_campaign_unlocked",
            "analysis_ready",
            "memory_effect_established",
            "negative_transfer_established",
        ),
        label="D-115 candidate authority",
    )
    preflight = validate_d115_preflight(repository=repo)
    expected = build_d115_candidate(preflight, repository=repo)
    _require(parsed == expected, "D-115 candidate full expected payload mismatch")
    _require(content == _pretty_json(expected), "D-115 candidate exact bytes drifted")
    return parsed


def validate_d115_source_gate(
    path: str | Path = DEFAULT_SOURCE_GATE_PATH,
    *,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    repo = _repo_root(repository)
    selected = _resolved(path, repository=repo, label="D-115 source gate")
    content = _read_stable(selected, label="D-115 source gate")
    parsed = _parse_json(content, label="D-115 source gate")
    body = _validate_envelope(
        parsed,
        root_keys=GATE_ROOT_KEYS,
        body_keys=GATE_BODY_KEYS,
        id_field="gate_id",
        id_prefix="d115_",
        label="D-115 source gate",
    )
    _require(
        body["authority"]["score_policy_correction_authorized"] is False
        and body["authority"]["retrieval_ready"] is False
        and body["authority"]["runtime_memory_injection_count"] == 0
        and body["authority"]["core_campaign_unlocked"] is False,
        "D-115 source gate authority expanded",
    )
    preflight = validate_d115_preflight(repository=repo)
    candidate = validate_d115_candidate(repository=repo)
    current = _protected_input_state(repo)
    expected = build_d115_source_gate(
        preflight,
        candidate,
        repository=repo,
        protected_pre=current,
        protected_post=current,
    )
    _require(parsed == expected, "D-115 source gate full expected payload mismatch")
    _require(content == _pretty_json(expected), "D-115 source gate exact bytes drifted")
    return parsed


def run_d115_offline_source_gate(*, repository: str | Path | None = None) -> dict[str, Any]:
    repo = _repo_root(repository)
    protected_pre = _protected_input_state(repo)
    preflight = build_d115_preflight(repository=repo)
    candidate = build_d115_candidate(preflight, repository=repo)
    preflight_path = _resolved(
        DEFAULT_PREFLIGHT_PATH, repository=repo, label="D-115 preflight", must_exist=False
    )
    candidate_path = _resolved(
        DEFAULT_CANDIDATE_PATH, repository=repo, label="D-115 candidate", must_exist=False
    )
    _write_exact(preflight_path, _pretty_json(preflight), repository=repo)
    _write_exact(candidate_path, _pretty_json(candidate), repository=repo)
    validate_d115_preflight(repository=repo)
    validate_d115_candidate(repository=repo)
    protected_post = _protected_input_state(repo)
    gate = build_d115_source_gate(
        preflight,
        candidate,
        repository=repo,
        protected_pre=protected_pre,
        protected_post=protected_post,
    )
    gate_path = _resolved(
        DEFAULT_SOURCE_GATE_PATH, repository=repo, label="D-115 source gate", must_exist=False
    )
    _write_exact(gate_path, _pretty_json(gate), repository=repo)
    validate_d115_source_gate(repository=repo)
    candidate_content = _pretty_json(candidate)
    gate_content = _pretty_json(gate)
    return {
        "preflight_id": preflight["preflight_id"],
        "candidate_id": candidate["candidate_id"],
        "candidate_semantic_body_hash": candidate["semantic_body_hash"],
        "candidate_file_bytes": len(candidate_content),
        "candidate_file_sha256": sha256_bytes(candidate_content),
        "gate_id": gate["gate_id"],
        "gate_semantic_body_hash": gate["semantic_body_hash"],
        "gate_file_bytes": len(gate_content),
        "gate_file_sha256": sha256_bytes(gate_content),
        "recommended_disposition": candidate["semantic_body"]["recommended_disposition"],
        "corrected_policy_selected": False,
        "score_policy_correction_authorized": False,
        "retrieval_ready": False,
        "runtime_memory_injection_count": 0,
        "agent_runs": 0,
        "core_campaign_unlocked": False,
    }
