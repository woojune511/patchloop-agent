from __future__ import annotations

import copy
import json

import pytest
from test_dev_history_search import exchange, items

from patchloop.dev import evidence_focus
from patchloop.dev import history_evidence as evidence
from patchloop.dev.contracts import DevToolResult
from patchloop.dev.history_search import PublicHistory
from patchloop.util import canonical_json, sha256_json


def overflow(output):
    result = DevToolResult(
        action_id="s",
        tool="search_history",
        status="succeeded",
        input_hash="i",
        workspace_diff_hash="d",
        output=output,
    )
    original = result.model_dump(mode="json")
    reduced = evidence.overflow_result(result)
    assert result.model_dump(mode="json") == original
    return reduced.output


def test_rank_excludes_authored_plans_but_full_delivery_labels_and_preserves_them():
    original = exchange(text="observed_failure")
    result = json.loads(original[1]["output"])
    result["memory_update_result"] = {"statement": "unverifiedmotive"}
    original[1]["output"] = canonical_json(result)
    history = evidence.EvidenceHistory()
    history.ingest(items(exchanges=original), sequence=1, turn_id="t", input_hash="i")
    assert not history.search("unverifiedmotive", current_diff_hash="d")["records"]
    row = history.search("observed_failure", current_diff_hash="d")["records"][0]
    assert row["delivery"] == "complete"
    assert row["body"]["call"]["arguments"]["python_source"] == "print('observed_failure')"
    assert row["body"]["result"] == result
    assert row["model_annotation_paths"] == [
        "/call/arguments/question",
        "/result/memory_update_result",
    ]
    full = history.search(row["record_id"], current_diff_hash="d")["records"][0]
    assert sha256_json(full["body"]) == row["record_id"]
    assert full["body"]["result"] == result


def test_source_fallback_keeps_multiple_functions_only_after_real_overflow():
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
    # Complete source fits normally, including the neighbor and class context.
    history = evidence.EvidenceHistory()
    history._add("public_tool_exchange", body, {"first_delivered_sequence": 1}, "D")
    result = history.search("dispatch source path", current_diff_hash="D")
    assert result["records"][0]["body"] == body
    # Actual 48k overflow, not the query, activates lexical unit fallback.
    text = "# module context\n" * 4000 + text
    body["result"]["output"]["spans"][0]["content"] = text
    history = evidence.EvidenceHistory()
    history._add("public_tool_exchange", body, {"first_delivered_sequence": 1}, "D")
    result = history.search("dispatch source path", current_diff_hash="D")
    assert result["records"][0]["body"] == body
    result = overflow(result)
    assert len(canonical_json(result)) <= 48_000
    excerpts = result["records"][0]["evidence"]["source_excerpts"]
    assert len(excerpts) == 2  # Both complete observed functions, not just the named one.
    assert "def dispatch" in excerpts[0]["text"] and "except OSError:" in excerpts[0]["text"]
    assert "if fallback:" in excerpts[0]["text"] and "            raise" in excerpts[0]["text"]
    assert "def unrelated" in excerpts[1]["text"]
    for excerpt in excerpts:
        assert excerpt["unit"] == "observed_function"
        assert excerpt["text"] == text[excerpt["start"] : excerpt["end"]]
    # Without an observed end boundary, retain the observed span, never certify a full function.
    body["result"]["output"]["spans"][0]["content"] = "    def dispatch(self):\n        return 1\n"
    _, units = evidence.source_candidates(evidence.execution_fields(body), "dispatch")
    assert [u["excerpt"]["unit"] for u in units] == ["observed_span"]


def test_oversized_execution_stays_atomic_and_original_pages_round_trip():
    history = evidence.EvidenceHistory()
    history.ingest(
        items(exchanges=exchange(text="needle " * 10_000)), sequence=1, turn_id="t", input_hash="i"
    )
    original = history.search("needle", current_diff_hash="d")
    assert original["records"][0]["delivery"] == "complete"
    record = overflow(original)["records"][0]
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


def test_render_retains_whole_original_until_exact_serialized_limit():
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
    assert result["records"][0]["body"] == body
    assert sha256_json(result["records"][0]["body"]) == result["records"][0]["record_id"]
    size = len(canonical_json(result))
    assert evidence.render(baseline, history.records, max_chars=size) == result
    reduced = evidence.render(baseline, history.records, max_chars=size - 1)
    assert len(canonical_json(reduced)) <= size - 1
    assert reduced["records"][0]["body"] is None


def test_overflow_tries_complete_other_records_and_whole_spans_before_functions():
    history = evidence.EvidenceHistory()
    small = {
        "path": "x.py",
        "file_hash": "H",
        "start_line": 1,
        "content": "CONTEXT = 3\ndef caller():\n    return CONTEXT\ndef helper():\n    pass\n",
    }
    large = {
        "path": "y.py",
        "file_hash": "H",
        "start_line": 1,
        "content": "# other module context\n" * 4000,
    }
    body = {
        "call": {"tool": "read_file", "arguments": {"path": "x.py"}},
        "result": {"output": {"spans": [small, large]}},
    }
    history._add("public_tool_exchange", body, {"first_delivered_sequence": 1}, "D")
    history.ingest(
        items(exchanges=exchange(text="caller counterexample")),
        sequence=2,
        turn_id="probe",
        input_hash="i",
    )
    result = overflow(history.search("caller", current_diff_hash="D"))
    probe = next(r for r in result["records"] if r["candidate"]["tool"] == "run_probe")
    assert probe["delivery"] == "complete"
    source = next(r for r in result["records"] if r["candidate"]["tool"] == "read_file")
    assert source["evidence"]["source_excerpts"] == [
        {
            "pointer": "/result/output/spans/0/content",
            "start": 0,
            "end": len(small["content"]),
            "text": small["content"],
            "unit": "observed_span",
        }
    ]
    assert len(canonical_json(result)) <= 48_000


