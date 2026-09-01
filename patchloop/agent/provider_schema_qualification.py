"""Zero-call qualification for the opt-in R23 strict-schema repair.

Only synthetic public schemas/receipts and frozen file identities are inputs.
This is not provider acceptance, a rehearsal, a candidate or an agent result.
"""

from __future__ import annotations

import copy
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from patchloop.agent.provider_count_accounting import (
    ProviderInputTokenCountError,
    ProviderInputTokenCountUncertainError,
    counted_request_with_receipts,
    project_input_token_count_attempts,
)
from patchloop.agent.provider_schema_admission import (
    PROVIDER_SCHEMA_POLICY,
    STRICT_ANCHORED_READ_POLICY,
    ProviderToolSchemaError,
    normalize_strict_read_arguments,
    validate_provider_tool_schemas,
)
from patchloop.agent.tools import TOOL_SCHEMAS_V27, TOOL_SCHEMAS_V28
from patchloop.agent.workflow_plan_contract_compatibility_successor import (
    project_trigger_bound_self_directed_plan_request,
)
from patchloop.agent.workflow_r21_reliability_successor import project_lifecycle_bound_plan_request
from patchloop.agent.workflow_self_directed_exploration_successor_qualification import (
    _catalog_v4,
    _request,
)
from patchloop.contracts import RunEvent
from patchloop.errors import ContractError, RecoveryError
from patchloop.util import canonical_json, ensure_within, sha256_bytes, sha256_json

QUALIFICATION_PATH = Path(
    "experiments/lean-harness-provider-schema-public-qualification-20260831-v1.json"
)
DELTA_PATH = Path("experiments/lean-v27-r23-predecessor-source-delta-20260831-v1.json")
R23_QUALIFICATION_PATH = (
    "experiments/rapid-candidate-v32-v25-v26-batch-image-ab-public-qualification-20260831-v1.json"
)
R23_QUALIFICATION_HASH = "sha256:47fb1e97d41f52157740b759a8445d3924192a1ac2c6ea6e4bee7800533b6508"
R23_AUDIT_PATH = (
    "reports/rapid-development/artifacts/rapid-public-dev-anyio-v5-batch-image-ab-20260831-r23-"
    "candidate-v32-halted-public-audit-v1.json"
)
R23_AUDIT_HASH = "sha256:bde94484fe8ad47482a9e648ff5d9ee78fbdc487bd8251c2cf287a7c78969982"
SOURCE_FILES = (
    "patchloop/agent/provider_schema_admission.py",
    "patchloop/agent/provider_schema_adapter.py",
    "patchloop/agent/provider_count_accounting.py",
    "patchloop/agent/provider_schema_qualification.py",
    "patchloop/agent/lean_runtime.py",
    "patchloop/agent/runner.py",
    "patchloop/agent/tools.py",
    "patchloop/agent/investigation.py",
    "patchloop/agent/model.py",
    "patchloop/contracts.py",
    "tests/test_provider_schema_admission.py",
    "tests/test_provider_schema_runner.py",
    "tests/test_provider_count_accounting.py",
    "tests/test_provider_schema_qualification.py",
    "scripts/build_lean_harness_provider_schema_qualification.py",
)


def _identity(root: Path, relative: str) -> dict[str, Any]:
    path = ensure_within(root, relative)
    if not path.is_file():
        raise ContractError(f"provider schema qualification input is unavailable: {relative}")
    raw = path.read_bytes()
    return {"path": relative, "bytes": len(raw), "file_sha256": sha256_bytes(raw)}


def _document(root: Path, relative: str, expected_hash: str | None = None) -> dict[str, Any]:
    path = ensure_within(root, relative)
    raw = path.read_bytes()
    if expected_hash is not None and sha256_bytes(raw) != expected_hash:
        raise ContractError(f"frozen provider-schema input changed: {relative}")
    value = json.loads(raw)
    if value.get("content_hash") != sha256_json(
        {k: v for k, v in value.items() if k != "content_hash"}
    ):
        raise ContractError(f"provider-schema input content hash differs: {relative}")
    return value


