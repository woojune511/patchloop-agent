"""Provider-free full-original delivery and independent boundary/reference audit."""

from __future__ import annotations

import argparse
import copy
import json
import os
import socket
import sys
from collections import Counter
from pathlib import Path
from unittest.mock import patch

from diagnostics.history_evidence_audit import coverage
from diagnostics.history_question_replay import delta, validate
from diagnostics.history_search_replay import pack_result, query_for
from diagnostics.size_only_replay import TokenEstimator, load_row, verify_baseline
from patchloop.artifacts import ArtifactStore
from patchloop.dev import evidence_focus, history_evidence, history_search, segments
from patchloop.dev.native_sources import PUBLIC_EVIDENCE_KIND, public_exchanges
from patchloop.dev.state import DevJournal
from patchloop.runtime import git_commit, repository_root, runtime_content_hash
from patchloop.util import canonical_json, sha256_bytes, sha256_json

LEVELS = ("lower", "central", "upper")
ARMS = ("one_function", "full_first", "size_only")


def summary(requests):
    result = {"requests": len(requests), "arms": {}}
    for arm in ARMS:
        vs = [q["variants"][arm] for q in requests]
        missing = [
            q["variants"][arm] for q in requests if q["target_acquired"] and not q["target_visible"]
        ]
        result["arms"][arm] = {
            "caller_available": sum(v["available"] for v in vs),
            "caller_returned_at_missing": sum(v["returned"] for v in missing),
            "input_tokens": sum(v["tokens"] for v in vs),
            "max_input_tokens": max(v["tokens"] for v in vs),
            "response_chars": sum(v["response_chars"] for v in vs),
            "deliveries": dict(sum((Counter(v["deliveries"]) for v in vs), Counter())),
            "packing": {
                level: dict(Counter(v["packing"][level]["mode"] for v in vs)) for level in LEVELS
            },
            "delta": {
                base: {
                    f: sum(len(v["vs"][base][f]) for v in vs)
                    for f in ("sources_gained", "sources_lost", "probes_gained", "probes_lost")
                }
                for base in vs[0]["vs"]
            },
        }
    result["refs"] = {
        "occupancy": dict(Counter(q["references"]["count"] for q in requests)),
        "kinds": dict(sum((Counter(q["references"]["kinds"]) for q in requests), Counter())),
        "optional_tool_bodies": dict(
            Counter(len(q["references"]["optional_action_ids"]) for q in requests)
        ),
        "result_handoff_occupancy": dict(
            Counter(
                q["references"]["count"]
                for q in requests
                if q["variants"]["full_first"]["packing"]["central"]["already_due_result_boundary"]
            )
        ),
    }
    result["all_originals_fit_48k"] = sum(q["all_original_chars"] <= 48_000 for q in requests)
    result["all_originals_fit_outer_bound"] = sum(
        q["all_original_chars"] <= history_search.MAX_ORIGINAL_CHARS for q in requests
    )
    return result


