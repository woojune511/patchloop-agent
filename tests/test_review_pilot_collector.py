import json
from decimal import Decimal

import pytest

from diagnostics import review_pilot_collector as collector
from diagnostics.review_pilot_manifest import ORDER, TASKS
from patchloop.errors import ContractError
from patchloop.util import sha256_bytes


def plan(tmp_path):
    return {"result_root": str(tmp_path / "results"), "env_file": "not-read.env",
            "operator_only_programs": {}, "new_cap_nanos": 24_000_000_000,
            "rows": [{"task": task, "arm": arm, "new_cap_nanos": 2_000_000_000}
                     for task, order in zip(TASKS, ORDER, strict=True) for arm in order]}


@pytest.mark.parametrize("fault", [None, "preflight", "transport", "score", "overrun", "close"])
def test_panel_exact_order_accounting_and_stop(tmp_path, fault):
    config = plan(tmp_path)
    calls, closes = [], []

    class Client:
        def close(self):
            closes.append(1)
            if fault == "close":
                raise RuntimeError("uncertain close")

    def environment(*args):
        if fault == "preflight":
            raise ContractError("image missing")

    def execute(row, *args):
        calls.append((row["task"], row["arm"]))
        if fault == "transport" and len(calls) == 3:
            raise TimeoutError("unknown dispatch")
        return {"billing_known": True, "new_cost_nanos": 2_000_000_001
                if fault == "overrun" else 100, "stop_remaining": False,
                "result": {"terminal": "EVALUATOR_PASS"}}

    def score(*args):
        if fault == "score" and len(calls) == 3:
            raise ContractError("scoring failed")
        return {"status": "SCORED"}

    result = collector._run_panel(config, "hash", row_executor=execute, preflight=environment,
                                  client_factory=lambda _: Client(), scorer=score)
    if fault is None:
        assert calls == [(r["task"], r["arm"]) for r in config["rows"]]
        assert result["new_cost_nanos"] == 1200
        assert result["stop_reason"] is None
    else:
        expected = {"preflight": 0, "transport": 3, "score": 3, "overrun": 1, "close": 1}[fault]
        assert len(calls) == expected
        assert all(r["status"] == "NOT_RUN" for r in result["rows"][expected:])
        assert result["stop_reason"] is not None
        assert result["billing_known"] == (fault not in {"transport", "overrun"})
        if fault == "score":
            assert result["new_cost_nanos"] == 300
    assert len(closes) == len(calls)
    if fault in {"transport", "overrun"}:
        assert result["rows"][len(calls) - 1]["status"] == "PARTIAL"
    with pytest.raises(FileExistsError):
        collector._run_panel(config, "hash", row_executor=execute, preflight=environment,
                             client_factory=lambda _: pytest.fail("retry"), scorer=score)


@pytest.mark.parametrize("known", [True, False])
def test_partial_review_settlements_survive_panel_stop(tmp_path, known):
    from types import SimpleNamespace

    from diagnostics.review_context_offline import ReviewStopped

    calls = []

    def execute(*args):
        calls.append(1)
        if len(calls) == 1:
            return {"billing_known": True, "new_cost_nanos": 100,
                    "stop_remaining": False, "result": {}}
        raise ReviewStopped("final review call must finish_review", 250, known)

    result = collector._run_panel(plan(tmp_path), "hash", row_executor=execute,
        preflight=lambda *a: None, client_factory=lambda _: SimpleNamespace(close=lambda: None),
        scorer=lambda *a: {"status": "NOT_RUN"})
    assert len(calls) == 2
    assert result["rows"][1]["status"] == "PARTIAL"
    assert result["rows"][1]["partial_usage"] == {
        "settled_cost_nanos": 250, "billing_known": known}
    assert all(r["status"] == "NOT_RUN" for r in result["rows"][2:])
    assert result["recorded_new_cost_nanos"] == 350
    assert result["new_cost_nanos"] == (350 if known else None)
    assert result["billing_known"] == known


@pytest.mark.parametrize("bad_hash", [True, False])
def test_approval_rejected_before_controls_or_credentials(tmp_path, monkeypatch, bad_hash):
    path = tmp_path / "manifest.json"
    raw = json.dumps({"new_cap_nanos": 24_000_000_000}).encode()
    path.write_bytes(raw)
    monkeypatch.setattr(collector, "build", lambda *a, **kw: pytest.fail("past approval gate"))
    monkeypatch.setattr(collector.runner, "load_exact_openai_api_key",
                        lambda *a: pytest.fail("credential read"))
    with pytest.raises(ContractError, match="approved"):
        collector.collect(path, "wrong" if bad_hash else sha256_bytes(raw),
                          Decimal("24") if bad_hash else Decimal("25"))


def test_unsubmitted_patch_is_not_scored(tmp_path):
    from diagnostics.review_pilot_scoring import score

    assert score({}, {"result": {}}, tmp_path, {}, tmp_path / "score") == {
        "status": "NOT_RUN", "reason": "no submitted patch"}


def test_evaluator_verdicts_use_typed_values():
    from diagnostics.review_pilot_scoring import require_completed_verdicts
    from patchloop.contracts import Verdicts, VerdictState

    verdicts = Verdicts(hidden_tests=VerdictState.PASS, regression_tests=VerdictState.PASS,
                         scope_policy=VerdictState.PASS, safety_policy=VerdictState.PASS)
    require_completed_verdicts(verdicts)
    require_completed_verdicts(verdicts.model_copy(update={"hidden_tests": VerdictState.FAIL}))
    with pytest.raises(ContractError, match="did not complete"):
        require_completed_verdicts(Verdicts())
