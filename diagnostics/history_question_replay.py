"""Offline fixed-query delivery comparison and context-capacity sensitivity."""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
from collections import Counter
from pathlib import Path
from unittest.mock import patch

from diagnostics.history_evidence_audit import coverage, source_change
from diagnostics.history_search_replay import pack_result, query_for
from diagnostics.size_only_replay import TokenEstimator, load_row, verify_baseline
from patchloop.artifacts import ArtifactStore
from patchloop.dev import history_evidence as evidence
from patchloop.dev import history_search, segments
from patchloop.dev.state import DevJournal
from patchloop.runtime import repository_root, runtime_content_hash
from patchloop.util import canonical_json, sha256_bytes, sha256_json

LEVELS = ("lower", "central", "upper")


def validate(result, records):
    """Check original bytes and that a probe never contains only its favorable output."""
    assert len(result["records"]) <= 8 and len(canonical_json(result)) <= 48_000
    count = 0
    for row in result["records"]:
        body = records[row["record_id"]]["body"]
        assert sha256_json(body) == row["record_id"]
        if row["delivery"] == "complete":
            assert row["body"] == body
        elif row["delivery"] == "evidence_fields":
            unit = row["evidence"]
            for pointer, value in unit["fields"].items():
                assert evidence.at(body, pointer) == value
                count += 1
            for excerpt in unit["source_excerpts"]:
                original = evidence.at(body, excerpt["pointer"])
                assert original[excerpt["start"] : excerpt["end"]] == excerpt["text"]
                assert excerpt["start"] == 0 or original[excerpt["start"] - 1] == "\n"
                assert excerpt["end"] == len(original) or original[excerpt["end"] - 1] == "\n"
                count += 1
            if body["call"]["tool"] in {"run_probe", "run_check", "run_tests"}:
                assert unit == evidence.execution_fields(body)
        else:
            assert row["delivery"] == "metadata_only_evidence_budget"
            assert row["body"] is None and row["excerpt"] is None and "evidence" not in row
    return count


def delta(before, after):
    return {
        "sources_gained": source_change(before["facts"], after["facts"]),
        "sources_lost": source_change(after["facts"], before["facts"]),
        "probes_gained": {k: v for k, v in after["probes"].items() if k not in before["probes"]},
        "probes_lost": {k: v for k, v in before["probes"].items() if k not in after["probes"]},
    }


def summarize(rows):
    requests = [q for row in rows for q in row["requests"]]
    summary = {
        "requests": len(requests),
        "search_available": sum(q["search_available"] for q in requests),
    }
    for name in ("whole_first", "guard", "fixed_rank", "runtime"):
        vs = [q["variants"][name] for q in requests]
        missing = [
            q["variants"][name]
            for q in requests
            if q["target_acquired"] and not q["target_visible"]
        ]
        summary[name] = {
            "packet_returned_at_missing_28": sum(v["complete"] for v in missing),
            "packet_available": sum(v["available"] for v in vs),
            "packing": dict(Counter(v["packing"]["central"]["mode"] for v in vs)),
            "input_tokens": sum(v["tokens"] for v in vs),
            "max_input_tokens": max(v["tokens"] for v in vs),
            "response_chars": sum(v["response_chars"] for v in vs),
            "displacement": {
                base: {
                    f: sum(len(v["vs"][base][f]) for v in vs)
                    for f in ("sources_gained", "sources_lost", "probes_gained", "probes_lost")
                }
                for base in vs[0].get("vs", {})
            },
        }
    summary["rank_changes"] = sum(q["ranking_changed"] for q in requests)
    summary["capacity"] = {}
    for cap in (70_000, 80_000):
        vs = [q["capacity"][str(cap)] for q in requests if str(cap) in q["capacity"]]
        summary["capacity"][str(cap)] = {
            "size_cases": len(vs),
            "packet_gains": sum(v["packet_gain"] for v in vs),
            "size_handoffs_avoided": sum(v["packing"]["mode"] == "same_segment" for v in vs),
            "additional_input_tokens": sum(v["token_delta"] for v in vs),
            **{
                f: sum(len(v[f]) for v in vs)
                for f in ("sources_gained", "sources_lost", "probes_gained", "probes_lost")
            },
        }
    return summary


