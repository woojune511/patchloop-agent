from __future__ import annotations

import json
from decimal import Decimal

import pytest

from diagnostics import planning_cycle as cycle
from patchloop.dev import runner
from patchloop.dev.contracts import DevModelTurn, PublicTurnDecision, RequestedTool
from patchloop.dev.cost import usd_to_nanos
from patchloop.dev.model import MockDevAdapter
from patchloop.dev.state import DevJournal
from patchloop.errors import RecoveryError


@pytest.fixture(autouse=True)
def mock_probe_image_preflight(monkeypatch):
    monkeypatch.setattr(
        runner.DockerProbeSandbox, "preflight", lambda self, **kwargs: self.identity
    )


def prepare(root):
    cycle.initialize(root, pricing_verified_on="2026-09-14", provider="mock")
    return cycle.prepare_group(root, hypothesis="A short public plan may improve task completion.")


def test_no_call_preparation_and_exact_contrast(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "run_dev", lambda *args: pytest.fail("preparation dispatched"))
    monkeypatch.setattr(
        runner,
        "load_exact_openai_api_key",
        lambda *args: pytest.fail("preparation accessed credential"),
    )
    root = tmp_path / "cycle"
    group = prepare(root)
    assert group["order"] == cycle.ORDER
    a, b = group["frozen"]["requests"].values()
    assert a.pop("planning_policy") == "none"
    assert b.pop("planning_policy") == "brief-v1"
    assert a == b
    assert a["enable_probes"] and a["repair_recheck"] and a["repeat"] == 1
    assert not (root / "state").exists()
    assert cycle.status(root)["spent_nanos"] == 0
    with pytest.raises(RecoveryError, match="finish the current"):
        cycle.prepare_group(root, hypothesis="not yet")


@pytest.mark.parametrize(
    "spent, slots, allowed",
    [("30.4", 8, True), ("30.400000001", 8, False), ("39", 1, False), ("38.8", 1, True)],
)
def test_group_cost_reservation(spent, slots, allowed):
    args = (usd_to_nanos(cycle.CAP), usd_to_nanos(Decimal(spent)), slots)
    if allowed:
        cycle.admit_group(*args)
    else:
        with pytest.raises(RecoveryError, match="every remaining"):
            cycle.admit_group(*args)


def test_mock_ab_full_fresh_runs_and_completed_reuse(tmp_path, monkeypatch):
    root = tmp_path / "cycle"
    group = prepare(root)
    report = cycle.execute_group(root, group["group_id"])
    assert report["complete"] and not report["extension_eligible"]  # equal 4/4 is not improvement
    assert all(a["acceptance_pass"] == a["submitted"] == 4 for a in report["arms"].values())
    assert all(r["cost_nanos"] == 0 and not r["stop_cycle"] for r in report["rows"])
    assert len({r["run_id"] for r in report["rows"]}) == 8
    for row in report["rows"]:
        assert row["accepted_mutations"] == 1
        assert row["call_counts"]["model"] == 4
        assert row["action_counts"]["run_check"] == 1
        assert row["task_acceptance"] == "PASS" and row["safety_state"] == "NOT_RUN"
        assert row["first_mutation_model_calls"] == 2
        assert (row["plan_status_counts"].get("created", 0) == 1) == (row["arm"] == "B")
    journal = cycle.control(root)
    before = journal.path.read_bytes()
    monkeypatch.setattr(runner, "run_dev", lambda *args: pytest.fail("completed sample rerun"))
    assert cycle.execute_group(root, group["group_id"]) == report
    assert journal.path.read_bytes() == before
    with pytest.raises(RecoveryError, match="qualifying"):
        cycle.prepare_group(root, task="loguru", hypothesis="not qualified")
    with pytest.raises(RecoveryError, match="one change axis"):
        cycle.prepare_group(root, hypothesis="no supporting public trace")
    cycle.close(root, "Tie in mock; no inference about actual agent quality")
    assert cycle.status(root)["closed"]


class Crash(BaseException):
    pass


@pytest.mark.parametrize("boundary", ["decision", "result"])
def test_cycle_restart_reuses_completed_and_exact_pending_run(tmp_path, monkeypatch, boundary):
    # The full eight-slot order is exercised above; recovery needs only an A/B pair.
    monkeypatch.setattr(cycle, "ORDER", ("A1", "B1"))
    root = tmp_path / "cycle"
    group = prepare(root)
    original, calls = MockDevAdapter.next_turn, []

    def count(self, context, tools):
        calls.append(1)
        return original(self, context, tools)

    monkeypatch.setattr(MockDevAdapter, "next_turn", count)
    append = DevJournal.append
    crashed = False

    def interrupt(self, kind, payload=None):
        nonlocal crashed
        result = append(self, kind, payload)
        target = "turn_decision_recorded" if boundary == "decision" else "terminal"
        if kind == target and not crashed:
            crashed = True
            raise Crash()
        return result

    monkeypatch.setattr(DevJournal, "append", interrupt)
    with pytest.raises(Crash):
        cycle.execute_group(root, group["group_id"])
    first = cycle.run_journal(root, group["group_id"], "A1").run_id
    report = cycle.execute_group(root, group["group_id"])
    assert report["complete"] and len(calls) == 8
    assert report["rows"][0]["run_id"] == first
    assert not cycle.status(root)["stopped"]