def predecessor_source_proof(root: Path) -> dict[str, Any]:
    """Recover exact predecessor bytes in memory; never rebuild a consumed candidate."""
    frozen = _document(root, R23_QUALIFICATION_PATH, R23_QUALIFICATION_HASH)
    audit = _document(root, R23_AUDIT_PATH, R23_AUDIT_HASH)
    delta = _document(root, DELTA_PATH.as_posix())
    if (
        delta.get("schema_version") != "lean-v27-predecessor-source-delta-v1"
        or delta.get("predecessor_qualification_file_sha256") != R23_QUALIFICATION_HASH
        or delta.get("historical_artifacts_modified") is not False
    ):
        raise ContractError("provider schema predecessor delta identity differs")
    patches = delta.get("source_deltas")
    expected_changed = {
        "patchloop/agent/lean_runtime.py",
        "patchloop/agent/runner.py",
        "patchloop/agent/tools.py",
        "patchloop/agent/investigation.py",
        "patchloop/contracts.py",
    }
    if (
        not isinstance(patches, list)
        or len(patches) != len(expected_changed)
        or {p.get("path") for p in patches} != expected_changed
    ):
        raise ContractError("provider schema delta source inventory differs")
    patch_map = {p["path"]: p for p in patches}
    frozen_sources = {
        row["path"]: row
        for row in (
            frozen["source_files"] + frozen["reviewed_package_binding"]["current_source_binding"]
        )
    }
    proven = []
    for relative, descriptor in sorted(frozen_sources.items()):
        current = ensure_within(root, relative).read_bytes()
        restored = current
        patch = patch_map.get(relative)
        if patch is not None:
            if patch.get("successor_file_sha256") != sha256_bytes(current):
                raise RecoveryError("successor source differs from its exact reverse delta")
            text = current.decode("utf-8")
            pieces = []
            cursor = 0
            for change in patch["replacements"]:
                start, end = change["start"], change["end"]
                if (
                    type(start) is not int
                    or type(end) is not int
                    or not cursor <= start <= end <= len(text)
                    or text[start:end] != change["successor_text"]
                    or not isinstance(change["predecessor_text"], str)
                ):
                    raise RecoveryError("predecessor source reverse delta differs")
                pieces.extend((text[cursor:start], change["predecessor_text"]))
                cursor = end
            pieces.append(text[cursor:])
            restored = "".join(pieces).encode("utf-8")
        if (
            len(restored) != descriptor["bytes"]
            or sha256_bytes(restored) != descriptor["file_sha256"]
        ):
            raise RecoveryError(f"predecessor source bytes were not recovered: {relative}")
        proven.append(
            {
                "path": relative,
                "predecessor_file_sha256": descriptor["file_sha256"],
                "current_file_sha256": sha256_bytes(current),
                "reverse_delta_used": patch is not None,
                "predecessor_bytes_recovered": True,
            }
        )
    immutable = []
    for row in audit["source_files"].values():
        actual = _identity(root, row["path"])
        if actual != row:
            raise RecoveryError("consumed R23 artifact differs")
        immutable.append(actual)
    # The reviewed standalone predecessor and its qualification/review artifacts
    # remain directly byte-identical, unlike the additive shared source files.
    for key in ("qualification", "activation_review"):
        row = frozen["reviewed_package_binding"][key]
        actual = _identity(root, row["path"])
        if any(actual[k] != row[k] for k in actual):
            raise RecoveryError("consumed V26 qualification or review differs")
        immutable.append(actual)
    return {
        "delta_identity": _identity(root, DELTA_PATH.as_posix()),
        "source_proof": proven,
        "immutable_artifacts": immutable,
        "r23_audit": _identity(root, R23_AUDIT_PATH),
        "consumed_candidate_rebuilt": False,
        "historical_artifacts_modified": False,
    }


class _SyntheticCountState:
    """In-memory events only. No StateStore, run, SDK or container is created."""

    def __init__(self) -> None:
        self.events: list[RunEvent] = []

    def list_events(self, run_id: str) -> list[RunEvent]:
        return list(self.events)

    def append_event(self, run_id: str, kind: Any, **kwargs: Any) -> RunEvent:
        event = RunEvent(
            event_id=f"evt_synthetic_count_{len(self.events) + 1}",
            run_id=run_id,
            sequence=len(self.events) + 1,
            type=kind,
            timestamp=datetime(2026, 8, 31, tzinfo=UTC),
            **kwargs,
        )
        self.events.append(event)
        return event


def count_scenarios() -> dict[str, Any]:
    values = {}
    for scenario in ("completed", "failed", "outcome_unknown", "schema_blocked"):
        state = _SyntheticCountState()
        request = {"tools": copy.deepcopy(TOOL_SCHEMAS_V28)}
        if scenario == "schema_blocked":
            request["tools"][0]["parameters"]["required"] = []
        callbacks = []

        def fake_count(_body: dict, *, mode=scenario, observed=callbacks) -> int:
            observed.append(mode)
            if mode == "failed":
                raise RuntimeError("synthetic count failure")
            if mode == "outcome_unknown":
                raise SystemExit(89)
            return 123

        try:
            counted_request_with_receipts(
                state=state,
                run_id="run_v27_synthetic_count",
                request=request,
                count=fake_count,
                monotonic=lambda: 1.0,
            )
        except (ProviderInputTokenCountError, ProviderToolSchemaError, SystemExit):
            if scenario == "completed":
                raise
        retry_blocked = None
        if scenario in {"failed", "outcome_unknown"}:
            retry_blocked = False
            try:
                counted_request_with_receipts(
                    state=state,
                    run_id="run_v27_synthetic_count",
                    request=request,
                    count=fake_count,
                    monotonic=lambda: 1.0,
                )
            except (ProviderInputTokenCountError, ProviderInputTokenCountUncertainError):
                retry_blocked = True
        summary = project_input_token_count_attempts("run_v27_synthetic_count", state.events)
        if (
            summary["logical_attempts"] != int(scenario != "schema_blocked")
            or summary["completed"] != int(scenario == "completed")
            or summary["failed"] != int(scenario == "failed")
            or summary["outcome_unknown"] != int(scenario == "outcome_unknown")
            or len(callbacks) != int(scenario != "schema_blocked")
            or retry_blocked is False
        ):
            raise ContractError("synthetic count qualification failed")
        values[scenario] = {"summary": summary, "automatic_retry_blocked": retry_blocked}
    return values