def run(args, encode):
    assert not args.output.exists() and not args.output.resolve().is_relative_to(repository_root())
    sources = {}

    def read(path, digest=None):
        data = Path(path).read_bytes()
        actual = sha256_bytes(data)
        assert digest is None or actual == digest, f"source drift: {path}"
        sources[str(Path(path).resolve())] = actual
        return json.loads(data)

    def artifact(ref):
        return read(ref["path"], ref["content_hash"])

    manifest, prior, guarded = read(args.manifest), read(args.baseline), read(args.guarded)
    assert manifest["invariants"]["references"] == 2
    assert manifest["invariants"]["retained_source_chars"] == 24_000
    assert all(
        r["request"]["segment_boundary_policy"] == segments.DEFAULT_BOUNDARY_POLICY
        for r in manifest["rows"]
    )
    sources[str(args.protocol.resolve())] = sha256_bytes(args.protocol.read_bytes())
    for path in (Path(__file__), Path(evidence.__file__), Path(history_search.__file__)):
        sources[str(path.resolve())] = sha256_bytes(path.read_bytes())
    args.output.mkdir(parents=True)
    store, journal = (
        ArtifactStore(args.output / "artifacts"),
        DevJournal(args.output, "run_dev_historyquestion"),
    )
    contract = {
        "official": False,
        "runtime_hash": runtime_content_hash(),
        "baseline_runtime_hash": prior["contract"]["runtime_hash"],
        "provider_calls": 0,
        "new_spend_nanos": 0,
        "model_query_choice": "NOT_RUN",
        "evidence_uptake": "NOT_RUN",
        "repair_success": "NOT_RUN",
        "sources": dict(sources),
        "search_contract": history_search.contract(),
        "capacity_analysis_only": [70_000, 80_000],
        "target": prior["contract"]["target"],
        "tokenizer": prior["contract"]["tokenizer"],
    }
    (args.output / "manifest.json").write_text(canonical_json(contract) + "\n", encoding="utf8")
    journal.append("experiment_frozen", contract)
    cases, opaque = {}, {}
    for row in manifest["rows"]:
        turns, reasoning, reads = load_row(row, prior["contract"]["after_sequence"])
        verify_baseline(turns)
        cases[row["row_id"]] = {t.sequence: t for t in turns}
        opaque.update(reasoning)
        sources.update(reads)
    estimator = TokenEstimator(encode, opaque, [t for row in cases.values() for t in row.values()])
    guards = {(r["row"], q["sequence"]): q for r in guarded["rows"] for q in r["requests"]}
    rows, checked = [], 0
    for old_row in prior["rows"]:
        catalog = artifact(old_row["index_records"])
        row = {"row": old_row["row"], "requests": []}
        for old in old_row["requests"]:
            turn = cases[row["row"]][old["sequence"]]
            assert query_for(turn.state)[0] == old["query"]
            records = {
                k: v["original"]
                for k, v in catalog.items()
                if v["original"]["origin"]["first_delivered_sequence"] <= turn.sequence
            }
            before = old["variants"]["bm25"]
            guard = guards[row["row"], old["sequence"]]["variants"]["bm25"]
            request = {
                k: old[k]
                for k in (
                    "sequence",
                    "query",
                    "target_acquired",
                    "target_visible",
                    "search_available",
                )
            }
            request.update(variants={}, capacity={})
            covers = {}
            baseline = artifact(before["retrieval"])
            for name, source in (("whole_first", before), ("guard", guard)):
                result = artifact(source["retrieval"])
                packing = source["packing"]
                items = artifact(packing["central"]["input_artifact"])
                assert sha256_json(items) == packing["central"]["input_hash"]
                covers[name] = coverage(items, result, records)
                request["variants"][name] = {
                    "complete": any(
                        r["record_id"] == contract["target"] and r["delivery"] == "complete"
                        for r in result["records"]
                    ),
                    "available": contract["target"] in covers[name]["whole"],
                    "packing": packing,
                    "retrieval": source["retrieval"],
                    "tokens": packing["central"]["attempts"][-1][
                        "counts_before_unknown_search_reasoning"
                    ]["central"],
                    "response_chars": len(canonical_json(result)),
                }
            history = evidence.EvidenceHistory()
            history.ingest(
                turn.wire["input"], sequence=turn.sequence, turn_id="visible", input_hash="visible"
            )
            history.records = records
            actual = history.search(
                old["query"], current_diff_hash=turn.state["current_diff"]["patch_hash"]
            )
            fixed = evidence.render(baseline, records)
            request["ranking_changed"] = [r["record_id"] for r in actual["records"]] != [
                r["record_id"] for r in baseline["records"]
            ]
            for name, result in (("fixed_rank", fixed), ("runtime", actual)):
                checked += validate(result, records)
                packed = {
                    level: pack_result(turn, result, estimator, level=level) for level in LEVELS
                }
                assert all(p[0]["fits_known_content"] for p in packed.values())
                covers[name] = coverage(packed["central"][1], result, records)
                value = {
                    "complete": any(
                        r["record_id"] == contract["target"] and r["delivery"] == "complete"
                        for r in result["records"]
                    ),
                    "available": contract["target"] in covers[name]["whole"],
                    "retrieval": store.put_json(result).model_dump(mode="json"),
                    "response_chars": len(canonical_json(result)),
                    "packing": {},
                    "vs": {
                        base: delta(covers[base], covers[name]) for base in ("whole_first", "guard")
                    },
                    "tokens": packed["central"][0]["attempts"][-1][
                        "counts_before_unknown_search_reasoning"
                    ]["central"],
                }
                for level, (packing, items) in packed.items():
                    if level == "central":
                        packing["input_artifact"] = store.put_json(items).model_dump(mode="json")
                    value["packing"][level] = packing
                request["variants"][name] = value
            current = request["variants"]["runtime"]
            if current["packing"]["central"]["mode"].startswith("size_handoff"):
                for cap in (70_000, 80_000):
                    with patch.object(segments, "MAX_INPUT_TOKENS", cap):
                        packing, items = pack_result(turn, actual, estimator)
                    cov = coverage(items, actual, records)
                    packing["input_artifact"] = store.put_json(items).model_dump(mode="json")
                    request["capacity"][str(cap)] = {
                        "packing": packing,
                        "packet_gain": not current["available"]
                        and contract["target"] in cov["whole"],
                        "token_delta": packing["attempts"][-1][
                            "counts_before_unknown_search_reasoning"
                        ]["central"]
                        - current["tokens"],
                        **delta(covers["runtime"], cov),
                    }
            row["requests"].append(request)
        rows.append(row)
        journal.append(
            "row_replayed",
            {"row": row["row"], "result": store.put_json(row).model_dump(mode="json")},
        )
        print(canonical_json({"row": row["row"], "requests": len(row["requests"])}), flush=True)
    assert runtime_content_hash() == contract["runtime_hash"], "runtime changed during replay"
    assert all(sha256_bytes(Path(p).read_bytes()) == h for p, h in sources.items()), (
        "source changed"
    )
    result = {
        "contract": contract,
        "rows": rows,
        "summary": summarize(rows),
        "exact_values_checked": checked,
        "sources": sources,
        "source_files_unchanged": True,
    }
    (args.output / "result.json").write_text(canonical_json(result) + "\n", encoding="utf8")
    journal.append(
        "experiment_completed", {"result": store.put_json(result).model_dump(mode="json")}
    )
    print(canonical_json(result["summary"]), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "manifest",
        "baseline",
        "guarded",
        "output",
        "protocol",
        "tokenizer-package",
        "tokenizer-cache",
    ):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.tokenizer_package.resolve()))
    os.environ["TIKTOKEN_CACHE_DIR"] = str(args.tokenizer_cache.resolve())
    import tiktoken

    def offline(*args, **kwargs):
        raise RuntimeError("network disabled during history replay")

    with (
        patch.object(socket.socket, "connect", offline),
        patch.object(socket.socket, "connect_ex", offline),
    ):
        tokenizer = tiktoken.get_encoding("o200k_base")
        run(args, lambda text: tokenizer.encode(text, disallowed_special=()))


if __name__ == "__main__":
    main()
