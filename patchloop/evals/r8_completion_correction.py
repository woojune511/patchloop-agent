"""Build the append-only R8 runtime index and completion-gate correction.

The paid R8 result is immutable.  This module binds its exact external files,
records the v1/v2 qualification-envelope mismatch, and recomputes only the
completion projection with the corrected offline consumer.
"""

from __future__ import annotations

import json
import os
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from patchloop.evals.runner import _ac_fixed_bundle_completion_gate
from patchloop.util import canonical_json, sha256_bytes, sha256_text

SCHEMA_VERSION = "ac-fixed-bundle-runtime-evidence-index-v5"
EXPERIMENT_ID = "dev-validation-ac-fixed-bundle-readiness-20260814-r8"
EXECUTION_HASH = "sha256:60c679083ad7b995918e2ba5de79843be8b03ce0511b67eb859da437f16cff9e"
EXECUTION_SOURCE_COMMIT = "a4f00f8565c840588b120d91e730427bb51166b5"
OUTPUT_PATH = Path(
    "reports/live-pilot/dev-validation-ac-fixed-bundle-readiness-20260814-r8-evidence-r4.json"
)
PREDECESSOR_OUTPUT_PATH = Path(
    "reports/live-pilot/dev-validation-ac-fixed-bundle-readiness-20260814-r8-evidence-r3.json"
)
SOURCE_QUALIFICATION_PATH = Path(
    "reports/live-pilot/artifacts/evaluator-v2-ac-successor-offline-source-qualification-r10.json"
)
RESULT_PATH = Path(f".patchloop/experiments/{EXPERIMENT_ID}.json")
JOURNAL_PATH = Path(f".patchloop/experiments/journals/{EXPERIMENT_ID}.jsonl")
PLAN_PATH = Path(f".patchloop/experiments/plans/{EXECUTION_HASH.removeprefix('sha256:')}.json")
PREPARED_RESULT_PATH = Path(
    ".patchloop/experiments/finalization/"
    f"{EXECUTION_HASH.removeprefix('sha256:')}/result.prepared.json"
)
CORRECTION_SOURCE_PATHS = (
    Path("patchloop/contracts.py"),
    Path("patchloop/evals/runner.py"),
    Path("patchloop/evals/r8_completion_correction.py"),
    Path("patchloop/util.py"),
    Path("scripts/build_r8_runtime_evidence.py"),
    Path("tests/test_ac_fixed_bundle_cost_completion.py"),
    Path("tests/test_r8_completion_correction.py"),
)
EXPECTED_CAMPAIGN = {
    "execution_hash": EXECUTION_HASH,
    "schedule_hash": "sha256:26026929c2992473b00ce58af760481d7406509f592b8d7674cb7ac6fa4a9a6d",
    "cost_control_hash": "sha256:50d9b7c93a01012df0751fbb63299fa0d080dc78536550524fd92c581a341d0e",
    "full_schedule_reserve_nanos": 15_300_000_000,
    "hard_cap_nanos": 18_000_000_000,
    "accrued_cost_nanos": 366_421_500,
    "actual_model_cost_usd": 0.3664215,
    "state": "SEALED",
    "raw_disposition": "inconclusive",
    "corrected_disposition": "complete-readiness-matrix",
    "expected_runs": 4,
    "terminal_runs": 4,
    "qualified_runs": 4,
    "receipt_qualified_evaluator_v2_runs": 4,
    "cost_settled_runs": 4,
    "not_started_runs": 0,
    "retry_or_replacement_performed": False,
}
EXPECTED_ROW_FACTS = (
    {
        "order": 1,
        "task_id": "moto-query-scanned-count",
        "condition": "no_memory",
        "run_id": "run_5a3113600554429e",
        "input_tokens": 116_952,
        "output_tokens": 4_649,
        "reasoning_output_tokens": 3_636,
        "model_calls": 12,
        "tool_calls": 17,
        "wall_clock_ms": 102_383,
        "model_cost_nanos": 108_634_500,
        "result_file_sha256": (
            "sha256:5ec2223c6958146004b4006c23dd19df361dae75f0114cecec90f1a013167d9a"
        ),
        "qualification_hash": (
            "sha256:ffb06a90e0812e07c2431166ab7c64aac14366e8e0efdffd1cf207538e79538a"
        ),
        "receipt_hash": "sha256:faa96dd0d460f25f74a3e1a4f08d3562122b6f83c3ee7e43a701716223048ee3",
    },
    {
        "order": 2,
        "task_id": "moto-query-scanned-count",
        "condition": "structured",
        "run_id": "run_69f76b4948af4d9d",
        "input_tokens": 81_655,
        "output_tokens": 1_949,
        "reasoning_output_tokens": 1_420,
        "model_calls": 9,
        "tool_calls": 11,
        "wall_clock_ms": 68_721,
        "model_cost_nanos": 70_011_750,
        "result_file_sha256": (
            "sha256:b96a894d8c583380b06e8068c448a39d4493e1534201238410356597cd35c187"
        ),
        "qualification_hash": (
            "sha256:a6f41cc85253db42a6e45cea4d2ad7ad964190901aebf304500a20d02efbeb9d"
        ),
        "receipt_hash": "sha256:e969999657c7e5bea2bb8b6c7942e9bcf86bcb687265767cfd7e86be2c37263a",
    },
    {
        "order": 3,
        "task_id": "babel-strict-grouped-decimal-trailing-zeroes",
        "condition": "structured",
        "run_id": "run_d10f4197b45342d5",
        "input_tokens": 67_627,
        "output_tokens": 4_866,
        "reasoning_output_tokens": 4_385,
        "model_calls": 8,
        "tool_calls": 8,
        "wall_clock_ms": 45_209,
        "model_cost_nanos": 72_617_250,
        "result_file_sha256": (
            "sha256:3432e5252b09e655174cab25daa2bfc954d68cb518f2dbdce218a4d14b40db9f"
        ),
        "qualification_hash": (
            "sha256:f163ef6a1f5f8b3a2654ad0677a823a4bd22943aa5a4b04b8b0a72e274fe77c1"
        ),
        "receipt_hash": "sha256:9baa4e529128bd085227f8d80ecf32ce155d354e0d3b0a9d674042056e76a5b5",
    },
    {
        "order": 4,
        "task_id": "babel-strict-grouped-decimal-trailing-zeroes",
        "condition": "no_memory",
        "run_id": "run_cc33bef38c8a42d0",
        "input_tokens": 99_532,
        "output_tokens": 9_002,
        "reasoning_output_tokens": 8_199,
        "model_calls": 12,
        "tool_calls": 15,
        "wall_clock_ms": 72_849,
        "model_cost_nanos": 115_158_000,
        "result_file_sha256": (
            "sha256:c35baf01a27fb5ecb1eb4de94d2d57b4d15a300ad8c347086524e84b997181c7"
        ),
        "qualification_hash": (
            "sha256:9a51e3ac6f4e20e354ac149495c1b0c52ce72286015bbb5160d4987c4c7a3276"
        ),
        "receipt_hash": "sha256:07487f85e54b118db990122f67b3c41fa385f47e90f912acbb08bb9e1fa1b473",
    },
)


