"""Development-evidence-only budget amendment for the held-out A/C successor.

The amendment narrows equal A/C token ceilings and their derived full-schedule
cost envelope.  It reads only the immutable base-suite bytes and seven named
development evidence files.  It never opens held-out task packages or runtime
outcomes and grants no candidate, approval, reservation, or execution authority.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import ValidationError

from patchloop.errors import ContractError
from patchloop.evals.heldout_ac_contracts import HeldoutACFrozenModel
from patchloop.runtime import repository_root
from patchloop.util import canonical_json, load_unique_yaml, sha256_bytes, sha256_text

AMENDMENT_PATH = Path("experiments/heldout-ac-budget-amendment-20260815-v1.yaml")
AMENDMENT_ID = "core-ac-fixed-bundle-heldout-budget-20260815-v1"
AMENDMENT_CONTENT_HASH = "sha256:9df732d5bf8d5c754ea47084e5dbf9c490f78882bcc9fbc6b0c5d2e2b8bf220d"
AMENDMENT_FILE_BYTES = 7_248
AMENDMENT_FILE_SHA256 = "sha256:a2532b466c55659c72e6602a37a6a6114ad42d90c5fd78502ad976f9384f9e53"

MAX_CUMULATIVE_INPUT_TOKENS = 1_000_000
MAX_CUMULATIVE_OUTPUT_TOKENS = 100_000
MAX_TOTAL_TOKENS = 1_100_000
PER_RUN_RESERVE_NANOS = 1_200_000_000
FULL_SCHEDULE_RESERVE_NANOS = 57_600_000_000
HARD_CAP_NANOS = 60_000_000_000
HARD_CAP_SLACK_NANOS = 2_400_000_000

_BASE_SUITE = {
    "path": "experiments/heldout-ac-suite-20260814-v1.yaml",
    "suite_id": "core-ac-fixed-bundle-heldout-20260814-v1",
    "content_hash": "sha256:1d023e8837e99889d76acf6f3a2d970261cb7aa4b3e978c84cef2ef5cf517aaa",
    "file_bytes": 13_348,
    "file_sha256": "sha256:27157e26881cc277a9026e51d22a6f21fbf5bbb8f6c1c09eaa89aec607e52534",
}

_EVIDENCE_FILES = (
    {
        "path": (
            "reports/live-pilot/dev-validation-ac-fixed-bundle-readiness-20260813-r3-evidence.json"
        ),
        "file_bytes": 8_242,
        "file_sha256": "sha256:4c22a16c7fa9f3c7cbc58cac56a8aead3b060ee4c1a8613a822f8a0df3c2d240",
        "role": "like-for-like-development-runtime",
    },
    {
        "path": (
            "reports/live-pilot/dev-validation-ac-fixed-bundle-readiness-20260814-r5-evidence.json"
        ),
        "file_bytes": 6_605,
        "file_sha256": "sha256:fa49986ed7693c65024a167fda6042fbbdb5cce3c38494d412018d1ee545832c",
        "role": "like-for-like-development-runtime",
    },
    {
        "path": (
            "reports/live-pilot/dev-validation-ac-fixed-bundle-readiness-20260814-r6-evidence.json"
        ),
        "file_bytes": 7_218,
        "file_sha256": "sha256:b84a27830f5bbc3d3f18235c542de5def0594d57ba00d5babc9daa865c1d59d7",
        "role": "like-for-like-development-runtime",
    },
    {
        "path": (
            "reports/live-pilot/"
            "dev-validation-ac-fixed-bundle-readiness-20260814-r8-evidence-r4.json"
        ),
        "file_bytes": 19_557,
        "file_sha256": "sha256:5035421a63d58fededab133b77c72e23ee4ad6d380a37c8d1157ce7480b7c62c",
        "role": "like-for-like-development-runtime",
    },
    {
        "path": "reports/live-pilot/dev-no-memory-saturation-v8-pilot-20260801-r1.json",
        "file_bytes": 7_183,
        "file_sha256": "sha256:33e67095c8a3d5c8c056ded6f144c5165676aa177e260348e623923b5fbaae78",
        "role": "secondary-development-stress",
    },
    {
        "path": "reports/live-pilot/dev-no-memory-review-evidence-v9-pilot-20260801-r1.json",
        "file_bytes": 7_661,
        "file_sha256": "sha256:1cbb4e33ab33b50eb21be10a4999af608a2524de35fec9a252270bee726b554b",
        "role": "secondary-development-stress",
    },
    {
        "path": "reports/live-pilot/dev-no-memory-coverage-review-v10-pilot-20260802-r1.json",
        "file_bytes": 9_634,
        "file_sha256": "sha256:9cf3009542674f260e4128b4c10736b50a5b9d685d7155b63a007aa16f2692ff",
        "role": "secondary-development-stress",
    },
)

_EXPECTED_CHANGE_CONTROL = {
    "reason": "user-cost-exposure-reduction-before-successor-approval",
    "threshold_selection_source": "development-evidence-only",
    "heldout_task_specs_opened_for_threshold_selection": False,
    "heldout_outcomes_used_for_threshold_selection": False,
    "r11_outcomes_used_for_threshold_selection": False,
    "task_panel_changed": False,
    "schedule_changed": False,
    "treatment_changed": False,
    "prompt_model_tool_or_evaluator_changed": False,
    "repetitions_changed": False,
    "only_changed_dimensions": [
        "token-budget-ceilings",
        "derived-cost-reserve-and-hard-cap",
    ],
}

_EXPECTED_RUNTIME_OVERRIDE = {
    "token_budget_schema_version": "cumulative-split-v1",
    "max_cumulative_input_tokens": MAX_CUMULATIVE_INPUT_TOKENS,
    "max_cumulative_output_tokens": MAX_CUMULATIVE_OUTPUT_TOKENS,
    "max_total_tokens": MAX_TOTAL_TOKENS,
    "max_output_tokens_per_response": 25_000,
    "max_model_calls": 240,
    "max_tool_calls": 400,
    "wall_clock_timeout_seconds": 3_600,
    "applies_identically_to_conditions": ["no_memory", "structured"],
    "budget_exhaustion_is_task_failure": True,
    "automatic_retry_replacement_or_resume": False,
}

_EXPECTED_COST_OVERRIDE = {
    "schema_version": "heldout-ac-cost-bounded-full-schedule-reserve-v1",
    "input_reserve_rate_per_million_usd": 0.75,
    "output_reserve_rate_per_million_usd": 4.5,
    "cache_discount_assumed": False,
    "scheduled_run_count": 48,
    "per_run_reserve_usd": 1.2,
    "full_schedule_reserve_usd": 57.6,
    "hard_cap_usd": 60.0,
    "hard_cap_slack_usd": 2.4,
    "per_run_reserve_nanos": PER_RUN_RESERVE_NANOS,
    "full_schedule_reserve_nanos": FULL_SCHEDULE_RESERVE_NANOS,
    "hard_cap_nanos": HARD_CAP_NANOS,
    "hard_cap_slack_nanos": HARD_CAP_SLACK_NANOS,
    "reservation_mode": "row-bound-full-schedule-up-front",
    "cost_censoring_allowed": False,
    "not_started_due_to_cost_allowed": False,
}

_EXPECTED_INTERPRETATION = {
    "threshold_is_invoice_prediction": False,
    "threshold_guarantees_completion": False,
    "development_observations_are_independent_samples": False,
    "future_result_is_directly_poolable_with_r11": False,
    "complete_48_row_matrix_still_required_for_primary_analysis": True,
    "partial_matrix_is_diagnostic_only": True,
}

_EXPECTED_AUTHORITY = {
    "heldout_task_or_outcome_access_authorized": False,
    "docker_sdk_credential_or_network_observation_authorized": False,
    "provider_evaluator_or_agent_execution_authorized": False,
    "candidate_creation_authorized": False,
    "approval_reservation_or_spend_authorized": False,
    "official_analysis_or_claim_authorized": False,
    "provider_calls_made": 0,
    "evaluator_calls_made": 0,
    "agent_runs_made": 0,
    "docker_calls_made": 0,
    "sdk_calls_made": 0,
    "added_model_cost_usd": 0.0,
}


class HeldoutACBudgetAmendmentError(ContractError):
    """Raised when the development-only budget amendment drifts."""


class HeldoutACBudgetAmendment(HeldoutACFrozenModel):
    schema_version: Literal["heldout-ac-budget-amendment-v1"]
    amendment_id: Literal[AMENDMENT_ID]
    status: Literal["execution-closed"]
    created_date: Literal["2026-08-15"]
    base_suite: dict[str, Any]
    change_control: dict[str, Any]
    development_evidence: dict[str, Any]
    runtime_override: dict[str, Any]
    cost_override: dict[str, Any]
    interpretation: dict[str, Any]
    authority: dict[str, Any]
    content_hash: Literal[AMENDMENT_CONTENT_HASH]


class HeldoutACBudgetAmendmentBinding(HeldoutACFrozenModel):
    path: Literal["experiments/heldout-ac-budget-amendment-20260815-v1.yaml"]
    amendment_id: Literal[AMENDMENT_ID]
    content_hash: Literal[AMENDMENT_CONTENT_HASH]
    file_bytes: Literal[AMENDMENT_FILE_BYTES]
    file_sha256: Literal[AMENDMENT_FILE_SHA256]


def _exact_typed_equal(actual: Any, expected: Any) -> bool:
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        return set(actual) == set(expected) and all(
            _exact_typed_equal(actual[key], value) for key, value in expected.items()
        )
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(
            _exact_typed_equal(left, right) for left, right in zip(actual, expected, strict=True)
        )
    return actual == expected


def _root(repository: str | Path | None) -> Path:
    return Path(repository).resolve() if repository is not None else repository_root().resolve()


def _closed_file(root: Path, relative: str, *, label: str) -> Path:
    lexical = root / relative
    current = lexical
    while current != root:
        if current.is_symlink():
            raise HeldoutACBudgetAmendmentError(f"{label} cannot traverse a symlink")
        current = current.parent
    resolved = lexical.resolve(strict=True)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise HeldoutACBudgetAmendmentError(f"{label} escapes the repository") from exc
    if not resolved.is_file():
        raise HeldoutACBudgetAmendmentError(f"{label} is not a file")
    return resolved


def _read_bound_json(root: Path, binding: dict[str, Any]) -> dict[str, Any]:
    path = _closed_file(root, binding["path"], label="development evidence")
    try:
        raw_bytes = path.read_bytes()
        payload = json.loads(raw_bytes)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HeldoutACBudgetAmendmentError("development evidence is invalid") from exc
    if not isinstance(payload, dict):
        raise HeldoutACBudgetAmendmentError("development evidence must be a JSON object")
    if len(raw_bytes) != binding["file_bytes"] or sha256_bytes(raw_bytes) != binding["file_sha256"]:
        raise HeldoutACBudgetAmendmentError("development evidence file binding drifted")
    return payload


def _usage_observation(
    *,
    label: str,
    observation_class: str,
    input_tokens: int | None,
    output_tokens: int | None,
    total_tokens: int,
    cost_nanos: int,
) -> dict[str, Any]:
    return {
        "label": label,
        "class": observation_class,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "cost_nanos": cost_nanos,
    }


def _extract_observations(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    r3, r5, r6, r8, v8, v9, v10 = evidence
    observations = [
        _usage_observation(
            label="r3-moto-a",
            observation_class="like-for-like-non-tail",
            input_tokens=None,
            output_tokens=None,
            total_tokens=r3["rows"][0]["total_tokens"],
            cost_nanos=r3["rows"][0]["cost_nanos"],
        ),
        _usage_observation(
            label="r3-moto-c-runaway",
            observation_class="like-for-like-runaway-tail",
            input_tokens=None,
            output_tokens=None,
            total_tokens=r3["rows"][1]["total_tokens"],
            cost_nanos=r3["rows"][1]["cost_nanos"],
        ),
    ]
    for label, payload in (("r5-moto-a", r5), ("r6-moto-a", r6)):
        row = payload["rows"][0]
        observations.append(
            _usage_observation(
                label=label,
                observation_class="like-for-like-non-tail",
                input_tokens=row["input_tokens"],
                output_tokens=row["output_tokens"],
                total_tokens=row["input_tokens"] + row["output_tokens"],
                cost_nanos=row["cost_nanos"],
            )
        )
    for label, row in zip(
        ("r8-moto-a", "r8-moto-c", "r8-babel-c", "r8-babel-a"),
        r8["rows"],
        strict=True,
    ):
        usage = row["usage"]
        observations.append(
            _usage_observation(
                label=label,
                observation_class="like-for-like-non-tail",
                input_tokens=usage["input_tokens"],
                output_tokens=usage["output_tokens"],
                total_tokens=usage["input_tokens"] + usage["output_tokens"],
                cost_nanos=row["usage_evidence"]["token_derived_cost_nanos"],
            )
        )
    for label, payload in (
        ("v8-development-stress", v8),
        ("v9-development-stress", v9),
        ("v10-development-stress", v10),
    ):
        usage = payload["run"]["usage"]
        observations.append(
            _usage_observation(
                label=label,
                observation_class="secondary-development-stress",
                input_tokens=usage["input_tokens"],
                output_tokens=usage["output_tokens"],
                total_tokens=usage["total_tokens"],
                cost_nanos=round(usage["model_cost_usd"] * 1_000_000_000),
            )
        )
    return observations


def _summary(observations: list[dict[str, Any]]) -> dict[str, int]:
    non_tail = [item for item in observations if item["class"] == "like-for-like-non-tail"]
    runaway = [item for item in observations if item["class"] == "like-for-like-runaway-tail"]
    stress = [item for item in observations if item["class"] == "secondary-development-stress"]
    return {
        "like_for_like_observation_count": len(non_tail) + len(runaway),
        "like_for_like_non_tail_count": len(non_tail),
        "like_for_like_non_tail_max_total_tokens": max(item["total_tokens"] for item in non_tail),
        "like_for_like_non_tail_max_cost_nanos": max(item["cost_nanos"] for item in non_tail),
        "like_for_like_non_tail_mean_cost_nanos_numerator": sum(
            item["cost_nanos"] for item in non_tail
        ),
        "like_for_like_non_tail_mean_cost_nanos_denominator": len(non_tail),
        "runaway_tail_total_tokens": runaway[0]["total_tokens"],
        "runaway_tail_cost_nanos": runaway[0]["cost_nanos"],
        "secondary_stress_count": len(stress),
        "secondary_stress_max_input_tokens": max(item["input_tokens"] for item in stress),
        "secondary_stress_max_output_tokens": max(item["output_tokens"] for item in stress),
        "secondary_stress_max_total_tokens": max(item["total_tokens"] for item in stress),
        "secondary_stress_max_cost_nanos": max(item["cost_nanos"] for item in stress),
    }


def load_heldout_ac_budget_amendment(
    *, repository: str | Path | None = None
) -> HeldoutACBudgetAmendment:
    """Validate the exact development-only amendment and its arithmetic."""

    root = _root(repository)
    path = _closed_file(root, AMENDMENT_PATH.as_posix(), label="budget amendment")
    try:
        raw_bytes = path.read_bytes()
        raw = load_unique_yaml(raw_bytes.decode("utf-8"))
        amendment = HeldoutACBudgetAmendment.model_validate(raw)
    except (OSError, UnicodeDecodeError, yaml.YAMLError, ValidationError) as exc:
        raise HeldoutACBudgetAmendmentError("held-out budget amendment is invalid") from exc
    if not isinstance(raw, dict):
        raise HeldoutACBudgetAmendmentError("held-out budget amendment must be a mapping")
    if len(raw_bytes) != AMENDMENT_FILE_BYTES or sha256_bytes(raw_bytes) != AMENDMENT_FILE_SHA256:
        raise HeldoutACBudgetAmendmentError("held-out budget amendment file binding drifted")
    body = {key: value for key, value in raw.items() if key != "content_hash"}
    if sha256_text(canonical_json(body)) != amendment.content_hash:
        raise HeldoutACBudgetAmendmentError("held-out budget amendment content hash drifted")

    base_path = _closed_file(root, _BASE_SUITE["path"], label="base suite")
    base_bytes = base_path.read_bytes()
    if (
        not _exact_typed_equal(amendment.base_suite, _BASE_SUITE)
        or len(base_bytes) != _BASE_SUITE["file_bytes"]
        or sha256_bytes(base_bytes) != _BASE_SUITE["file_sha256"]
    ):
        raise HeldoutACBudgetAmendmentError("held-out budget base-suite binding drifted")
    try:
        base_raw = load_unique_yaml(base_bytes.decode("utf-8"))
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        raise HeldoutACBudgetAmendmentError("held-out budget base suite is invalid") from exc
    if (
        not isinstance(base_raw, dict)
        or base_raw.get("content_hash") != _BASE_SUITE["content_hash"]
    ):
        raise HeldoutACBudgetAmendmentError("held-out budget base-suite content identity drifted")

    development = amendment.development_evidence
    if set(development) != {"files", "observations", "summary"}:
        raise HeldoutACBudgetAmendmentError("held-out budget evidence envelope drifted")
    if not _exact_typed_equal(development["files"], list(_EVIDENCE_FILES)):
        raise HeldoutACBudgetAmendmentError("held-out budget evidence file list drifted")
    evidence = [_read_bound_json(root, binding) for binding in _EVIDENCE_FILES]
    observations = _extract_observations(evidence)
    if not _exact_typed_equal(development["observations"], observations):
        raise HeldoutACBudgetAmendmentError("held-out budget observations differ from evidence")
    if not _exact_typed_equal(development["summary"], _summary(observations)):
        raise HeldoutACBudgetAmendmentError("held-out budget summary differs from evidence")
    for actual, expected, label in (
        (amendment.change_control, _EXPECTED_CHANGE_CONTROL, "change control"),
        (amendment.runtime_override, _EXPECTED_RUNTIME_OVERRIDE, "runtime override"),
        (amendment.cost_override, _EXPECTED_COST_OVERRIDE, "cost override"),
        (amendment.interpretation, _EXPECTED_INTERPRETATION, "interpretation"),
        (amendment.authority, _EXPECTED_AUTHORITY, "authority"),
    ):
        if not _exact_typed_equal(actual, expected):
            raise HeldoutACBudgetAmendmentError(f"held-out budget {label} drifted")

    cost = amendment.cost_override
    if not (
        cost["per_run_reserve_nanos"]
        == MAX_CUMULATIVE_INPUT_TOKENS * 750 + MAX_CUMULATIVE_OUTPUT_TOKENS * 4_500
        and cost["full_schedule_reserve_nanos"]
        == cost["per_run_reserve_nanos"] * cost["scheduled_run_count"]
        and cost["hard_cap_nanos"]
        == cost["full_schedule_reserve_nanos"] + cost["hard_cap_slack_nanos"]
        and MAX_TOTAL_TOKENS == MAX_CUMULATIVE_INPUT_TOKENS + MAX_CUMULATIVE_OUTPUT_TOKENS
    ):
        raise HeldoutACBudgetAmendmentError("held-out budget arithmetic drifted")
    return amendment


def heldout_ac_budget_amendment_binding(
    *, repository: str | Path | None = None
) -> HeldoutACBudgetAmendmentBinding:
    amendment = load_heldout_ac_budget_amendment(repository=repository)
    return HeldoutACBudgetAmendmentBinding(
        path=AMENDMENT_PATH.as_posix(),
        amendment_id=amendment.amendment_id,
        content_hash=amendment.content_hash,
        file_bytes=AMENDMENT_FILE_BYTES,
        file_sha256=AMENDMENT_FILE_SHA256,
    )


__all__ = [
    "AMENDMENT_CONTENT_HASH",
    "AMENDMENT_FILE_BYTES",
    "AMENDMENT_FILE_SHA256",
    "AMENDMENT_ID",
    "AMENDMENT_PATH",
    "FULL_SCHEDULE_RESERVE_NANOS",
    "HARD_CAP_NANOS",
    "HARD_CAP_SLACK_NANOS",
    "HeldoutACBudgetAmendment",
    "HeldoutACBudgetAmendmentBinding",
    "HeldoutACBudgetAmendmentError",
    "MAX_CUMULATIVE_INPUT_TOKENS",
    "MAX_CUMULATIVE_OUTPUT_TOKENS",
    "MAX_TOTAL_TOKENS",
    "PER_RUN_RESERVE_NANOS",
    "heldout_ac_budget_amendment_binding",
    "load_heldout_ac_budget_amendment",
]