def test_exception_stops_whole_cycle_and_never_retries(tmp_path, monkeypatch):
    root = tmp_path / "cycle"
    group = prepare(root)
    invoked = []

    def uncertain(req):
        invoked.append(req)
        raise RecoveryError("provider/execution state uncertain")

    monkeypatch.setattr(runner, "run_dev", uncertain)
    with pytest.raises(RecoveryError, match="uncertain"):
        cycle.execute_group(root, group["group_id"])
    assert len(invoked) == 1 and cycle.status(root)["stopped"]
    partial = cycle.status(root)["groups"][0]
    assert partial["arms"]["A"]["runs"] == 1
    assert partial["arms"]["A"]["audited_results"] == 0
    assert partial["unscored_labels"] == ["A1"]
    with pytest.raises(RecoveryError, match="stopped or closed"):
        cycle.execute_group(root, group["group_id"])
    assert len(invoked) == 1


def test_runtime_drift_and_duplicate_executor_fail_before_dispatch(tmp_path, monkeypatch):
    root = tmp_path / "cycle"
    group = prepare(root)
    monkeypatch.setattr(runner, "run_dev", lambda *a: pytest.fail("must not dispatch"))
    with cycle.control(root).execution_lock(), pytest.raises(RecoveryError, match="already active"):
        cycle.execute_group(root, group["group_id"])
    monkeypatch.setattr(runner, "_runtime_hash", lambda: "changed")
    with pytest.raises(RecoveryError, match="contract changed"):
        cycle.execute_group(root, group["group_id"])


def test_durable_spend_and_price_validation(tmp_path):
    journal = DevJournal(tmp_path, "run_dev_cost")
    journal.append(
        "provider_call_finished",
        {
            "call_id": "call-1",
            "input_tokens": 1000,
            "cached_input_tokens": 0,
            "output_tokens": 1000,
            "cost_nanos": 5_250_000,
        },
    )
    assert cycle.settled(journal) == 5_250_000
    journal.append("provider_call_finished", {"call_id": "call-2", "cost_nanos": -1})
    with pytest.raises(Exception, match="usage"):
        cycle.settled(journal)


def test_manifest_and_group_tampering_fail_closed(tmp_path):
    root = tmp_path / "cycle"
    group = prepare(root)
    path = root / "groups" / f"{group['group_id']}.json"
    changed = json.loads(path.read_text())
    changed["order"] = ["B1"]
    path.write_text(json.dumps(changed))
    with pytest.raises(RecoveryError, match="changed"):
        cycle.load_group(root, group["group_id"])


def test_normal_non_submission_continues_and_counts_in_denominator(tmp_path, monkeypatch):
    def stop(self, context, tools):
        return DevModelTurn(
            tool_calls=[
                RequestedTool(
                    name="stop_task",
                    action_id="no-solution",
                    arguments={
                        "reason_code": "insufficient_public_evidence",
                        "summary": "No solution found",
                    },
                    turn_decision=PublicTurnDecision(mode="stop", basis="No supported edit"),
                )
            ]
        )

    monkeypatch.setattr(MockDevAdapter, "next_turn", stop)
    root = tmp_path / "cycle"
    group = prepare(root)
    report = cycle.execute_group(root, group["group_id"])
    assert report["complete"] and not report["extension_eligible"]
    assert all(a["runs"] == 4 and a["acceptance_pass"] == 0 for a in report["arms"].values())
    assert all(r["task_acceptance"] == "NOT_RUN" and not r["submitted"] for r in report["rows"])
    assert not cycle.status(root)["stopped"]


@pytest.mark.parametrize(
    "a_pass,b_pass,unsafe,eligible",
    [
        (0, 1, False, False),
        (0, 2, False, True),
        (1, 2, False, True),
        (2, 2, False, False),
        (3, 2, False, False),
        (0, 4, True, False),
    ],
)
def test_extension_threshold_is_predeclared(
    tmp_path, monkeypatch, a_pass, b_pass, unsafe, eligible
):
    root = tmp_path / "cycle"
    group = prepare(root)
    rows = {}
    for label in group["order"]:
        rows[label] = {
            "arm": label[0],
            "cost_nanos": 0,
            "uncached_equivalent_cost_nanos": 0,
            "task_acceptance": (
                "PASS" if int(label[1]) <= (a_pass if label[0] == "A" else b_pass) else "FAIL"
            ),
            "submitted": True,
            "stop_cycle": unsafe,
        }
        cycle.save(root, f"results/{group['group_id']}-{label}.json", rows[label])
    monkeypatch.setattr(cycle, "run_journal", lambda root, group_id, label: label)
    monkeypatch.setattr(cycle, "audit_run", lambda label, arm, **kw: rows[label])
    assert cycle.group_report(root, group)["extension_eligible"] is eligible