class R8CompletionCorrectionError(RuntimeError):
    """Raised when immutable R8 evidence or its correction differs."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise R8CompletionCorrectionError(message)


def _exact_typed_equal(actual: Any, expected: Any) -> bool:
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        return set(actual) == set(expected) and all(
            _exact_typed_equal(actual[key], expected[key]) for key in expected
        )
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(
            _exact_typed_equal(actual_item, expected_item)
            for actual_item, expected_item in zip(actual, expected, strict=True)
        )
    return bool(actual == expected)


def _root(repository: str | Path | None = None) -> Path:
    selected = Path(repository) if repository is not None else Path.cwd()
    resolved = selected.resolve(strict=True)
    _require((resolved / "pyproject.toml").is_file(), "repository root is invalid")
    return resolved


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def _loads_unique_json(raw: bytes, label: str) -> Any:
    try:
        return json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_pairs,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise R8CompletionCorrectionError(f"{label} is not unique UTF-8 JSON") from exc


def _read(root: Path, relative: Path) -> bytes:
    _require(not relative.is_absolute(), "R8 evidence path must be repository-relative")
    logical = root / relative
    current = root
    for part in relative.parts:
        current /= part
        _require(not current.is_symlink(), f"R8 evidence path is linked: {relative.as_posix()}")
    path = logical.resolve(strict=True)
    _require(
        path.is_relative_to(root), f"R8 evidence path escapes repository: {relative.as_posix()}"
    )
    _require(path.is_file(), f"required R8 file is missing: {relative.as_posix()}")
    first = path.read_bytes()
    second = path.read_bytes()
    _require(first == second, f"R8 file changed while reading: {relative.as_posix()}")
    return first


def _json(raw: bytes, label: str) -> dict[str, Any]:
    payload = _loads_unique_json(raw, label)
    _require(isinstance(payload, dict), f"{label} root is not an object")
    return payload


def _file_binding(root: Path, relative: Path) -> dict[str, Any]:
    raw = _read(root, relative)
    return {
        "path": relative.as_posix(),
        "file_sha256": sha256_bytes(raw),
        "file_bytes": len(raw),
    }


def _validate_journal(raw: bytes, result_hash: str) -> tuple[list[dict[str, Any]], str]:
    _require(raw.endswith(b"\n"), "R8 journal is not newline terminated")
    try:
        events = [
            _loads_unique_json(line.encode("utf-8"), "R8 journal event")
            for line in raw.decode("utf-8").splitlines()
        ]
    except (UnicodeDecodeError, R8CompletionCorrectionError) as exc:
        raise R8CompletionCorrectionError("R8 journal is invalid") from exc
    previous: str | None = None
    for sequence, event in enumerate(events, start=1):
        _require(isinstance(event, dict), "R8 journal event is not an object")
        recorded_hash = event.get("event_hash")
        body = {key: value for key, value in event.items() if key != "event_hash"}
        _require(
            _exact_typed_equal(event.get("sequence"), sequence),
            "R8 journal sequence differs",
        )
        _require(
            _exact_typed_equal(event.get("previous_event_hash"), previous),
            "R8 journal chain differs",
        )
        _require(
            _exact_typed_equal(recorded_hash, sha256_text(canonical_json(body))),
            "R8 event hash differs",
        )
        previous = recorded_hash
    _require(len(events) == 15, "R8 journal event count differs")
    _require(events[-1].get("event_type") == "CampaignCompleted", "R8 is not sealed")
    _require(
        (events[-1].get("payload") or {}).get("result_hash") == result_hash,
        "R8 final event does not bind the result",
    )
    return events, str(previous)


def _row_evidence(
    root: Path,
    row: dict[str, Any],
    terminal_payload: dict[str, Any],
) -> dict[str, Any]:
    run_id = row.get("run_id")
    _require(isinstance(run_id, str) and bool(run_id), "R8 row run ID is invalid")
    result_path = Path(f".patchloop/artifacts/runs/{run_id}/result.json")
    qualification_path = Path(f".patchloop/qualifications/{run_id}.json")
    receipt_path = Path(f".patchloop/artifacts/runs/{run_id}/evaluation-receipt.json")
    run_result_raw = _read(root, result_path)
    qualification_raw = _read(root, qualification_path)
    receipt_raw = _read(root, receipt_path)
    run_result = _json(run_result_raw, f"{run_id} result")
    qualification = _json(qualification_raw, f"{run_id} qualification")
    receipt = _json(receipt_raw, f"{run_id} receipt")
    _require(
        _exact_typed_equal(run_result, row.get("result")),
        f"{run_id} durable result differs",
    )
    row_qualification = row.get("qualification")
    _require(isinstance(row_qualification, dict), f"{run_id} row qualification is missing")
    for key in (
        "run_id",
        "experiment_id",
        "task_id",
        "execution_hash",
        "schedule_row_id",
        "outcome_kind",
        "qualified",
        "qualification_hash",
        "source_evidence_hash",
        "evaluator_version",
        "evaluator_v2_receipt_hash",
        "evaluator_v2_receipt_file_hash",
        "evaluator_v2_source_hash",
        "evaluator_v2_source_qualification_hash",
        "evaluator_v2_runtime_authenticated",
        "evaluator_v2_completion_eligible",
    ):
        _require(
            _exact_typed_equal(qualification.get(key), row_qualification.get(key)),
            f"{run_id} qualification binding differs: {key}",
        )
    _require(
        _exact_typed_equal(qualification.get("memory_condition"), row.get("condition")),
        f"{run_id} qualification condition differs",
    )
    _require(run_result.get("outcome_kind") == "resolved", f"{run_id} did not resolve")
    _require(
        qualification.get("schema_version") == "trace-qualification-v2",
        "producer schema differs",
    )
    _require(qualification.get("qualified") is True, f"{run_id} is not trace-qualified")
    _require(qualification.get("evaluator_v2_completion_eligible") is True, "v2 row is ineligible")
    _require(
        qualification.get("evaluator_v2_runtime_authenticated") is True,
        "v2 row is unauthenticated",
    )
    _require(
        receipt.get("content_hash") == qualification.get("evaluator_v2_receipt_hash"),
        "receipt differs",
    )
    _require(receipt.get("runtime_authenticated") is True, "receipt is unauthenticated")
    _require(receipt.get("qualification_eligible") is True, "receipt is ineligible")
    usage = row.get("usage")
    _require(isinstance(usage, dict), f"{run_id} usage is missing")
    usage_evidence = terminal_payload.get("usage_evidence")
    _require(isinstance(usage_evidence, dict), f"{run_id} usage evidence is missing")
    usage_descriptor = usage_evidence.get("descriptor")
    _require(isinstance(usage_descriptor, dict), f"{run_id} usage descriptor is missing")
    _require(
        terminal_payload.get("qualification_hash") == qualification.get("qualification_hash"),
        f"{run_id} terminal qualification differs",
    )
    _require(
        usage_descriptor.get("qualification_hash") == qualification.get("qualification_hash"),
        f"{run_id} durable qualification differs",
    )
    _require(
        usage_descriptor.get("source_evidence_hash") == qualification.get("source_evidence_hash"),
        f"{run_id} durable source evidence differs",
    )
    persisted_result_hash = sha256_bytes(run_result_raw)
    _require(
        usage_descriptor.get("persisted_result_hash") == persisted_result_hash,
        f"{run_id} durable result hash differs",
    )
    _require(
        receipt.get("result_file_hash") == persisted_result_hash,
        f"{run_id} receipt result hash differs",
    )
    _require(
        qualification.get("evaluator_v2_receipt_file_hash") == sha256_bytes(receipt_raw),
        f"{run_id} receipt file hash differs",
    )
    descriptor_usage = usage_descriptor.get("usage")
    _require(isinstance(descriptor_usage, dict), f"{run_id} durable usage is missing")
    _require(
        _exact_typed_equal(
            {key: usage.get(key) for key in descriptor_usage},
            descriptor_usage,
        ),
        f"{run_id} durable usage differs",
    )
    _require(
        usage_descriptor.get("token_derived_cost_nanos")
        == round(float(usage.get("model_cost_usd")) * 1_000_000_000),
        f"{run_id} durable cost differs",
    )
    return {
        "order": row.get("order"),
        "task_id": row.get("task_id"),
        "condition": row.get("condition"),
        "run_id": run_id,
        "outcome_kind": run_result.get("outcome_kind"),
        "verdicts": run_result.get("verdicts"),
        "trace_qualified": True,
        "evaluation_reached": qualification.get("evaluation_reached"),
        "evaluator_v2_runtime_authenticated": True,
        "evaluator_v2_completion_eligible": True,
        "usage": usage,
        "result": {
            **_file_binding(root, result_path),
            "persisted_result_hash": persisted_result_hash,
        },
        "qualification": {
            **_file_binding(root, qualification_path),
            "schema_version": qualification.get("schema_version"),
            "qualification_hash": qualification.get("qualification_hash"),
            "source_evidence_hash": qualification.get("source_evidence_hash"),
        },
        "evaluation_receipt": {
            **_file_binding(root, receipt_path),
            "receipt_hash": receipt.get("content_hash"),
        },
        "usage_evidence": {
            "content_hash": usage_evidence.get("content_hash"),
            "persisted_result_hash": persisted_result_hash,
            "token_derived_cost_nanos": usage_descriptor.get("token_derived_cost_nanos"),
        },
    }


def _descriptive_pairs(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_identity = {(row["task_id"], row["condition"]): row for row in rows}
    pairs: list[dict[str, Any]] = []
    for task_id in (
        "moto-query-scanned-count",
        "babel-strict-grouped-decimal-trailing-zeroes",
    ):
        no_memory = by_identity[(task_id, "no_memory")]
        structured = by_identity[(task_id, "structured")]
        no_memory_total = no_memory["usage"]["input_tokens"] + no_memory["usage"]["output_tokens"]
        structured_total = (
            structured["usage"]["input_tokens"] + structured["usage"]["output_tokens"]
        )
        no_memory_cost = no_memory["usage_evidence"]["token_derived_cost_nanos"]
        structured_cost = structured["usage_evidence"]["token_derived_cost_nanos"]
        pairs.append(
            {
                "task_id": task_id,
                "no_memory": {
                    "run_id": no_memory["run_id"],
                    "resolved": no_memory["outcome_kind"] == "resolved",
                    "total_tokens": no_memory_total,
                    "model_cost_nanos": no_memory_cost,
                },
                "structured": {
                    "run_id": structured["run_id"],
                    "resolved": structured["outcome_kind"] == "resolved",
                    "total_tokens": structured_total,
                    "model_cost_nanos": structured_cost,
                },
                "structured_minus_no_memory": {
                    "resolved_delta": 0,
                    "total_tokens": structured_total - no_memory_total,
                    "model_cost_nanos": structured_cost - no_memory_cost,
                },
            }
        )
    return pairs


def _row_fact(row: dict[str, Any]) -> dict[str, Any]:
    usage = row.get("usage") if isinstance(row.get("usage"), dict) else {}
    usage_evidence = (
        row.get("usage_evidence") if isinstance(row.get("usage_evidence"), dict) else {}
    )
    result = row.get("result") if isinstance(row.get("result"), dict) else {}
    qualification = row.get("qualification") if isinstance(row.get("qualification"), dict) else {}
    receipt = (
        row.get("evaluation_receipt") if isinstance(row.get("evaluation_receipt"), dict) else {}
    )
    return {
        "order": row.get("order"),
        "task_id": row.get("task_id"),
        "condition": row.get("condition"),
        "run_id": row.get("run_id"),
        "input_tokens": usage.get("input_tokens"),
        "output_tokens": usage.get("output_tokens"),
        "reasoning_output_tokens": usage.get("reasoning_output_tokens"),
        "model_calls": usage.get("model_calls"),
        "tool_calls": usage.get("tool_calls"),
        "wall_clock_ms": usage.get("wall_clock_ms"),
        "model_cost_nanos": usage_evidence.get("token_derived_cost_nanos"),
        "result_file_sha256": result.get("file_sha256"),
        "qualification_hash": qualification.get("qualification_hash"),
        "receipt_hash": receipt.get("receipt_hash"),
    }


def _validate_static_index(root: Path, payload: dict[str, Any]) -> None:
    expected_keys = {
        "schema_version",
        "recorded_at",
        "experiment_id",
        "evidence_scope",
        "execution_source_commit",
        "source_qualification",
        "predecessor_correction_index",
        "campaign",
        "completion_correction",
        "external_artifacts",
        "journal_event_counts",
        "rows",
        "descriptive_paired_analysis",
        "correction_source_bindings",
        "claim_authority",
        "correction_runtime_boundary",
        "content_hash",
    }
    _require(set(payload) == expected_keys, "R8 evidence envelope differs")
    _require(payload.get("schema_version") == SCHEMA_VERSION, "R8 evidence schema differs")
    _require(payload.get("experiment_id") == EXPERIMENT_ID, "R8 evidence identity differs")
    _require(
        payload.get("execution_source_commit") == EXECUTION_SOURCE_COMMIT,
        "R8 execution source differs",
    )
    recorded_at = payload.get("recorded_at")
    _require(
        type(recorded_at) is str and recorded_at.endswith("Z"),
        "R8 evidence timestamp differs",
    )
    try:
        parsed_at = datetime.fromisoformat(recorded_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise R8CompletionCorrectionError("R8 evidence timestamp is invalid") from exc
    _require(parsed_at.tzinfo == UTC, "R8 evidence timestamp is not UTC")

    expected_source = {
        **_file_binding(root, SOURCE_QUALIFICATION_PATH),
        "qualification_hash": (
            "sha256:66bd54bcce94e69297d3045ad1a50f7e5266f9ea6c6b0ba305179f93d0a88b25"
        ),
        "evaluator_source_hash": (
            "sha256:6c6594b4121a30ecf634a94c0ac39a0218cff25de85ef445123b7b710212bcb1"
        ),
        "successor_suite_hash": (
            "sha256:0c42c3a587e9127c908bf13906ee6a101e2ccc4f8e5caa1186c418eaa77d71f2"
        ),
    }
    _require(
        _exact_typed_equal(payload.get("source_qualification"), expected_source),
        "R8 source qualification binding differs",
    )
    predecessor = payload.get("predecessor_correction_index")
    _require(isinstance(predecessor, dict), "R8 correction predecessor is missing")
    _require(
        _exact_typed_equal(
            {key: predecessor.get(key) for key in ("path", "file_sha256", "file_bytes")},
            _file_binding(root, PREDECESSOR_OUTPUT_PATH),
        ),
        "R8 correction predecessor binding differs",
    )
    _require(
        _exact_typed_equal(payload.get("campaign"), EXPECTED_CAMPAIGN),
        "R8 campaign facts differ",
    )
    expected_external = {
        "execution_plan": {
            "path": PLAN_PATH.as_posix(),
            "file_sha256": (
                "sha256:4181bacd01b4bcedbe650edc7063588623a3313e3eef3b884865f196af9532c5"
            ),
            "file_bytes": 20_386,
            "artifact_hash": (
                "sha256:efb712fbfd62764567d736f6e7aeef89732ec19384ee13ea8cfc29425847358b"
            ),
        },
        "journal": {
            "path": JOURNAL_PATH.as_posix(),
            "file_sha256": (
                "sha256:f05dc041ea2196f790d7df3985d0731c0dfd2878f0c273f6e4811d81cdc0446a"
            ),
            "file_bytes": 21_654,
            "event_count": 15,
            "last_event_hash": (
                "sha256:73f17d9ceab7963e8826095ab785b9668edb80267392361cccab91c3b1d950a2"
            ),
        },
        "prepared_result": {
            "path": PREPARED_RESULT_PATH.as_posix(),
            "file_sha256": (
                "sha256:8dbcb60a8a7f2937b00f7729561755cd9ef9b023d84ce64be4a0230ec5cc2878"
            ),
            "file_bytes": 138_156,
        },
        "final_result": {
            "path": RESULT_PATH.as_posix(),
            "file_sha256": (
                "sha256:8dbcb60a8a7f2937b00f7729561755cd9ef9b023d84ce64be4a0230ec5cc2878"
            ),
            "file_bytes": 138_156,
            "same_bytes_as_prepared_result": True,
        },
    }
    _require(
        _exact_typed_equal(payload.get("external_artifacts"), expected_external),
        "R8 external artifact facts differ",
    )
    _require(
        _exact_typed_equal(
            payload.get("journal_event_counts"),
            {
                "CampaignCompleted": 1,
                "CampaignStarted": 1,
                "FullScheduleCostReserved": 1,
                "RunCostSettled": 4,
                "RunStarted": 4,
                "RunTerminal": 4,
            },
        ),
        "R8 journal event facts differ",
    )
    rows = payload.get("rows")
    _require(isinstance(rows, list), "R8 evidence rows are missing")
    _require(
        _exact_typed_equal([_row_fact(row) for row in rows], list(EXPECTED_ROW_FACTS)),
        "R8 row facts differ",
    )
    _require(
        all(
            row.get("outcome_kind") == "resolved"
            and row.get("verdicts")
            == {
                "hidden_tests": "pass",
                "regression_tests": "pass",
                "scope_policy": "pass",
                "safety_policy": "pass",
            }
            and row.get("trace_qualified") is True
            and row.get("evaluation_reached") is True
            and row.get("evaluator_v2_runtime_authenticated") is True
            and row.get("evaluator_v2_completion_eligible") is True
            for row in rows
        ),
        "R8 row qualification facts differ",
    )
    expected_analysis = {
        "analysis_unit": "two development-validation task pairs with one repetition",
        "pairs": _descriptive_pairs(rows),
        "success_delta_observed": 0,
        "inferential_memory_effect_claim_authorized": False,
    }
    _require(
        _exact_typed_equal(payload.get("descriptive_paired_analysis"), expected_analysis),
        "R8 descriptive analysis differs",
    )
    _require(
        _exact_typed_equal(
            payload.get("correction_source_bindings"),
            [_file_binding(root, path) for path in CORRECTION_SOURCE_PATHS],
        ),
        "R8 correction source differs",
    )
    _require(
        _exact_typed_equal(
            payload.get("claim_authority"),
            {
                "development_readiness_matrix_complete": True,
                "descriptive_paired_analysis_ready": True,
                "memory_effect_claim_authorized": False,
                "retrieval_quality_claim_authorized": False,
                "heldout_generalization_claim_authorized": False,
                "core_campaign_authorized": False,
            },
        ),
        "R8 claim authority differs",
    )
    _require(
        _exact_typed_equal(
            payload.get("correction_runtime_boundary"),
            {
                "provider_calls_made": 0,
                "evaluator_calls_made": 0,
                "docker_calls_made": 0,
                "agent_runs_made": 0,
                "added_model_cost_usd": 0,
                "paid_execution_authorized": False,
            },
        ),
        "R8 correction runtime boundary differs",
    )
    correction = payload.get("completion_correction")
    _require(isinstance(correction, dict), "R8 completion correction is missing")
    original = correction.get("original_completion_gate")
    corrected = correction.get("corrected_completion_gate")
    _require(
        correction.get("producer_schema_version") == "trace-qualification-v2"
        and correction.get("original_consumer_schema_version") == "trace-qualification-v1"
        and correction.get("original_result_rewritten") is False
        and correction.get("provider_or_evaluator_reexecution_performed") is False
        and isinstance(original, dict)
        and original.get("passed") is False
        and _exact_typed_equal(original.get("official_evaluator_runs"), 0)
        and _exact_typed_equal(original.get("unclassified_runs"), 4)
        and _exact_typed_equal(original.get("task_failures"), -4)
        and isinstance(corrected, dict)
        and corrected.get("passed") is True
        and corrected.get("analysis_ready") is True
        and _exact_typed_equal(corrected.get("official_evaluator_runs"), 4)
        and _exact_typed_equal(corrected.get("unclassified_runs"), 0)
        and _exact_typed_equal(corrected.get("task_successes"), 4)
        and _exact_typed_equal(corrected.get("task_failures"), 0),
        "R8 completion correction facts differ",
    )


def _build(root: Path, recorded_at: datetime) -> dict[str, Any]:
    result_raw = _read(root, RESULT_PATH)
    result_hash = sha256_bytes(result_raw)
    result = _json(result_raw, "R8 final result")
    prepared_raw = _read(root, PREPARED_RESULT_PATH)
    _require(prepared_raw == result_raw, "R8 prepared and final result bytes differ")
    plan_raw = _read(root, PLAN_PATH)
    plan = _json(plan_raw, "R8 execution plan")
    journal_raw = _read(root, JOURNAL_PATH)
    events, last_event_hash = _validate_journal(journal_raw, result_hash)
    source_raw = _read(root, SOURCE_QUALIFICATION_PATH)
    source = _json(source_raw, "R10 source qualification")
    predecessor_raw = _read(root, PREDECESSOR_OUTPUT_PATH)
    predecessor = _json(predecessor_raw, "R8 correction predecessor")

    _require(result.get("experiment_id") == EXPERIMENT_ID, "R8 experiment identity differs")
    _require(result.get("execution_hash") == EXECUTION_HASH, "R8 execution hash differs")
    _require(result.get("completed_runs") == 4, "R8 completed-run count differs")
    _require(result.get("actual_model_cost_usd") == 0.3664215, "R8 cost differs")
    _require(
        _exact_typed_equal(
            plan.get("environment", {}).get("git"),
            {
                "available": True,
                "commit": EXECUTION_SOURCE_COMMIT,
                "clean": True,
                "execution_clean": True,
                "dirty_paths": [],
                "ignored_documentation_paths": [],
                "execution_dirty_paths": [],
            },
        ),
        "R8 execution source binding differs",
    )
    _require(
        plan.get("suite_hash") == source["successor_suite"]["content_hash"],
        "R8 plan and R10 suite binding differ",
    )
    _require(
        predecessor.get("content_hash")
        == "sha256:dc00ac13d7d03970c6575f03d6c4ec76c0085ade8562fedfc536f416be6192aa",
        "R8 correction predecessor content differs",
    )
    _require(
        sha256_bytes(predecessor_raw)
        == "sha256:24f942d487be1d30280a20f2a34a1bea7f3679c2756080c1d6cc7f0fdd1f7e38",
        "R8 correction predecessor file differs",
    )
    original_gate = result.get("completion_gate")
    _require(isinstance(original_gate, dict), "R8 original completion gate is missing")
    _require(
        original_gate.get("passed") is False
        and original_gate.get("official_evaluator_runs") == 0
        and original_gate.get("unclassified_runs") == 4
        and original_gate.get("task_failures") == -4,
        "R8 original completion defect differs",
    )
    cost_control = result.get("campaign_cost_control")
    cost_qualification = result.get("campaign_cost_qualification")
    _require(isinstance(cost_control, dict), "R8 cost control is missing")
    _require(isinstance(cost_qualification, dict), "R8 cost qualification is missing")
    corrected_gate = _ac_fixed_bundle_completion_gate(
        result["runs"],
        expected_experiment_id=EXPERIMENT_ID,
        expected_execution_hash=EXECUTION_HASH,
        expected_schedule=plan["schedule"],
        expected_campaign_cost_control_hash=cost_control["content_hash"],
        campaign_cost_qualification=cost_qualification,
    )
    _require(
        corrected_gate.get("passed") is True
        and corrected_gate.get("analysis_ready") is True
        and corrected_gate.get("official_evaluator_runs") == 4
        and corrected_gate.get("unclassified_runs") == 0
        and corrected_gate.get("task_successes") == 4
        and corrected_gate.get("task_failures") == 0,
        "corrected R8 completion projection differs",
    )
    _require(
        all(
            corrected_gate.get(field) is False
            for field in (
                "memory_effect_claim_authorized",
                "retrieval_quality_claim_authorized",
                "heldout_generalization_claim_authorized",
                "core_campaign_unlocked",
            )
        ),
        "R8 correction widened claim authority",
    )
    terminal_payloads = {
        event["payload"]["run_id"]: event["payload"]
        for event in events
        if event.get("event_type") == "RunTerminal"
    }
    _require(len(terminal_payloads) == 4, "R8 terminal event count differs")
    rows = [
        _row_evidence(root, row, terminal_payloads[str(row.get("run_id"))])
        for row in result["runs"]
    ]
    descriptive_pairs = _descriptive_pairs(rows)
    event_counts = dict(sorted(Counter(event["event_type"] for event in events).items()))
    source_bindings = [_file_binding(root, path) for path in CORRECTION_SOURCE_PATHS]
    body: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "recorded_at": recorded_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "experiment_id": EXPERIMENT_ID,
        "evidence_scope": "append-only R8 live result index and offline completion-gate correction",
        "execution_source_commit": EXECUTION_SOURCE_COMMIT,
        "source_qualification": {
            **_file_binding(root, SOURCE_QUALIFICATION_PATH),
            "qualification_hash": source.get("content_hash"),
            "evaluator_source_hash": source.get("evaluator_source_hash"),
            "successor_suite_hash": source["successor_suite"]["content_hash"],
        },
        "predecessor_correction_index": {
            **_file_binding(root, PREDECESSOR_OUTPUT_PATH),
            "content_hash": predecessor.get("content_hash"),
            "disposition": "superseded-by-portable-strict-static-validation-index",
            "runtime_evidence_changed": False,
        },
        "campaign": {
            "execution_hash": EXECUTION_HASH,
            "schedule_hash": result.get("schedule_hash"),
            "cost_control_hash": cost_control.get("content_hash"),
            "full_schedule_reserve_nanos": cost_qualification.get("full_schedule_reserve_nanos"),
            "hard_cap_nanos": cost_qualification.get("hard_cap_nanos"),
            "accrued_cost_nanos": cost_qualification.get("accrued_cost_nanos"),
            "actual_model_cost_usd": result.get("actual_model_cost_usd"),
            "state": "SEALED",
            "raw_disposition": original_gate.get("disposition"),
            "corrected_disposition": corrected_gate.get("disposition"),
            "expected_runs": 4,
            "terminal_runs": 4,
            "qualified_runs": 4,
            "receipt_qualified_evaluator_v2_runs": 4,
            "cost_settled_runs": 4,
            "not_started_runs": 0,
            "retry_or_replacement_performed": False,
        },
        "completion_correction": {
            "kind": "offline-read-only-completion-projection-correction",
            "direct_cause": (
                "the immutable producer emitted trace-qualification-v2 while the completion "
                "envelope accepted only trace-qualification-v1"
            ),
            "producer_schema_version": "trace-qualification-v2",
            "original_consumer_schema_version": "trace-qualification-v1",
            "affected_run_ids": [row["run_id"] for row in rows],
            "original_completion_gate": original_gate,
            "corrected_completion_gate": corrected_gate,
            "original_result_rewritten": False,
            "provider_or_evaluator_reexecution_performed": False,
        },
        "external_artifacts": {
            "execution_plan": {
                **_file_binding(root, PLAN_PATH),
                "artifact_hash": result["execution_plan"]["artifact_hash"],
            },
            "journal": {
                **_file_binding(root, JOURNAL_PATH),
                "event_count": len(events),
                "last_event_hash": last_event_hash,
            },
            "prepared_result": _file_binding(root, PREPARED_RESULT_PATH),
            "final_result": {
                **_file_binding(root, RESULT_PATH),
                "same_bytes_as_prepared_result": True,
            },
        },
        "journal_event_counts": event_counts,
        "rows": rows,
        "descriptive_paired_analysis": {
            "analysis_unit": "two development-validation task pairs with one repetition",
            "pairs": descriptive_pairs,
            "success_delta_observed": 0,
            "inferential_memory_effect_claim_authorized": False,
        },
        "correction_source_bindings": source_bindings,
        "claim_authority": {
            "development_readiness_matrix_complete": True,
            "descriptive_paired_analysis_ready": True,
            "memory_effect_claim_authorized": False,
            "retrieval_quality_claim_authorized": False,
            "heldout_generalization_claim_authorized": False,
            "core_campaign_authorized": False,
        },
        "correction_runtime_boundary": {
            "provider_calls_made": 0,
            "evaluator_calls_made": 0,
            "docker_calls_made": 0,
            "agent_runs_made": 0,
            "added_model_cost_usd": 0,
            "paid_execution_authorized": False,
        },
    }
    body["content_hash"] = sha256_text(canonical_json(body))
    return body


def _canonical_bytes(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def validate_r8_runtime_evidence(
    *, repository: str | Path | None = None, require_external: bool = False
) -> dict[str, Any]:
    root = _root(repository)
    raw = _read(root, OUTPUT_PATH)
    payload = _json(raw, "R8 evidence index")
    _require(raw == _canonical_bytes(payload), "R8 evidence index bytes are noncanonical")
    content_hash = payload.get("content_hash")
    body = {key: value for key, value in payload.items() if key != "content_hash"}
    _require(content_hash == sha256_text(canonical_json(body)), "R8 evidence hash differs")
    _validate_static_index(root, payload)
    external_available = (root / RESULT_PATH).is_file()
    if require_external or external_available:
        recorded_at = datetime.fromisoformat(str(payload["recorded_at"]).replace("Z", "+00:00"))
        _require(payload == _build(root, recorded_at), "R8 external evidence differs")
    return {
        "status": "CORRECTED_COMPLETE_READINESS_MATRIX",
        "content_hash": content_hash,
        "file_sha256": sha256_bytes(raw),
        "file_bytes": len(raw),
        "external_evidence_revalidated": external_available,
        "provider_calls_made": 0,
        "evaluator_calls_made": 0,
        "docker_calls_made": 0,
        "agent_runs_made": 0,
    }


def run_r8_runtime_evidence(*, repository: str | Path | None = None) -> dict[str, Any]:
    root = _root(repository)
    output = (root / OUTPUT_PATH).resolve(strict=False)
    if output.exists():
        return validate_r8_runtime_evidence(repository=root)
    payload = _build(root, datetime.now(UTC))
    raw = _canonical_bytes(payload)
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with output.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    except OSError as exc:
        raise R8CompletionCorrectionError("R8 evidence index cannot be created") from exc
    return validate_r8_runtime_evidence(repository=root, require_external=True)


__all__ = [
    "EXECUTION_HASH",
    "EXPERIMENT_ID",
    "OUTPUT_PATH",
    "R8CompletionCorrectionError",
    "run_r8_runtime_evidence",
    "validate_r8_runtime_evidence",
]
