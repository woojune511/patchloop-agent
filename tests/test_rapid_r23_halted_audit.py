from __future__ import annotations

import contextlib
import json
import socket
import sqlite3
from collections import Counter
from decimal import Decimal
from pathlib import Path

import pytest

from patchloop.agent.tools import TOOL_SCHEMAS_V26, TOOL_SCHEMAS_V27
from patchloop.contracts import RunEvent
from patchloop.errors import ContractError
from patchloop.evals.rapid_batch_driver import load_rapid_batch_driver_journal
from patchloop.evals.rapid_public_development_v4 import _runtime_build_binding
from patchloop.evals.rapid_workflow_diagnosis import _load_bundle, _tool_input
from patchloop.util import canonical_json, sha256_bytes, sha256_json

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "rapid-public-dev-anyio-v5-batch-image-ab-20260831-r23"
EXECUTION = "sha256:d9d3818c9d2b80eb8238746c510fd071d808fb734bdc7f3d74837548c967d309"
RUN_PREFIX = "run_rapid_v32_d9d3818c9d2b_"
CANDIDATE = Path("reports/rapid-development/artifacts") / f"{PREFIX}-candidate-v32.json"
REHEARSAL = CANDIDATE.with_name(f"{PREFIX}-candidate-v32-rehearsal-v29.json")
BUNDLE = Path("reports/rapid-development") / f"{PREFIX}-d9d3818c9d2b.jsonl"
IMAGE_RECEIPT = BUNDLE.with_name(f"{PREFIX}-d9d3818c9d2b.image-admission.jsonl")
AUDIT = CANDIDATE.with_name(f"{PREFIX}-candidate-v32-halted-public-audit-v1.json")


def _file_record(path: Path) -> dict:
    raw = (ROOT / path).read_bytes()
    return {"path": path.as_posix(), "bytes": len(raw), "file_sha256": sha256_bytes(raw)}


def _sealed(value: dict) -> dict:
    body = {key: item for key, item in value.items() if key != "content_hash"}
    assert value["content_hash"] == sha256_json(body)
    return value


