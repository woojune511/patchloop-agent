from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from patchloop.agent.tools import TOOL_SCHEMAS_V2
from patchloop.evals.evaluator_v2_source_qualification import (
    evaluator_v2_task_private_markers,
)
from patchloop.evals.heldout_ac_task_evaluator import (
    load_heldout_ac_task_evaluator_plan,
)
from patchloop.evals.heldout_ac_task_pricing_materialization import (
    OUTPUT_PATH,
    R5_PLAN_HASH,
    HeldoutACTaskPricingMaterialization,
    HeldoutACTaskPricingMaterializationError,
    _build_candidate,
    _contract_template_hash,
    _materialize_task_template,
    run_heldout_ac_task_pricing_materialization,
    validate_heldout_ac_task_pricing_materialization,
)
from patchloop.task_loader import load_task_package
from patchloop.util import sha256_bytes, sha256_json
from patchloop.verifier.runtime_evidence import build_evaluator_safety_contract_v2

ROOT = Path(__file__).resolve().parents[1]
HISTORICAL_PRICING = (
    ROOT / "reports/live-pilot/artifacts/d136-replayable-official-pricing-evidence.json"
)


def _pricing_capture() -> dict[str, object]:
    payload = json.loads(HISTORICAL_PRICING.read_bytes())
    return payload["semantic_body"]["observation"]


def _candidate() -> HeldoutACTaskPricingMaterialization:
    return _build_candidate(
        ROOT,
        recorded_at=datetime(2026, 8, 14, 12, 0, tzinfo=UTC),
        pricing_capture=_pricing_capture(),
    )


def test_offline_candidate_materializes_exact_12_templates_and_pricing() -> None:
    candidate = _candidate()

    assert len(candidate.task_bindings) == 12
    assert len({item.task.task_id for item in candidate.task_bindings}) == 12
    assert sum(item.task.role == "core-same-repo" for item in candidate.task_bindings) == 6
    assert sum(item.task.role == "core-cross-repo" for item in candidate.task_bindings) == 6
    assert candidate.task_evaluator_plan_content_hash == R5_PLAN_HASH
    assert all(item.task_private_marker_count > 0 for item in candidate.task_bindings)
    assert all(item.runtime_secret_markers_materialized == 0 for item in candidate.task_bindings)
    assert all(
        item.final_evaluator_contract_materialized is False for item in candidate.task_bindings
    )
    assert candidate.pricing.price_nanos_per_token == {
        "uncached_input": 750,
        "cached_input": 75,
        "cache_write_input": 750,
        "output": 4_500,
    }
    assert candidate.pricing.per_run_reserve_nanos == 5_250_000_000
    assert candidate.pricing.full_schedule_reserve_nanos == 252_000_000_000
    assert candidate.pricing.hard_cap_nanos == 275_000_000_000
    assert candidate.authority.provider_calls_made == 0
    assert candidate.authority.execution_candidate_authorized is False


def test_materialized_record_serializes_no_private_marker_value() -> None:
    candidate = _candidate()
    serialized = candidate.model_dump_json()
    plan = load_heldout_ac_task_evaluator_plan(repository=ROOT)

    for selected in plan.tasks:
        package = load_task_package(ROOT / selected.task_path)
        for marker in evaluator_v2_task_private_markers(package):
            assert marker.decode("utf-8") not in serialized


def test_template_hash_is_invariant_to_future_run_secret_expansion() -> None:
    plan = load_heldout_ac_task_evaluator_plan(repository=ROOT)
    selected = plan.tasks[0]
    package = load_task_package(ROOT / selected.task_path)
    template = _materialize_task_template(root=ROOT, plan=plan, expected=selected)
    private_markers = evaluator_v2_task_private_markers(package)
    expanded = build_evaluator_safety_contract_v2(
        package=package,
        tool_schemas=TOOL_SCHEMAS_V2,
        private_markers=tuple(sorted((*private_markers, b"future-runtime-secret-marker"))),
        contract_id=f"heldout_ac_evaluator_v2_{selected.task_id.replace('-', '_')}",
    )

    assert expanded.content_hash != template.baseline_private_contract_hash
    assert (
        _contract_template_hash(expanded) == template.run_secret_independent_contract_template_hash
    )


def test_rehashed_pricing_or_task_projection_drift_fails_closed() -> None:
    candidate = _candidate()
    pricing_drift = candidate.model_dump(mode="json")
    pricing_drift["pricing"]["full_schedule_reserve_nanos"] += 1
    pricing_body = {
        key: value for key, value in pricing_drift["pricing"].items() if key != "content_hash"
    }
    pricing_drift["pricing"]["content_hash"] = sha256_json(pricing_body)
    pricing_drift["content_hash"] = sha256_json(
        {key: value for key, value in pricing_drift.items() if key != "content_hash"}
    )

    with pytest.raises(ValidationError):
        HeldoutACTaskPricingMaterialization.model_validate_json(json.dumps(pricing_drift))

    task_drift = candidate.model_dump(mode="json")
    task_drift["task_bindings"][0]["runtime_secret_markers_materialized"] = 1
    task_drift["task_bindings"][0]["content_hash"] = sha256_json(
        {
            key: value
            for key, value in task_drift["task_bindings"][0].items()
            if key != "content_hash"
        }
    )
    task_drift["task_bindings_hash"] = sha256_json(task_drift["task_bindings"])
    task_drift["content_hash"] = sha256_json(
        {key: value for key, value in task_drift.items() if key != "content_hash"}
    )

    with pytest.raises(ValidationError):
        HeldoutACTaskPricingMaterialization.model_validate_json(json.dumps(task_drift))


def test_checked_in_materialization_is_preserved_and_rejects_current_source_replay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selected = ROOT / OUTPUT_PATH
    raw = selected.read_bytes()
    assert len(raw) == 51_018
    assert sha256_bytes(raw) == (
        "sha256:cdd971a57f6f20661d8de326f5603ee1d90eca4234633a8a09d65560d7d52641"
    )

    def unexpected_capture() -> dict[str, object]:
        raise AssertionError("existing materialization must not refresh pricing")

    monkeypatch.setattr(
        "patchloop.evals.heldout_ac_task_pricing_materialization.capture_official_pricing_evidence",
        unexpected_capture,
    )
    with pytest.raises(
        HeldoutACTaskPricingMaterializationError,
        match="has drifted",
    ):
        validate_heldout_ac_task_pricing_materialization(repository=ROOT)
    with pytest.raises(
        HeldoutACTaskPricingMaterializationError,
        match="has drifted",
    ):
        run_heldout_ac_task_pricing_materialization(repository=ROOT)
    assert selected.read_bytes() == raw
