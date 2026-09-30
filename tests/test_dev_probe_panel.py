"""Provider-free admission and control-arm tests; no task-quality claims."""

from decimal import Decimal

import httpx
import pytest
from test_dev_planning import request as mock_request
from test_dev_probe_cases import call, scripted_cases, setup_gateway
from test_dev_runner import _live_request, _patch_live_boundaries

from patchloop.dev import panel, runner
from patchloop.dev import probe_cases as cases
from patchloop.dev.contracts import dev_tool_surface_hash
from patchloop.dev.cost import DevCostLedger, pricing_for_model
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import dev_tool_schemas
from patchloop.errors import ContractError, ResumeContractMismatch


@pytest.fixture(autouse=True)
def no_provider_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("panel validation must not send provider requests")
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbidden)


def test_control_schema_and_hashes_isolate_reference_free_registration(tmp_path):
    schemas = {p: dev_tool_schemas(finish_enabled=True, allowed_tools=["run_probe"], probe_policy=p)
               for p in cases.POLICIES}
    a = next(t for t in schemas[cases.REFERENCE_POLICY] if t["name"] == "run_probe")
    b = next(t for t in schemas[cases.POLICY] if t["name"] == "run_probe")
    assert "save_program" not in str(a)
    assert "save_program" in b["parameters"]["required"]
    for key in ("case_id", "reference_action_id", "question", "python_source"):
        assert a["parameters"]["properties"][key] == b["parameters"]["properties"][key]
    assert [t for t in schemas[cases.REFERENCE_POLICY] if t["name"] != "run_probe"] == [
        t for t in schemas[cases.POLICY] if t["name"] != "run_probe"]
    assert len({dev_tool_surface_hash(probe_policy=p) for p in ["none", *cases.POLICIES]}) == 3
    assert len({runner._model_hash(mock_request(tmp_path, "none").model_copy(update={
        "enable_probes": True, "probe_policy": p}), None) for p in cases.POLICIES}) == 2


@pytest.mark.parametrize("save", [True, False])
def test_control_rejects_unadvertised_field_before_dispatch(gateway_factory, save):
    gateway, journal, _, backend = setup_gateway(gateway_factory)
    gateway.probe_policy = cases.REFERENCE_POLICY
    result = gateway.execute(call(reference=None, save=save))
    assert result.status == "failed"
    assert backend.calls == 0 and not cases.saved_cases(journal.events())


def test_control_rejects_reference_free_replay(gateway_factory):
    gateway, journal, _, backend = setup_gateway(gateway_factory)
    saved = gateway.execute(call(reference=None, save=True))
    replay = call("replay", case_id=saved.output["case_comparison"]["case_id"])
    del replay.arguments["save_program"]
    gateway.probe_policy = cases.REFERENCE_POLICY
    assert gateway.execute(replay).status == "failed"
    assert backend.calls == 1


def test_panel_both_arms_reach_mock_evaluation_and_bind_resume(tmp_path, monkeypatch):
    backend = scripted_cases(monkeypatch)
    base = mock_request(tmp_path, "none")
    requests = [base.model_copy(update={"enable_probes": True, "probe_policy": p})
                for p in [cases.REFERENCE_POLICY, cases.POLICY]]
    root = tmp_path / "panel"
    result = panel.run_panel(requests, max_cost_usd=Decimal(12), state_root=root)
    assert result["cost_nanos"] == 0
    assert backend.calls == 6  # Reference, candidate, exact replay in each fresh row.
    for i, row in enumerate(result["rows"]):
        assert row["result"]["terminal"] == "EVALUATOR_PASS", row
        assert row["result"]["evaluator"]["safety_state"] == "NOT_RUN"
        journal = DevJournal(root / f"row-{i + 1}", row["result"]["run_id"])
        assert len(cases.saved_cases(journal.events())) == 1
        changed = requests[1 - i].model_copy(update={
            "state_root": root / f"row-{i + 1}", "resume_run_id": row["result"]["run_id"],
        })
        with pytest.raises(ResumeContractMismatch):
            runner.run_dev(changed)
    with pytest.raises(FileExistsError):
        panel.run_panel(requests, max_cost_usd=Decimal(12), state_root=root)


def test_shared_ledger_settles_immediately_and_never_transfers_row_budget():
    parent = DevCostLedger(Decimal(12), pricing_for_model("gpt-5.4-2026-03-05"))
    first = panel.RowCostLedger(Decimal(3), parent)
    paid = first.settle(input_tokens=1000, cached_input_tokens=0, output_tokens=1000)
    assert parent.spent_nanos == first.spent_nanos == paid
    second = panel.RowCostLedger(Decimal(3), parent)
    assert second.remaining_nanos == 3_000_000_000
    parent.spent_nanos = parent.cap_nanos - 100
    assert second.remaining_nanos == 100
    assert second.admit(1) is None


