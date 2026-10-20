"""Exact source/probe coverage for the bounded rendering experiment."""

from __future__ import annotations

from diagnostics.history_evidence_bundles import at, execution_fields, minimal
from diagnostics.semantic_history_index import separate
from diagnostics.size_only_replay import inventory
from patchloop.dev.history_search import PublicHistory
from patchloop.dev.native_sources import _lines
from patchloop.util import sha256_json


def validate(result, baseline, records):
    assert [r["record_id"] for r in result["records"]] == [
        r["record_id"] for r in baseline["records"]
    ]
    checked = 0
    for row, old in zip(result["records"], baseline["records"], strict=True):
        for key in ("record_id", "kind", "origin", "score", "observed_diff_hash", "diff_currency"):
            assert row[key] == old[key]
        body = records[row["record_id"]]["body"]
        assert sha256_json(body) == row["record_id"]
        if row["delivery"] == "complete":
            assert row["body"] == body
        elif row["delivery"] == "evidence_fields":
            full = execution_fields(body)
            assert row["evidence"] in (full, minimal(full, result["query"]))
            for pointer, value in row["evidence"]["fields"].items():
                assert at(body, pointer) == value
                checked += 1
            for excerpt in row["evidence"]["source_excerpts"]:
                value = at(body, excerpt["pointer"])
                assert value[excerpt["start"] : excerpt["end"]] == excerpt["text"]
                checked += 1
        else:
            assert row["body"] is None and not row.get("evidence") and row["excerpt"] is None
    return checked


def direct_sources(body):
    output = body.get("result", {}).get("output") or {}
    return [
        output.get("mutation_evidence"),
        *output.get("spans", []),
        *output.get("revalidated_spans", []),
    ]


def inline_facts(spans):
    facts = {}
    for span in spans:
        lines = _lines(span)
        if lines is not None:
            facts.update(
                {
                    (span["path"], span["file_hash"], number): line
                    for number, line in enumerate(lines, span["start_line"])
                }
            )
    return facts


def excerpt_facts(excerpt, body):
    pointer = excerpt.get("pointer", "")
    if not pointer.startswith("/result/output/") or not pointer.endswith("/content"):
        return {}
    span = at(body, pointer.rsplit("/", 1)[0])
    if _lines(span) is None:
        return {}
    content = span["content"]
    first, last = excerpt["start"], excerpt["end"]
    assert content[first:last] == excerpt["text"]
    facts, offset = {}, 0
    for number, line in enumerate(content.split("\n"), span["start_line"]):
        if first <= offset and offset + len(line) <= last:
            facts[span["path"], span["file_hash"], number] = line.removesuffix("\r")
        offset += len(line) + 1
    return facts


def probe_signature(body):
    if body.get("call", {}).get("tool") != "run_probe":
        return None
    observed = separate(body)["observed"]
    result = observed["result"]
    return sha256_json(
        {
            "arguments": observed["call"]["arguments"],
            "result": {
                key: result.get(key)
                for key in ("status", "error_code", "message", "workspace_diff_hash", "output")
            },
        }
    )


def coverage(projected, result, records):
    facts, _, observations = inventory(projected)
    native = PublicHistory()
    native.ingest(projected, sequence=1, turn_id="coverage", input_hash="coverage")
    probes = {}

    def note_probe(body):
        key = probe_signature(body)
        if key:
            probes[key] = {"record_id": sha256_json(body), "body": body}

    for record in native.records.values():
        note_probe(record["body"])
    whole = set(native.records) | set(observations)
    for row in result["records"]:
        body = records[row["record_id"]]["body"]
        if row["delivery"] == "complete":
            whole.add(row["record_id"])
            facts.update(inline_facts(direct_sources(body)))
            note_probe(body)
        elif row["delivery"] == "evidence_fields":
            fields = row["evidence"]["fields"]
            spans = [fields.get("/result/output/mutation_evidence")]
            for pointer in ("/result/output/spans", "/result/output/revalidated_spans"):
                spans.extend(fields.get(pointer, []))
            facts.update(inline_facts(spans))
            for excerpt in row["evidence"]["source_excerpts"]:
                facts.update(excerpt_facts(excerpt, body))
            # validate() proved that probes contain their whole execution-field set.
            note_probe(body)
        elif row.get("excerpt"):
            facts.update(excerpt_facts(row["excerpt"], body))
    return {"facts": facts, "probes": probes, "whole": whole}


def source_change(before, after):
    return [
        {"path": p, "file_hash": h, "line": n, "text": text}
        for (p, h, n), text in sorted(after.items())
        if before.get((p, h, n)) != text
    ]


def native_loss_keys(packing):
    return (
        set((s["path"], s["file_hash"], s["line"]) for s in packing["lost_sources"]),
        set(packing["lost_outputs"]),
        set(packing["lost_observations"]),
    )
