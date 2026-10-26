"""Independent correction ceilings, without provider or sandbox execution."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError
from typer.testing import CliRunner

from patchloop.cli import app
from patchloop.dev import cost, runner, segments
from patchloop.dev.contracts import DevLimits, DevRunEnvelope, DevRunRequest

POLICY = cost.COMPLETION_RECOVERY_POLICY
CURRENT_CONTRACT = {
    "policy": POLICY,
    "future_input_tokens": segments.MAX_INPUT_TOKENS,
    "future_output_tokens": 128,
    "pricing": "uncached-input-and-minimum-output",
    "horizon": "minimum-success-path-and-one-protocol-correction-v1",
    "reservation": "minimum-successor-plus-correction-and-finalization-v2",
    "finalization_output_tokens": 8_192,
    "finalization_ceiling": "min-floor-and-invocation-normal-output-ceiling",
    "finalization_release": "exact-counted-ready-request-no-successor",
    "correction_credits_per_run": 1,
    "correction_output_tokens": "invocation-max-output-tokens",
    "correction_consumption": "first-durable-protocol-correction-never-renewed",
    "correction_model_calls": 1,
    "correction_tool_actions": 0,
    "release": "first-protocol-correction-or-terminal",
    "limit": "One protocol correction receives the requested output ceiling; valid "
    "response and task success are not guaranteed. Tool failures and unknown billing "
    "are not covered. One finalization successor retains a bounded output floor; "
    "other successors retain minimum output admission only.",
}


def request_data(**changes):
    return {
        "provider": "mock", "task": Path("public.json"), "model": "mock-dev",
        "context_policy": segments.POLICY, "completion_cost_policy": POLICY,
        **changes,
    }


def envelope_data(**changes):
    digest = "sha256:" + "a" * 64
    return {
        "run_id": "run_dev_correction", "provider": "mock",
        "task_path": "public.json", "task_id": "fixture", "task_version": 1,
        "base_commit": "a" * 40, "public_spec_hash": digest, "private_spec_hash": digest,
        "task_content_hash": digest, "runtime_hash": digest, "model_hash": digest,
        "sandbox_identity_hash": digest, "model": "mock-dev", "reasoning_effort": "medium",
        "max_cost_nanos": 0, "cost_start_nanos": 0, "limits": DevLimits(),
        "sandbox_backend": "local", "created_at": datetime(2026, 10, 25, tzinfo=UTC),
        "split": "dev-train", "context_policy": segments.POLICY,
        "segment_contract": segments.contract(), "completion_cost_policy": POLICY,
        "completion_cost_contract": dict(CURRENT_CONTRACT),
        **changes,
    }


def test_omitted_correction_allowance_preserves_coupled_ceiling_and_wire_shape():
    assert cost.completion_cost_contract(POLICY) == CURRENT_CONTRACT
    assert cost.completion_cost_contract(
        POLICY, max_correction_output_tokens=None,
    ) == CURRENT_CONTRACT
    for model, data in [(DevRunRequest, request_data()), (DevRunEnvelope, envelope_data())]:
        original = model.model_validate(data).model_dump(mode="json")
        explicit_none = model.model_validate({**data, "max_correction_output_tokens": None})
        assert explicit_none.model_dump(mode="json") == original
        assert "max_correction_output_tokens" not in original
        assert "max_output_tokens" not in original
    assert cost.correction_output_ceiling(40_000) == 40_000


@pytest.mark.parametrize("normal,correction", [(40_000, 25_000), (8_000, 25_000), (128, 128_000)])
def test_explicit_allowance_is_independent_and_bound_into_the_envelope(normal, correction):
    contract = cost.completion_cost_contract(POLICY, max_correction_output_tokens=correction)
    assert contract == {**CURRENT_CONTRACT, "correction_output_tokens": correction}
    values = {"max_output_tokens": normal, "max_correction_output_tokens": correction}
    request = DevRunRequest.model_validate(request_data(**values))
    envelope = DevRunEnvelope.model_validate(envelope_data(
        **values, completion_cost_contract=contract,
    ))
    assert request.max_output_tokens == envelope.max_output_tokens == normal
    assert cost.correction_output_ceiling(normal, correction) == correction
    wire = envelope.model_dump(mode="json")
    assert wire["max_correction_output_tokens"] == correction
    assert DevRunEnvelope.model_validate(wire) == envelope
    for changed in [{"max_correction_output_tokens": None},
                    {"completion_cost_contract": CURRENT_CONTRACT},
                    {"completion_cost_contract": {**contract, "correction_output_tokens": 256}}]:
        with pytest.raises(ValidationError, match="exact contract"):
            DevRunEnvelope.model_validate({**wire, **changed})


@pytest.mark.parametrize("value", [127, 128_001, True, "25000", 25_000.0])
def test_invalid_allowances_are_rejected_strictly(value):
    for model, data in [(DevRunRequest, request_data()), (DevRunEnvelope, envelope_data())]:
        with pytest.raises(ValidationError, match="max_correction_output_tokens"):
            model.model_validate({**data, "max_correction_output_tokens": value})
    with pytest.raises(ValueError, match="integer from 128 to 128000"):
        cost.completion_cost_contract(POLICY, max_correction_output_tokens=value)


@pytest.mark.parametrize("policy", [cost.DEFAULT_COMPLETION_COST_POLICY,
                                   cost.COMPLETION_RESERVE_POLICY, cost.COMPLETION_MINIMUM_POLICY])
def test_explicit_allowance_requires_recovery_policy(policy):
    for model, data in [(DevRunRequest, request_data()), (DevRunEnvelope, envelope_data())]:
        with pytest.raises(ValidationError, match="requires.*completion-recovery-v1"):
            model.model_validate({**data, "completion_cost_policy": policy,
                                  "max_correction_output_tokens": 25_000})
    with pytest.raises(ValueError, match="requires completion-recovery-v1"):
        cost.completion_cost_contract(policy, max_correction_output_tokens=25_000)


def test_independent_reservation_keeps_the_invocation_cap_and_full_correction_minimum():
    ledger = cost.DevCostLedger(Decimal("1.20"), cost.pricing_for_model("gpt-5.4-mini"))
    ledger.spent_nanos = 869_725_350
    coupled = ledger.future_call_reservation_nanos(output_ceiling=40_000)
    independent = ledger.future_call_reservation_nanos(
        output_ceiling=cost.correction_output_ceiling(40_000, 25_000),
    )
    minimum = ledger.future_call_reservation_nanos()
    assert coupled == 225_000_000 and independent == 157_500_000
    assert (ledger.remaining_nanos - coupled) // minimum == 2
    assert (ledger.remaining_nanos - independent) // minimum == 3
    correction = ledger.admit(60_000, desired_output_ceiling=25_000, minimum_output_ceiling=25_000,
                              future_cost_reserve_nanos=3 * minimum)
    assert correction is not None and correction.output_ceiling == 25_000
    assert ledger.spent_nanos + correction.reserved_cost_nanos + 3 * minimum <= ledger.cap_nanos
    ledger.cap_nanos = ledger.spent_nanos + independent - 1
    assert ledger.admit(60_000, desired_output_ceiling=25_000,
                        minimum_output_ceiling=25_000) is None


def test_cli_passes_independent_allowance_and_rejects_invalid_options(tmp_path, monkeypatch):
    task = tmp_path / "public.json"
    task.write_text("{}", encoding="utf-8")
    captures = []
    monkeypatch.setattr(runner, "run_dev", lambda request: captures.append(request) or {})
    arguments = ["dev", "--provider", "mock", "--task", str(task), "--model", "mock-dev",
                 "--context-policy", "segmented-v1", "--max-output-tokens", "40000"]
    valid = [*arguments, "--completion-cost-policy", POLICY,
             "--max-correction-output-tokens", "25000"]
    result = CliRunner().invoke(app, valid)
    assert result.exit_code == 0, result.output
    assert len(captures) == 1
    assert captures[0].max_output_tokens == 40_000
    assert captures[0].max_correction_output_tokens == 25_000
    for invalid in [[*valid[:-1], "127"], [*valid[:-1], "128001"], [*valid[:-1], "25000.0"],
                    [*arguments, "--max-correction-output-tokens", "25000"]]:
        rejected = CliRunner().invoke(app, invalid)
        assert rejected.exit_code != 0, rejected.output
    assert len(captures) == 1
