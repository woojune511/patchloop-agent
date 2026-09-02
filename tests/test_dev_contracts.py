from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError
from typer.testing import CliRunner

from patchloop.cli import app
from patchloop.dev.contracts import DevRunRequest, MutationIntent, RequestedTool
from patchloop.dev.cost import DevCostLedger, pricing_for_model
from patchloop.dev.tools import validate_tool_batch
from patchloop.errors import ContractError
from patchloop.runtime import repository_root
from patchloop.task_loader import load_task_package


def call(name: str, index: int = 0) -> RequestedTool:
    return RequestedTool(name=name, action_id=f"a-{index}", arguments={})


def test_tool_batch_contract_is_small_and_unmixed() -> None:
    assert validate_tool_batch([call("read_file"), call("search_files", 1)]) == "parallel_read"
    assert validate_tool_batch([call("run_check")]) == "single_action"
    with pytest.raises(ContractError):
        validate_tool_batch([call("read_file"), call("run_check", 1)])
    with pytest.raises(ContractError):
        validate_tool_batch([call("read_file", item) for item in range(5)])
    with pytest.raises(ContractError):
        validate_tool_batch([call("read_file"), call("search_files")])


def test_mutation_contract_requires_minimal_plan_and_pairs_alternative() -> None:
    base = {
        "hypothesis": "state is reset too early",
        "expected_behavior": "state survives through cleanup",
        "evidence_span_ids": ["span_a"],
        "edit_anchor": {"path": "src/a.py", "old_text": "old", "occurrence": 1},
    }
    assert MutationIntent.model_validate(base).alternative_mechanism is None
    with pytest.raises(ValidationError):
        MutationIntent.model_validate({**base, "alternative_mechanism": "different owner"})
    with pytest.raises(ValidationError):
        MutationIntent.model_validate(
            {key: value for key, value in base.items() if key != "hypothesis"}
        )


def test_cost_cap_is_checked_before_dispatch_and_can_lower_output_ceiling() -> None:
    pricing = pricing_for_model("gpt-5.4-mini-2026-03-17")
    assert DevCostLedger(Decimal("0.001"), pricing).admit(1_000) is None
    ledger = DevCostLedger(Decimal("0.01"), pricing)
    admission = ledger.admit(1_000)
    assert admission is not None
    assert 128 <= admission.output_ceiling < 4_096
    cost = ledger.settle(input_tokens=1_000, cached_input_tokens=0, output_tokens=100)
    assert 0 < cost <= ledger.cap_nanos

    restored = DevCostLedger(Decimal("0.01"), pricing)
    restored.restore_settled_usage(
        [{"call_id": "call-resumed", "cost_nanos": cost}],
        base_spent_nanos=123,
    )
    assert restored.spent_nanos == 123 + cost


def test_provider_options_fail_closed() -> None:
    task = Path("tasks/smoke/csv-quoted-newline/public.yaml")
    with pytest.raises(ValidationError):
        DevRunRequest(
            provider="openai",
            task=task,
            model="gpt-5.4-mini",
            max_cost_usd=Decimal("1"),
        )
    with pytest.raises(ValidationError):
        DevRunRequest(
            provider="openai",
            task=task,
            model="gpt-5.4-mini",
            env_file=Path("credential.env"),
        )
    with pytest.raises(ValidationError):
        DevRunRequest(
            provider="openai",
            task=task,
            model="gpt-5.4-mini",
            env_file=Path("credential.env"),
            max_cost_usd=Decimal("0"),
        )
    with pytest.raises(ValidationError):
        DevRunRequest(
            provider="mock",
            task=task,
            model="mock-dev",
            max_cost_usd=Decimal("1"),
        )
    with pytest.raises(ValidationError):
        DevRunRequest(provider="mock", task=task, model="mock-dev", repeat=7)
    with pytest.raises(ValidationError, match="--repeat 1"):
        DevRunRequest(
            provider="mock",
            task=task,
            model="mock-dev",
            repeat=2,
            resume_run_id="run_dev_existing0001",
        )


def test_cli_exposes_only_dev_doctor_and_task_commands() -> None:
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "dev" in result.stdout
    assert "rapid" not in result.stdout
    assert "evaluate" not in result.stdout
    assert "resume" not in result.stdout

    dev_help = CliRunner().invoke(
        app,
        [
            "dev",
            "--provider",
            "mock",
            "--task",
            "tasks/smoke/csv-quoted-newline/public.yaml",
            "--model",
            "mock-dev",
            "--help",
        ],
    )
    assert dev_help.exit_code == 0
    assert "--resume-run-id" in dev_help.stdout


@pytest.mark.parametrize(
    ("relative_path", "public_hash", "private_hash"),
    [
        (
            "smoke/csv-quoted-newline",
            "sha256:e396266522131f4aabfaae3fd140e33c60eaab17dfdd7bca18be03be3a93e04d",
            "sha256:c2174e536111cec56d29ad59bb0d547bd38febfff156bb7ca63cdc42c7ef65be",
        ),
        (
            "dev-train/duration-minute-boundary",
            "sha256:bcd131c3449e9d9b8c193847a3bced62e75934bd53ed49747f3847abec1f5a6b",
            "sha256:27b0045d5b3c8e0a303f24115e75a8b49cf840750091905994a6f08dd4b148bc",
        ),
        (
            "cross-repo-heldout/kubeflow-exit-handler-after-dependencies",
            "sha256:dfaa69083d119046f78f532a99db3cf9eb0ca2a4b34ca73f70f62242a22d5f8c",
            "sha256:bc8c6e70c15d926e24c6b7fcbcdf471b5577704ea9e46fea4f93cf47a4955798",
        ),
    ],
)
def test_task_identity_hashes_survive_reset(
    relative_path: str,
    public_hash: str,
    private_hash: str,
) -> None:
    package = load_task_package(repository_root() / "tasks" / relative_path)
    assert package.public_spec_hash == public_hash
    assert package.private_spec_hash == private_hash