def run(args, encode):
    assert not args.output.exists() and not args.output.resolve().is_relative_to(repository_root())
    sources = {}

    def read(path, digest=None):
        data = Path(path).read_bytes()
        actual = sha256_bytes(data)
        assert digest is None or digest == actual, f"source drift: {path}"
        sources[str(Path(path).resolve())] = actual
        return json.loads(data)

    def artifact(ref):
        return read(ref["path"], ref["content_hash"])

    manifest, catalog_index, prior = read(args.manifest), read(args.catalog), read(args.baseline)
    assert manifest["invariants"]["references"] == 2
    assert manifest["invariants"]["retained_source_chars"] == 24_000
    assert all(
        r["request"]["segment_boundary_policy"] == segments.DEFAULT_BOUNDARY_POLICY
        for r in manifest["rows"]
    )
    for path in (
        args.protocol,
        Path(__file__),
        Path(history_evidence.__file__),
        Path(history_search.__file__),
    ):
        sources[str(path.resolve())] = sha256_bytes(path.read_bytes())
    args.output.mkdir(parents=True)
    store = ArtifactStore(args.output / "artifacts")
    journal = DevJournal(args.output, "run_dev_historyfull")
    contract = {
        "official": False,
        "runtime_hash": runtime_content_hash(),
        "parent_commit": git_commit(),
        "baseline_runtime_hash": prior["contract"]["runtime_hash"],
        "provider_calls": 0,
        "new_spend_nanos": 0,
        "model_query_choice": "NOT_RUN",
        "evidence_uptake": "NOT_RUN",
        "repair_success": "NOT_RUN",
        "sources": dict(sources),
        "search_contract": history_search.contract(),
        "target": prior["contract"]["target"],
        "tokenizer": prior["contract"]["tokenizer"],
        "packing": "independent requests; common current prompt/schema for old and new delivery",
        "boundary_sensitivity": "size-only-v1 at unchanged 60000 tokens; diagnostic only",
        "reference_sensitivity": "observed occupancy only; no invented third citation",
    }
    (args.output / "manifest.json").write_text(canonical_json(contract) + "\n", encoding="utf8")
    journal.append("experiment_frozen", contract)
    cases, opaque = {}, {}
    for row in manifest["rows"]:
        turns, reasoning, reads = load_row(row, catalog_index["contract"]["after_sequence"])
        verify_baseline(turns)
        cases[row["row_id"]] = {t.sequence: t for t in turns}
        opaque.update(reasoning)
        sources.update(reads)
    estimator = TokenEstimator(encode, opaque, [t for row in cases.values() for t in row.values()])
    catalogs = {r["row"]: artifact(r["index_records"]) for r in catalog_index["rows"]}
    rows, exact_values = [], 0
    for old_row in prior["rows"]:
        row = {"row": old_row["row"], "requests": []}
        for old in old_row["requests"]:
            turn = cases[row["row"]][old["sequence"]]
            assert query_for(turn.state)[0] == old["query"]
            records = {
                k: v["original"]
                for k, v in catalogs[row["row"]].items()
                if v["original"]["origin"]["first_delivered_sequence"] <= turn.sequence
            }
            before = artifact(old["variants"]["runtime"]["retrieval"])
            history = history_evidence.EvidenceHistory()
            history.ingest(
                turn.wire["input"], sequence=turn.sequence, turn_id="visible", input_hash="visible"
            )
            history.records = records
            after = history.search(
                old["query"], current_diff_hash=turn.state["current_diff"]["patch_hash"]
            )
            assert [r["record_id"] for r in before["records"]] == [
                r["record_id"] for r in after["records"]
            ]
            exact_values += validate(after, records, max_chars=history_search.MAX_ORIGINAL_CHARS)
            full = copy.deepcopy(after)
            for r in full["records"]:
                r.update(body=records[r["record_id"]]["body"], delivery="complete")
                r.pop("evidence", None)
            question = turn.state.get("working_notes", {}).get("open_question") or {}
            refs = question.get("evidence", []) if isinstance(question, dict) else []
            optional = evidence_focus.optional_exchanges(
                question, turn.prefix, diff_hash=turn.state["current_diff"]["patch_hash"]
            )
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
            request.update(
                variants={},
                all_original_chars=len(canonical_json(full)),
                references={
                    "count": len(refs),
                    "kinds": dict(Counter(r["kind"] for r in refs)),
                    "evidence": refs,
                    "optional_action_ids": [
                        i["call_id"] for i in optional if i["type"] == "function_call_output"
                    ],
                },
            )
            covers = {}
            for arm in ARMS:
                result = before if arm == "one_function" else after
                packed_turn = turn
                if arm == "size_only":
                    packed_turn = copy.deepcopy(turn)
                    packed_turn.turn["context_segment"]["binding"]["boundary_policy"] = (
                        segments.SIZE_ONLY_BOUNDARY_POLICY
                    )
                packed = {
                    level: pack_result(packed_turn, result, estimator, level=level)
                    for level in LEVELS
                }
                assert all(p[0]["fits_known_content"] for p in packed.values())
                delivered = next(
                    json.loads(i["output"])["output"]
                    for i in public_exchanges(
                        packed["central"][1], archive_kind=PUBLIC_EVIDENCE_KIND
                    )
                    if i["type"] == "function_call_output"
                    and i["call_id"] == f"offline-history-{turn.sequence}"
                )
                assert sha256_json(delivered) == packed["central"][0]["delivered_result_hash"]
                covers[arm] = coverage(packed["central"][1], delivered, records)
                value = {
                    "returned": any(
                        r["record_id"] == contract["target"] and r["delivery"] == "complete"
                        for r in delivered["records"]
                    ),
                    "available": contract["target"] in covers[arm]["whole"],
                    "retrieval": store.put_json(delivered).model_dump(mode="json"),
                    "canonical_retrieval": store.put_json(result).model_dump(mode="json"),
                    "response_chars": len(canonical_json(delivered)),
                    "deliveries": dict(Counter(r["delivery"] for r in delivered["records"])),
                    "tokens": packed["central"][0]["attempts"][-1][
                        "counts_before_unknown_search_reasoning"
                    ]["central"],
                    "packing": {},
                    "vs": {
                        base: delta(covers[base], covers[arm])
                        for base in ARMS
                        if base in covers and base != arm
                    },
                }
                for level, (packing, items) in packed.items():
                    if level == "central":
                        packing["input_artifact"] = store.put_json(items).model_dump(mode="json")
                    value["packing"][level] = packing
                request["variants"][arm] = value
            row["requests"].append(request)
        rows.append(row)
        journal.append(
            "row_replayed",
            {"row": row["row"], "result": store.put_json(row).model_dump(mode="json")},
        )
        print(canonical_json({"row": row["row"], "requests": len(row["requests"])}), flush=True)
    assert runtime_content_hash() == contract["runtime_hash"]
    assert all(sha256_bytes(Path(p).read_bytes()) == h for p, h in sources.items())
    requests = [q for row in rows for q in row["requests"]]
    result = {
        "contract": contract,
        "rows": rows,
        "summary": summary(requests),
        "eligible_summary": summary([q for q in requests if q["search_available"]]),
        "exact_values_checked": exact_values,
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
        "catalog",
        "baseline",
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
