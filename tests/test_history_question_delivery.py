from __future__ import annotations

import copy
import json

from test_dev_history_search import exchange, items

from patchloop.dev import evidence_focus
from patchloop.dev import history_evidence as evidence
from patchloop.dev.history_search import PublicHistory
from patchloop.util import canonical_json, sha256_json


def test_rank_and_payload_exclude_authored_plans_but_id_read_preserves_original():
    original = exchange(text="observed_failure")
    result = json.loads(original[1]["output"])
    result["memory_update_result"] = {"statement": "unverifiedmotive"}
    original[1]["output"] = canonical_json(result)
    history = evidence.EvidenceHistory()
    history.ingest(items(exchanges=original), sequence=1, turn_id="t", input_hash="i")
    assert not history.search("unverifiedmotive", current_diff_hash="d")["records"]
    row = history.search("observed_failure", current_diff_hash="d")["records"][0]
    assert row["delivery"] == "evidence_fields"
    fields = row["evidence"]["fields"]
    assert fields["/call/arguments/python_source"] == "print('observed_failure')"
    assert fields["/result/output/stdout"] == "observed_failure"
    assert fields["/result/output/environment"]["cwd"] == "isolated"
    assert "unverifiedmotive" not in canonical_json(fields)
    full = history.search(row["record_id"], current_diff_hash="d")["records"][0]
    assert sha256_json(full["body"]) == row["record_id"]
    assert full["body"]["result"] == result


def test_function_unit_keeps_exception_and_dispatch_conditions_not_class_preamble():
    text = '''class Loader:
    def unrelated(self):
        """dispatch path fallback source path source path"""
        return 0

    def dispatch(self, path, fallback=True):
        try:
            return open_file(path)
        except OSError:
            if fallback:
                return from_name(path)
            raise

    def neighbor(self):
        return 1
'''
    body = {
        "call": {"tool": "read_file", "arguments": {"path": "loader.py"}},
        "result": {
            "output": {
                "spans": [{"path": "loader.py", "file_hash": "H", "start_line": 1, "content": text}]
            }
        },
    }
    unit = evidence.source_unit(evidence.execution_fields(body), "dispatch source path")
    excerpt = unit["source_excerpts"][0]
    assert excerpt["unit"] == "observed_function"
    assert "def dispatch" in excerpt["text"] and "except OSError:" in excerpt["text"]
    assert "if fallback:" in excerpt["text"] and "            raise" in excerpt["text"]
    assert "def unrelated" not in excerpt["text"] and "def neighbor" not in excerpt["text"]
    assert excerpt["text"] == text[excerpt["start"] : excerpt["end"]]
    # Without an observed end boundary, retain the observed span, never certify a full function.
    body["result"]["output"]["spans"][0]["content"] = "    def dispatch(self):\n        return 1\n"
    assert (
        evidence.source_unit(evidence.execution_fields(body), "dispatch")["source_excerpts"][0][
            "unit"
        ]
        == "observed_span"
    )


def test_oversized_execution_stays_atomic_and_original_pages_round_trip():
    history = evidence.EvidenceHistory()
    history.ingest(
        items(exchanges=exchange(text="needle " * 10_000)), sequence=1, turn_id="t", input_hash="i"
    )
    record = history.search("needle", current_diff_hash="d")["records"][0]
    assert record["delivery"] == "metadata_only_evidence_budget"
    assert "evidence" not in record and record["excerpt"] is None
    text, offset = "", None
    while True:
        result = history.search(record["record_id"], current_diff_hash="d", offset=offset)
        assert len(canonical_json(result)) <= 48_000
        page = result["records"][0]["page"]
        assert page["start"] == len(text) and page["end"] > page["start"]
        text += page["text"]
        offset = page["next_offset"]
        if offset is None:
            break
    assert sha256_json(json.loads(text)) == record["record_id"]


def test_two_question_refs_keep_search_and_countercheck_with_exact_exchange_and_currency():
    search = {
        "action_id": "s",
        "tool": "search_history",
        "input_hash": "I",
        "workspace_diff_hash": "D",
        "output": {"records": [], "policy": "public-v1"},
    }
    probe = {
        "action_id": "p",
        "tool": "run_probe",
        "input_hash": "P",
        "workspace_diff_hash": "D",
        "output": {"stdout": "failed", "passed": False},
    }
    question = {
        "text": "Which original condition fails?",
        "evidence": [
            {"kind": "tool_result", "action_id": "s", "role": "primary"},
            {"kind": "tool_result", "action_id": "p", "role": "countercheck"},
        ],
    }
    bound, error = evidence_focus.bind_question(
        question, [], {"s": search, "p": probe}, diff_hash="D"
    )
    assert not error and len(bound["evidence"]) == 2
    calls = [
        {"action_id": "s", "name": "search_history", "arguments": {"query": "condition"}},
        {"action_id": "p", "name": "run_probe", "arguments": {"python_source": "print(0)"}},
    ]
    events = [
        {"event_type": "turn_decision_recorded", "payload": {"tool_calls": calls}},
        *[{"event_type": "action_finished", "payload": {"result": r}} for r in (search, probe)],
    ]
    quoted = evidence_focus.optional_exchanges(bound, events, diff_hash="D")
    assert len(quoted) == 4
    assert next(i for i in quoted if i["type"] == "function_call_output" and i["call_id"] == "s")[
        "output"
    ] == canonical_json(search)
    view = {
        "current_diff": {"patch_hash": "D"},
        "working_notes": {"open_question": copy.deepcopy(bound)},
    }
    evidence_focus.project_interpretations(view, quoted)
    ref = view["working_notes"]["open_question"]["evidence"][0]
    assert ref["evidence_delivery"] == "complete" and ref["evidence_currency"] == "historical"
    assert ref["behavior_coverage"] == "not_assessed"
    assert evidence_focus.optional_exchanges(bound, events, diff_hash="changed") == []
    assert evidence_focus.bind_question(
        {**question, "evidence": question["evidence"] * 2},
        [],
        {"s": search, "p": probe},
        diff_hash="D",
    )[1]


def test_render_prioritizes_units_without_filling_remaining_space_with_unrelated_source():
    history = PublicHistory()
    code = "def chosen(x):\n    return x\n\ndef neighbor():\n    return 2\n" + "# unrelated\n" * 800
    body = {
        "call": {"tool": "read_file", "arguments": {"path": "x.py"}},
        "result": {
            "output": {
                "spans": [{"path": "x.py", "file_hash": "H", "start_line": 1, "content": code}]
            }
        },
    }
    history._add("public_tool_exchange", body, {"first_delivered_sequence": 1}, "D")
    baseline = history.search("chosen", current_diff_hash="D")
    result = evidence.render(baseline, history.records)
    assert len(canonical_json(result)) < len(canonical_json(baseline))
    assert (
        result["records"][0]["evidence"]["source_excerpts"][0]["text"]
        == "def chosen(x):\n    return x\n"
    )