def _build_audit(*, verify_current_runtime: bool = False) -> dict:
    """Read-only, run-scoped audit; never regenerate a candidate or live capability."""
    candidate = _sealed(json.loads((ROOT / CANDIDATE).read_bytes()))
    rehearsal = _sealed(json.loads((ROOT / REHEARSAL).read_bytes()))
    assert candidate["execution_hash"] == rehearsal["execution_hash"] == EXECUTION
    if verify_current_runtime:
        assert _runtime_build_binding(ROOT)[0] == candidate["runtime_build_hash"]
    unvalidated = [json.loads(line) for line in (ROOT / BUNDLE).read_text().splitlines()]
    first = unvalidated[0]
    capabilities = rehearsal["all_row_capabilities"]
    contract = {
        "schema_version": "rapid-append-only-batch-driver-contract-v1",
        "policy_version": first["driver_policy_version"],
        "official": False,
        **{
            key: first[key]
            for key in (
                "experiment_id",
                "execution_hash",
                "plan_hash",
                "runtime_build_hash",
                "schedule_hash",
                "cost_control_hash",
                "row_reserve_nanos",
                "full_schedule_reserve_nanos",
                "hard_cap_nanos",
            )
        },
        "manifest_hashes": tuple(row["manifest_hash"] for row in capabilities),
        "schedule_row_ids": tuple(row["schedule_row_id"] for row in capabilities),
        "run_ids": tuple(row["run_id"] for row in capabilities),
        "content_hash": first["driver_contract_hash"],
    }
    journal = load_rapid_batch_driver_journal(ROOT / BUNDLE, contract)
    final = journal[-1]
    assert final["event"] == "batch-halted"
    assert final["cost_fully_settled"] is True and final["schedule_fully_observed"] is False
    terminals = {row["schedule_order"]: row for row in journal if row["event"] == "row-terminal"}
    assert list(terminals) == [1, 2]
    image = [_sealed(json.loads(line)) for line in (ROOT / IMAGE_RECEIPT).read_text().splitlines()]
    assert [row["type"] for row in image] == ["image-inspection-attempt-started", "image-admitted"]
    assert image[1]["previous_hash"] == image[0]["content_hash"]
    assert image[0]["binding"]["execution_hash"] == EXECUTION
    assert image[0]["binding"]["manifest_hashes"] == list(contract["manifest_hashes"])
    assert image[1]["inspection_adapter_calls"] == 1
    rows = []
    state_path = ROOT / ".patchloop/state.sqlite3"
    with contextlib.closing(sqlite3.connect(state_path.as_uri() + "?mode=ro", uri=True)) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        db.execute("BEGIN")
        for scheduled, capability in zip(candidate["schedule"], capabilities, strict=True):
            order = scheduled["order"]
            run_id = capability["run_id"]
            run = db.execute(
                "SELECT status, manifest_json, json_extract(result_json, '$.usage') AS usage, "
                "json_extract(result_json, '$.outcome_kind') AS outcome, "
                "json_extract(result_json, '$.agent_submission_status') AS submission, "
                "json_extract(result_json, '$.evaluation_status') AS evaluation, "
                "json_extract(result_json, '$.scope_compliant_success') AS success, "
                "json_extract(result_json, '$.terminal_error') AS terminal_error "
                "FROM runs WHERE run_id=?",
                (run_id,),
            ).fetchone()
            row = {"order": order, "run_id": run_id, "variant": scheduled["variant"]}
            if run is None:
                assert order not in terminals
                rows.append({**row, "status": "not_started"})
                continue
            manifest = json.loads(run["manifest_json"])
            assert sha256_json(manifest) == capability["manifest_hash"]
            usage = json.loads(run["usage"])
            events = [
                dict(item)
                for item in db.execute(
                    "SELECT sequence, event_id, json_extract(event_json, '$.type') AS type, "
                    "json_extract(event_json, '$.payload.tool') AS tool, "
                    "json_extract(event_json, '$.payload.check_id') AS check_id, "
                    "json_extract(event_json, '$.payload.passed') AS passed, "
                    "json_extract(event_json, '$.payload.worktree_diff_hash') AS diff_hash "
                    "FROM events WHERE run_id=? ORDER BY sequence",
                    (run_id,),
                )
            ]
            assert [item["sequence"] for item in events] == list(range(1, len(events) + 1))
            assert len({item["event_id"] for item in events}) == len(events)
            counts = Counter(item["type"] for item in events)
            assert counts["RunStarted"] == 1
            assert counts["RunCompleted"] + counts["RunFailed"] == 1
            assert events[-1]["type"] in {"RunCompleted", "RunFailed"}
            assert counts["ModelCalled"] == usage["model_calls"]
            assert counts["ToolCalled"] == usage["tool_calls"]
            cost = int(Decimal(str(usage["model_cost_usd"])) * 1_000_000_000)
            assert terminals[order]["model_cost_nanos"] == cost
            assert terminals[order]["outcome_kind"] == run["outcome"]
            reads = []
            for item in db.execute(
                "SELECT event_json FROM events WHERE run_id=? "
                "AND json_extract(event_json, '$.type')='ToolCalled' "
                "AND json_extract(event_json, '$.payload.tool')='read_file' ORDER BY sequence",
                (run_id,),
            ):
                event = RunEvent.model_validate_json(item[0])
                arguments = _tool_input(event, state_path=state_path)
                reads.append(
                    {
                        "event_sequence": event.sequence,
                        **{key: arguments.get(key) for key in ("path", "start_line", "end_line")},
                    }
                )
            rows.append(
                {
                    **row,
                    "status": run["status"],
                    "outcome_kind": run["outcome"],
                    "submission_status": run["submission"],
                    "evaluation_status": run["evaluation"],
                    "scope_compliant_success": bool(run["success"]),
                    "usage": usage,
                    "model_cost_nanos": cost,
                    "event_count": len(events),
                    "event_type_counts": dict(sorted(counts.items())),
                    "public_metadata_hash": sha256_json(events),
                    "source_reads": reads,
                    "tool_sequence": [
                        [item["sequence"], item["tool"]]
                        for item in events
                        if item["type"] == "ToolCalled"
                    ],
                    "visible_check_results": [
                        item
                        for item in events
                        if item["type"] == "ToolSucceeded" and item["tool"] == "run_check"
                    ],
                    "terminal_error": json.loads(run["terminal_error"])
                    if run["terminal_error"]
                    else None,
                    "recorded_driver_flags": {
                        key: terminals[order][key]
                        for key in (
                            "row_capability_consumed_and_dispatched",
                            "terminal_state_atomic",
                            "cost_settlement_complete",
                            "ordinary_terminal_valid",
                        )
                    },
                }
            )
    assert sum(row.get("model_cost_nanos", 0) for row in rows) == final["accrued_cost_nanos"]
    schemas = {}
    for variant, tools in (
        ("lean-harness-v25", TOOL_SCHEMAS_V26),
        ("lean-harness-v26", TOOL_SCHEMAS_V27),
    ):
        tool = next(item for item in tools if item["name"] == "read_file")
        parameters = tool["parameters"]
        schemas[variant] = {
            "strict": tool["strict"],
            "properties": list(parameters["properties"]),
            "required": parameters["required"],
            "missing_required_properties": sorted(
                set(parameters["properties"]) - set(parameters["required"])
            ),
            "static_tool_schema_hash": sha256_json(tool),
        }
    body = {
        "schema_version": "rapid-r23-halted-public-audit-v1",
        "official": False,
        "execution_hash": EXECUTION,
        "status": "consumed-halted-incomplete-comparison",
        "runtime_build_hash": candidate["runtime_build_hash"],
        "source_files": {
            "candidate": _file_record(CANDIDATE),
            "rehearsal": _file_record(REHEARSAL),
            "qualification": _file_record(
                Path(
                    "experiments/rapid-candidate-v32-v25-v26-batch-image-ab-public-qualification-20260831-v1.json"
                )
            ),
            "approved_plan": _file_record(
                Path(".patchloop/experiments/plans") / (EXECUTION.removeprefix("sha256:") + ".json")
            ),
            "bundle": _file_record(BUNDLE),
            "image_receipt": _file_record(IMAGE_RECEIPT),
        },
        "execution_observation": {
            "entry_invocations": 1,
            "scheduled_rows": 6,
            "started_rows": 2,
            "terminal_rows": 2,
            "settled_rows": 2,
            "not_started_rows": 4,
            "image_inspect_adapter_calls": 1,
            "local_image_identity_verified": True,
            "recorded_model_calls": 10,
            "recorded_input_token_count_calls": 10,
            "recorded_tool_calls": 10,
            "evaluator_reached_rows": 1,
            "submission_completed_rows": 1,
            "successful_rows": 0,
            "model_cost_nanos": final["accrued_cost_nanos"],
            "cost_fully_settled": final["cost_fully_settled"],
            "schedule_fully_observed": final["schedule_fully_observed"],
            "reserve_nanos": first["full_schedule_reserve_nanos"],
            "hard_cap_nanos": first["hard_cap_nanos"],
            "terminal_content_hash": final["content_hash"],
            "halt_reason_codes": final["reason_codes"],
        },
        "rows": rows,
        "failure_diagnosis": {
            "classification": "pre-generation-provider-strict-schema-rejection",
            "observed_http_error_code": "invalid_function_parameters",
            "observed_missing_property": "path",
            "static_read_file_schemas": schemas,
            "source_location": "patchloop/agent/tools.py:839-850",
            "stage_inference": "input-token-count-before-ContextBuilt-and-generation-dispatch",
            "stage_inference_basis": [
                "patchloop/agent/runner.py:3195-3233",
                "patchloop/agent/model.py:913-918",
                "row-2-has-no-ContextBuilt-or-ModelCalled-event",
            ],
            "failed_provider_requests_lower_bound": 1,
            "exact_http_request_count_recorded": False,
            "row_2_recorded_zero_model_calls_does_not_mean_zero_provider_requests": True,
            "failed_count_call_not_in_usage": True,
            "failed_request_body_persisted": False,
            "rehearsal_limit": (
                "manifest-image-generation-capability gates do not validate "
                "provider strict tool schemas"
            ),
            "official_contract_reference": "https://developers.openai.com/api/docs/guides/function-calling#strict-mode",
            "row_1_hidden_failure_cause": "not-attributable-from-public-evidence",
        },
        "evidence_boundary": {
            "public_metadata_and_tool_input_only": True,
            "wal_aware_read_only_sqlite": True,
            "immutable_sqlite_mode_claimed": False,
            "private_spec_read": False,
            "hidden_evaluator_content_read": False,
            "reference_patch_read": False,
            "llm_response_or_reasoning_text_read": False,
            "raw_state_mutated": False,
            "provider_calls_added_by_audit": 0,
            "docker_calls_added_by_audit": 0,
            "evaluator_calls_added_by_audit": 0,
            "cost_added_by_audit_nanos": 0,
            "complete_batch_diagnosis_synthesized": False,
        },
        "disposition": {
            "same_candidate_retry_authorized": False,
            "remaining_rows_authorized_to_resume": False,
            "v25_v26_comparison": "inconclusive-infrastructure-confounded-and-incomplete",
            "v26_promoted": False,
            "quality_or_efficiency_claim": False,
            "runtime_fix_implemented": False,
            "successor_candidate_created": False,
            "next_offline_seam": (
                "strict-compatible anchored-read schema and final-request validation "
                "before any provider token-count transport"
            ),
        },
    }
    return {**body, "content_hash": sha256_json(body)}


