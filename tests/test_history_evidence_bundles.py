from __future__ import annotations

import copy

import pytest
from test_dev_history_search import exchange, items

from diagnostics import history_evidence_bundles as bundles
from diagnostics.history_evidence_audit import coverage, validate
from patchloop.dev.history_search import PublicHistory
from patchloop.util import canonical_json


def corpus():
    history = PublicHistory()
    history.ingest(
        items(exchanges=exchange(text="observed failure")),
        sequence=1,
        turn_id="first",
        input_hash="first",
    )
    return history


def test_probe_quotes_program_environment_and_output_together_without_question():
    history = corpus()
    record = next(iter(history.records.values()))
    record["body"]["result"]["output"].update(
        setup_checks={"status": "failed", "actual": "/tmp", "expected": "/workspace"},
        truncated=True,
        timed_out=False,
        stderr="SetupMismatchError",
    )
    full = bundles.execution_fields(record["body"])
    assert bundles.minimal(full, "expected behavior") == full
    assert full["fields"]["/call/arguments/python_source"]
    assert full["fields"]["/result/output/setup_checks"]["status"] == "failed"
    assert full["fields"]["/result/output/environment"]["cwd"] == "isolated"
    assert full["fields"]["/result/output/stdout"] == "observed failure"
    assert full["fields"]["/result/output/truncated"]
    assert "/call/arguments/question" not in full["fields"]
    assert all(bundles.at(record["body"], p) == v for p, v in full["fields"].items())


def test_minimum_units_precede_large_source_expansion_and_oversize_probe_is_atomic(monkeypatch):
    history = corpus()
    probe = next(iter(history.records.values()))
    body = {
        "call": {"tool": "read_file", "action_id": "read", "arguments": {"path": "a.py"}},
        "result": {
            "status": "succeeded",
            "output": {
                "spans": [
                    {
                        "path": "a.py",
                        "file_hash": "hash",
                        "start_line": 1,
                        "end_line": 500,
                        "content": "\n".join("observed value" for _ in range(500)),
                    }
                ]
            },
        },
    }
    source_id = history._add("public_tool_exchange", body, probe["origin"], "current")
    baseline = history.search("observed", current_diff_hash="current")
    # Freeze an explicit source-first order; rendering cannot change its ranking.
    baseline["records"].sort(key=lambda r: r["record_id"] != source_id)
    monkeypatch.setattr(bundles, "MAX_RESULT_CHARS", 4500)
    result, attempts = bundles.render(baseline, history.records)
    assert [r["record_id"] for r in result["records"]] == [
        r["record_id"] for r in baseline["records"]
    ]
    assert all(r["delivery"] == "evidence_fields" for r in result["records"])
    assert result["records"][0]["evidence"]["source_excerpts"]
    assert result["records"][1]["evidence"]["fields"]["/result/output/stdout"] == "observed failure"
    assert attempts[-1]["stage"] == "source_expansion" and not attempts[-1]["admitted"]
    assert len(canonical_json(result)) <= 4500
    probe["body"]["result"]["output"]["stdout"] = "long " * 5000
    result, _ = bundles.render(baseline, history.records)
    assert result["records"][1]["delivery"] == "metadata_only_evidence_budget"
    assert "evidence" not in result["records"][1] and result["records"][1]["excerpt"] is None


def test_source_excerpts_preserve_exact_full_lines_and_empty_searches():
    body = {
        "call": {"tool": "search_files", "arguments": {"query": "needle"}},
        "result": {
            "status": "succeeded",
            "output": {
                "spans": [
                    {
                        "path": "a.py",
                        "file_hash": "hash",
                        "start_line": 9,
                        "end_line": 308,
                        "content": "\n".join(f"needle on line {n}" for n in range(300)),
                    }
                ],
                "truncated": True,
                "searched_file_count": 4,
            },
        },
    }
    minimal = bundles.minimal(bundles.execution_fields(body), "needle")
    excerpt = minimal["source_excerpts"][0]
    original = bundles.at(body, excerpt["pointer"])
    assert excerpt["text"] == original[excerpt["start"] : excerpt["end"]]
    assert excerpt["start"] == 0 or original[excerpt["start"] - 1] == "\n"
    assert excerpt["end"] == len(original) or original[excerpt["end"] - 1] == "\n"
    assert minimal["fields"]["/result/output/truncated"]
    body["result"]["output"]["spans"] = []
    assert (
        bundles.minimal(bundles.execution_fields(body), "needle")["fields"]["/result/output/spans"]
        == []
    )


def test_local_context_guard_rejects_whole_unit_and_exact_id_pages_stay_unchanged():
    history = corpus()
    baseline = history.search("observed", current_diff_hash="current")
    original = copy.deepcopy(baseline)
    # Model a context already full: reject any added evidence, not selected fields.
    result, attempts = bundles.render(
        baseline,
        history.records,
        accept=lambda r: all("evidence" not in row for row in r["records"]),
    )
    assert result["records"][0]["delivery"] == "metadata_only_evidence_budget"
    assert attempts[0]["reason"] == "context" and baseline == original
    record_id = next(iter(history.records))
    page = history.search(record_id, current_diff_hash="current", offset=0)
    result, attempts = bundles.render(page, history.records, accept=lambda r: False)
    assert result == page and not attempts


def test_measurement_counts_execution_fields_separately_from_full_original_records():
    history = corpus()
    baseline = history.search("observed", current_diff_hash="current")
    result, _ = bundles.render(baseline, history.records)
    assert validate(result, baseline, history.records)
    before = coverage(items(), baseline, history.records)
    after = coverage(items(), result, history.records)
    assert before["probes"] == after["probes"] and len(after["probes"]) == 1
    record_id = next(iter(history.records))
    assert record_id in before["whole"] and record_id not in after["whole"]
    result["records"][0]["evidence"]["fields"]["/result/output/stdout"] = "invented pass"
    with pytest.raises(AssertionError):
        validate(result, baseline, history.records)