@pytest.mark.parametrize("failure", ["count", "transport", "billing", "cleanup", "state", "cap"])
def test_panel_stops_later_rows_on_uncertainty(tmp_path, monkeypatch, failure):
    calls = []

    def one(**kwargs):
        calls.append(kwargs)
        if failure == "state":
            raise ContractError("identity mismatch")
        return runner._OneRunResult({
            "terminal": "COST_CAP_REACHED" if failure == "cap" else "TASK_FAILED",
        }, True)

    monkeypatch.setattr(runner, "_run_one", one)
    requests = [mock_request(tmp_path, "none") for _ in range(4)]
    if failure == "state":
        with pytest.raises(ContractError, match="identity"):
            panel.run_panel(requests, max_cost_usd=Decimal(12), state_root=tmp_path / "panel")
    else:
        result = panel.run_panel(requests, max_cost_usd=Decimal(12), state_root=tmp_path / "panel")
        assert len(calls) == (4 if failure == "cap" else 1)
        assert all(r["status"] == "NOT_RUN" for r in result["rows"][len(calls):])
    if failure == "state":
        assert len(calls) == 1


def test_panel_rejects_repeat_and_resume_before_dispatch(tmp_path):
    request = mock_request(tmp_path, "none").model_copy(update={"repeat": 2})
    with pytest.raises(ContractError, match="fresh"):
        panel.run_panel([request], max_cost_usd=Decimal(12), state_root=tmp_path / "panel")
    assert not (tmp_path / "panel").exists()


@pytest.mark.parametrize("failure", ["count", "transport", "cap"])
def test_panel_uses_real_runner_count_and_dispatch_boundaries(tmp_path, monkeypatch, failure):
    counts, dispatches = [], []

    class Adapter:
        def __init__(self, config, *, api_key):
            assert config.transport_max_retries == 0
            assert api_key == "test-only-sentinel"

        def request_payload(self, context, tools, *, system_prompt):
            return {"context": context, "tools": tools, "system": system_prompt}

        def count_input_tokens_v2(self, request, *, timeout_seconds):
            counts.append(request)
            if failure == "count":
                raise TimeoutError("count uncertainty")
            return 1_000_000 if failure == "cap" else 100

        def execute_request(self, request, *, requested_input_tokens, timeout_seconds):
            assert counts  # Count precedes dispatch in the shared runner.
            dispatches.append(request)
            raise TimeoutError("transport uncertainty")

    _patch_live_boundaries(monkeypatch)
    monkeypatch.setattr(runner, "OpenAIResponsesAdapter", Adapter)
    request = _live_request(tmp_path / "inputs", repeat=1, cap="0.01")
    result = panel.run_panel([request] * 4, max_cost_usd=Decimal("0.04"),
                             state_root=tmp_path / "panel")
    assert len(counts) == (4 if failure == "cap" else 1)
    assert len(dispatches) == (1 if failure == "transport" else 0)
    if failure != "cap":
        assert all(row["status"] == "NOT_RUN" for row in result["rows"][1:])


def test_panel_rejects_overallocated_budget_before_execution(tmp_path):
    request = _live_request(tmp_path / "inputs", repeat=1, cap="3")
    with pytest.raises(ContractError, match="allocations"):
        panel.run_panel([request] * 4, max_cost_usd=Decimal("11.99"),
                        state_root=tmp_path / "panel")
    assert not (tmp_path / "panel").exists()


def test_panel_reports_shared_settlement_without_reallocating_unused_money(tmp_path, monkeypatch):
    balances = []

    def one(**kwargs):
        ledger = kwargs["cost_ledger"]
        balances.append((ledger.cap_nanos, ledger.spent_nanos, ledger.parent.spent_nanos))
        assert ledger.admit(100, desired_output_ceiling=128) is not None
        cost = ledger.settle(input_tokens=100, cached_input_tokens=0, output_tokens=128)
        return runner._OneRunResult({"terminal": "AGENT_STOPPED", "cost_nanos": cost}, False)

    monkeypatch.setattr(runner, "_run_one", one)
    request = _live_request(tmp_path / "inputs", repeat=1, cap="0.01")
    result = panel.run_panel([request] * 4, max_cost_usd=Decimal("0.04"),
                             state_root=tmp_path / "panel")
    costs = [r["cost_nanos"] for r in result["rows"]]
    assert result["cost_nanos"] == sum(costs) > 0
    assert balances == [(10_000_000, 0, sum(costs[:i])) for i in range(4)]
    journal = DevJournal(tmp_path / "panel", result["panel_id"])
    assert journal.events()[-1]["payload"] == result