def schema_scenarios() -> dict[str, Any]:
    tools = copy.deepcopy(TOOL_SCHEMAS_V28)
    static = validate_provider_tool_schemas({"tools": tools})
    old_read = next(t for t in TOOL_SCHEMAS_V27 if t["name"] == "read_file")
    try:
        validate_provider_tool_schemas({"tools": [old_read]})
    except ProviderToolSchemaError as exc:
        old_reason = exc.details["reason_code"]
    else:
        raise ContractError("R23 invalid predecessor was not reproduced")
    catalog = _catalog_v4(source_count=2)
    source = _request(catalog)
    trigger = project_trigger_bound_self_directed_plan_request(source.source_request.base_request)
    plan = project_lifecycle_bound_plan_request(trigger)
    plan_schema = copy.deepcopy(next(t for t in tools if t["name"] == "record_work_plan"))
    plan_schema["parameters"] = copy.deepcopy(plan.parameters)
    dynamic = validate_provider_tool_schemas({"tools": [plan_schema]})
    direct = {"path": "src/example.py", "start_line": 5, "end_line": 12, "search_anchor": None}
    anchor = {"search_event_sequence": 7, "match_index": 1, "before_lines": 8, "after_lines": 12}
    anchored = {"path": None, "start_line": None, "end_line": None, "search_anchor": anchor}
    rejected = 0
    for arguments in ({}, {**direct, "search_anchor": anchor}, {**anchored, "search_anchor": None}):
        try:
            normalize_strict_read_arguments(arguments)
        except ContractError:
            rejected += 1
    if rejected != 3 or old_reason != "required_property_mismatch":
        raise ContractError("strict anchored-read qualification failed")
    return {
        "static_surface": static,
        "production_projected_synthetic_initial_plan": dynamic,
        "predecessor_read_schema_hash": sha256_json(old_read),
        "predecessor_rejection": old_reason,
        "normalized_direct": normalize_strict_read_arguments(direct),
        "normalized_anchor": normalize_strict_read_arguments(anchored),
        "ambiguous_or_missing_modes_rejected": rejected,
        "read_policy_version": STRICT_ANCHORED_READ_POLICY,
        "provider_schema_policy_version": PROVIDER_SCHEMA_POLICY,
    }


def build_qualification(repository: str | Path = ".") -> dict[str, Any]:
    root = Path(repository).resolve()
    body = {
        "schema_version": "lean-provider-schema-qualification-v1",
        "generated_at": "2026-08-31T00:00:00+00:00",
        "status": "offline-qualified",
        "runtime_identity": {
            "runtime_policy_version": "lean-harness-v27",
            "tool_schema_version": "v28",
            "context_policy_version": "phase-evidence-v37",
            "request_evidence_schema": "lean-harness-request-evidence-v27",
        },
        "schema_scenarios": schema_scenarios(),
        "synthetic_count_scenarios": count_scenarios(),
        "predecessor_preservation": predecessor_source_proof(root),
        "source_files": [_identity(root, path) for path in SOURCE_FILES],
        "validation_limits": [
            "Schemas/receipts are synthetic public fixtures, not live provider acceptance.",
            "Runner E2E, correction/review and crash tests are separate source-bound tests.",
            "The builder never rebuilds or rehearses a consumed candidate.",
            "Local admission covers the emitted subset, not every vendor JSON Schema feature.",
            "Logical count attempts are not exact HTTP totals or observed billing.",
        ],
        "evidence_boundary": {
            "provider_calls": 0,
            "docker_calls": 0,
            "evaluator_calls": 0,
            "visible_check_calls": 0,
            "network_calls": 0,
            "added_cost_usd": "0",
            "raw_reasoning_read": False,
            "private_task_spec_read": False,
            "hidden_evaluator_content_read": False,
            "reference_patch_read": False,
        },
        "candidate_created": False,
        "rehearsal_created": False,
        "external_calls": 0,
        "paid_execution_authorized": False,
        "provider_acceptance_observed": False,
        "quality_improvement_established": False,
        "next_gate": "separate-lean-v27-activation-review",
    }
    return {**body, "content_hash": sha256_json(body)}


def qualification_bytes(value: dict[str, Any]) -> bytes:
    if value.get("content_hash") != sha256_json(
        {k: v for k, v in value.items() if k != "content_hash"}
    ):
        raise ContractError("provider schema qualification hash differs")
    return (canonical_json(value) + "\n").encode("utf-8")


def materialize_qualification(repository: str | Path = ".") -> dict[str, Any]:
    root = Path(repository).resolve()
    value = build_qualification(root)
    raw = qualification_bytes(value)
    path = ensure_within(root, QUALIFICATION_PATH.as_posix())
    if path.exists():
        if path.read_bytes() != raw:
            raise ContractError(
                "existing qualification differs; never overwrite historical evidence"
            )
    else:
        with path.open("xb") as stream:
            stream.write(raw)
    return value