def test_r23_halted_audit_is_deterministic_read_only_and_matches_frozen_artifacts(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("R23 audit must not access the network")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    first = _build_audit()
    second = _build_audit()
    assert first == second
    assert (ROOT / AUDIT).read_bytes() == (canonical_json(first) + "\n").encode()


def test_r23_does_not_fake_a_complete_comparison_or_zero_provider_requests():
    audit = _sealed(json.loads((ROOT / AUDIT).read_bytes()))
    assert audit["execution_observation"]["model_cost_nanos"] == 162_854_250
    assert [row["status"] for row in audit["rows"]] == [
        "completed",
        "failed",
        "not_started",
        "not_started",
        "not_started",
        "not_started",
    ]
    assert audit["rows"][1]["usage"]["model_calls"] == 0
    assert audit["failure_diagnosis"]["failed_provider_requests_lower_bound"] == 1
    assert audit["disposition"]["same_candidate_retry_authorized"] is False
    assert audit["disposition"]["runtime_fix_implemented"] is False
    assert audit["rows"][0]["event_type_counts"]["SubmissionAccepted"] == 1
    assert len(audit["rows"][0]["visible_check_results"]) == 3


def test_r23_original_complete_batch_diagnoser_still_rejects_halted_bundle():
    with pytest.raises(ContractError, match="lacks one batch completion"):
        _load_bundle(ROOT / BUNDLE)


def test_r23_characterizes_provider_schema_rejection_without_repairing_v26():
    audit = _sealed(json.loads((ROOT / AUDIT).read_bytes()))
    schemas = audit["failure_diagnosis"]["static_read_file_schemas"]
    assert schemas["lean-harness-v25"]["missing_required_properties"] == []
    assert schemas["lean-harness-v26"]["strict"] is True
    assert schemas["lean-harness-v26"]["required"] == []
    assert "path" in schemas["lean-harness-v26"]["missing_required_properties"]