@pytest.mark.parametrize("pressure", [None, "tokens", "bytes", "recovery"])
def test_runner_delivers_large_original_or_reduces_only_after_measured_fresh_overflow(
    monkeypatch,
    tmp_path,
    pressure,
):
    from test_dev_history_search import call
    from test_dev_runner import _crash_journal_once, _SimulatedCrash
    from test_dev_segments import assert_submitted, configured, records

    from patchloop.contracts import Artifact
    from patchloop.dev import runner, segments
    from patchloop.dev.model import DevModelTurn, MockDevAdapter
    from patchloop.dev.native_sources import PUBLIC_EVIDENCE_KIND, public_exchanges

    class Script(MockDevAdapter):
        searched = False

        def _next_action(self, context, schemas):
            if json.loads(context).get("source_spans") and not self.searched:
                self.searched = True
                return DevModelTurn(tool_calls=[call(query="parse_rows")])
            turn = super()._next_action(context, schemas)
            # A real size handoff can require a fresh source read. The static mock
            # IDs must not collide with its earlier read under a different plan.
            for action in turn.tool_calls:
                if self.searched and action.name in {"read_file", "search_files"}:
                    action.action_id += "-after-search"
            return turn

    req, inputs, counted, _ = configured(
        monkeypatch,
        tmp_path,
        planning="brief-v1",
        script=Script("csv-quoted-newline"),
    )
    req = req.model_copy(update={"history_search_policy": "public-v1"})
    # A public result stub isolates request admission from retrieval, which the
    # real gateway/corpus tests exercise separately. No provider/network is used.
    corpus = evidence.EvidenceHistory()
    body = {"field": "supplied_observation", "value": "parse_rows " + "raw_context " * 6000}
    corpus._add("supplied_public_observation", body, {"first_delivered_sequence": 1}, None)
    lookup = evidence.EvidenceHistory.search
    monkeypatch.setattr(
        evidence.EvidenceHistory, "search", lambda self, *a, **kw: lookup(corpus, *a, **kw)
    )

    def search_outputs(items):
        return [
            json.loads(i["output"])["output"]
            for i in public_exchanges(
                items,
                archive_kind=PUBLIC_EVIDENCE_KIND,
            )
            if i["type"] == "function_call_output"
            and json.loads(i["output"]).get("tool") == "search_history"
        ]

    count = runner.OpenAIResponsesAdapter.count_input_tokens_v2

    def tokens(self, payload, **kw):
        normal = count(self, payload, **kw)
        return (
            60_001
            if any(len(canonical_json(r)) > 48_000 for r in search_outputs(payload["input"]))
            else normal
        )

    if pressure in {"tokens", "recovery"}:
        monkeypatch.setattr(runner.OpenAIResponsesAdapter, "count_input_tokens_v2", tokens)
    if pressure == "bytes":
        monkeypatch.setattr(segments, "MAX_REQUEST_BYTES", 128_000)
    if pressure == "recovery":

        def reduced_seed(payload):
            journal, store = records(req)
            handoff = json.loads(
                store.read_bytes(Artifact.model_validate(payload["handoff_artifact"]))
            )
            return handoff.get("evidence_manifest", {}).get("history_result_reduced", False)

        _crash_journal_once(
            monkeypatch, event_type=segments.PREPARED_EVENT, predicate=reduced_seed, when="after"
        )
        with pytest.raises(_SimulatedCrash):
            runner.run_dev(req)
        journal, _ = records(req)
        req = req.model_copy(update={"resume_run_id": journal.run_id})
    result = runner.run_dev(req)["runs"][0]
    assert_submitted(result)
    journal, store = records(req)
    canonical = [
        e["payload"]["result"]
        for e in journal.events()
        if e["event_type"] == "action_finished"
        and e["payload"]["result"]["tool"] == "search_history"
    ]
    assert len(canonical) == 1 and canonical[0]["output"]["records"][0]["body"] == body
    delivered = [r for item in inputs for r in search_outputs(item)]
    assert delivered
    assert (
        all(r["records"][0]["body"] == body for r in delivered)
        if pressure is None
        else all(len(canonical_json(r)) <= 48_000 for r in delivered)
    )
    # Counts do not spend model/tool actions; the real source refresh does.
    assert len(inputs) == (5 if pressure is None else 6)
    assert len(counted) == (8 if pressure in {"tokens", "recovery"} else len(inputs))
    if pressure == "bytes":
        assert all(segments.request_sizes({"input": i})["request_bytes"] <= 128_000 for i in inputs)
    for event in journal.events():
        if event["event_type"] == "turn_started":
            runner._load_active_model_input(event["payload"], store, context_policy=segments.POLICY)
