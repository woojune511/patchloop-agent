"""Comparison controls: global stop, immutable allocation, grading identity and oracle."""

import json
from decimal import Decimal

import pytest

from diagnostics import source_retention_comparison as panel
from patchloop.dev.contracts import DevRunRequest
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError


def packet(tmp_path):
    rows = []
    for n, (index, arm, repetition) in enumerate(panel.ORDER, 1):
        req = DevRunRequest(provider="openai", model="gpt-5.4-mini-2026-03-17",
                            env_file=tmp_path / "unused.env", task=tmp_path / str(index),
                            state_root=tmp_path / "states" / str(n),
                            max_cost_usd=Decimal("1.20"),
                            retained_source_chars=24000 if arm == "A" else 48000)
        rows.append({"row": n, "wave": (n + 1) // 2, "task_index": index, "arm": arm,
                     "repetition": repetition, "instance_id": str(index),
                     "request": req.model_dump(mode="json")})
    return {"rows": rows, "native_entries": {str(i): {"index": i} for i in (18, 2)}}


@pytest.mark.parametrize("stop_wave", [None, 1, 2, 4])
def test_global_stop_and_native_identity_across_waves(tmp_path, stop_wave):
    calls, assessed = [], []
    def assess(root, entry, value, req):
        assessed.append((root, entry["index"], req.state_root))
        return {"ok": True, "status": "PASS", "agreement": True}
    def dispatch(rows, *, total_cap, workers, journal, after_row):
        calls.append(rows)
        assert total_cap == Decimal("2.40") and workers == 2
        assert {r["task_index"] for r in rows} == {18, 2}
        values = []
        for i, row in enumerate(rows):
            value = {"index": i, "ok": True,
                     "accounting": {"cost_nanos": 10, "billing_known": True,
                                    "counting_known": True}}
            value["assessment"] = after_row(i, value, DevRunRequest.model_validate(row["request"]))
            values.append(value)
        return {"rows": values, "stopped": len(calls) == stop_wave}
    result = panel.execute_waves(tmp_path, packet(tmp_path), DevJournal(tmp_path, "run_dev_test"),
                                 dispatch=dispatch, assess=assess)
    count = 2 * (stop_wave or 4)
    assert result["started"] == count and result["not_started"] == 8 - count
    assert result["cost_nanos"] == 10 * count and result["allocation"] == "CLOSED"
    assert [r["row"] for r in result["rows"]] == list(range(1, count + 1))
    assert [index for _, index, _ in assessed] == [18, 2] * (count // 2)
    assert len({root for root, _, _ in assessed}) == count


@pytest.mark.parametrize("change", ["cap", "confound", "resume", "order", "state"])
def test_confounded_or_expanded_requests_rejected(tmp_path, change):
    rows = packet(tmp_path)["rows"]
    if change == "cap":
        rows[0]["request"]["max_cost_usd"] = "1.21"
    elif change == "confound":
        rows[2]["request"]["planning_policy"] = "brief-v1"
    elif change == "resume":
        rows[0]["request"]["resume_run_id"] = "run_dev_previous"
    elif change == "order":
        rows.reverse()
    else:
        rows[0]["request"]["state_root"] = rows[1]["request"]["state_root"]
    with pytest.raises((ContractError, ValueError)):
        panel.validate_rows(rows)


def observation(values):
    return {"exit_code": 0, "stdout": json.dumps(values)}


def test_public_pvlib_requires_complete_correct_output_and_preservation():
    spec = panel.public_spec(2, "public issue")
    rows = [{"case": case, "values": [47.85, 50.85, 50.85], "index_preserved": True,
             "name": "tmod"} for case in ("naive", "aware")]
    assert panel.classify(observation(rows), spec)["status"] == "PASS"
    rows[1] = {"case": "aware", "error": "TypeError"}
    result = panel.classify(observation(rows), spec)
    assert result["status"] == "FAIL" and result["ordinary_pass"]
    rows[1] = {**rows[0], "case": "aware", "values": [0, 0, 0]}
    assert panel.classify(observation(rows), spec)["status"] == "FAIL"
    rows[1] = {**rows[0], "case": "aware", "index_preserved": False}
    assert panel.classify(observation(rows), spec)["status"] == "FAIL"
    assert panel.classify({**observation(rows), "cleanup_failed": True}, spec)["status"] \
        == "UNASSESSED"


def test_public_sql_requires_full_output_not_only_removed_symptom():
    spec = {"case": "1733", "expected_lines": ["SELECT", "    a + b", "FROM t"]}
    assert panel.classify(observation({"output": "SELECT\n    a + b\nFROM t\n"}), spec)["status"] \
        == "PASS"
    assert panel.classify(observation({"output": "SELECT\n    a + b"}), spec)["status"] == "FAIL"
