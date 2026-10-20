"""Frozen, network-disabled BM25/dense/hybrid comparison on saved public inputs."""
from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import statistics
import sys
import time
from collections import Counter
from pathlib import Path
from unittest.mock import patch

from diagnostics.cleanup_information_checkpoint import ForkStore
from diagnostics.decision_sampler import require
from diagnostics.declaration_checkpoint import disjoint
from diagnostics.history_search_replay import pack_result, query_for, search_available
from diagnostics.semantic_history_index import PROJECTION, EvidenceHistory, observed_body, separate
from diagnostics.semantic_history_search import LocalEncoder, fuse, ranked
from diagnostics.size_only_replay import TokenEstimator, inventory, load_row, verify_baseline
from patchloop.artifacts import ArtifactStore
from patchloop.dev import history_search as search
from patchloop.dev.state import DevJournal
from patchloop.runtime import repository_root, runtime_content_hash
from patchloop.util import canonical_json, sha256_bytes

VARIANTS = ("bm25", "dense", "hybrid")


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def available_after(projected, result):
    visible = search.PublicHistory()
    visible.ingest(projected, sequence=1, turn_id="projection", input_hash="projection")
    return set(visible.records) | {r["record_id"] for r in result["records"]
                                  if r["delivery"] == "complete"}


def source_keys(packing):
    return {(s["path"], s["file_hash"], s["line"]) for s in packing["lost_sources"]}


def controls(encoder):
    cases = [
        ("How are temporary network outages handled?", [
            "Transient connection failures trigger another attempt with exponential backoff.",
            "The chart title is printed above the legend in a larger font."], 0),
        ("Can an account regain access after forgetting its credentials?", [
            "An administrator can change the color and width of each table column.",
            "A password reset link is emailed to the registered user."], 1),
    ]
    results = []
    for query, texts, expected in cases:
        records = {str(i): {"body": {"public_text": text}} for i, text in enumerate(texts)}
        scores, _ = encoder.score(query, records)
        chosen = max(scores, key=scores.get)
        results.append({"query": query, "texts": texts, "scores": scores,
                        "expected": str(expected), "chosen": chosen})
    require(all(r["chosen"] == r["expected"] for r in results), "paraphrase control failed")
    return results


def summarize(rows):
    requests = [q for row in rows for q in row["requests"]]
    missing = [q for q in requests if q["target_acquired"] and not q["target_visible"]]
    summary = {}
    for name in VARIANTS:
        variants = [q["variants"][name] for q in requests]
        tokens = [v["packing"]["central"]["attempts"][-1][
            "counts_before_unknown_search_reasoning"]["central"] for v in variants]
        summary[name] = {
            "missing_candidate": sum(q["variants"][name]["candidate"] for q in missing),
            "missing_complete": sum(q["variants"][name]["complete"] for q in missing),
            "target_available_after_packing": sum(v["target_available"] for v in variants),
            "target_gains_vs_bm25": sum(v["target_available"]
                and not q["variants"]["bm25"]["target_available"]
                for q, v in zip(requests, variants, strict=True)),
            "target_losses_vs_bm25": sum(not v["target_available"]
                and q["variants"]["bm25"]["target_available"]
                for q, v in zip(requests, variants, strict=True)),
            "complete_gained": sum(len(v["complete_gained"]) for v in variants),
            "complete_displaced": sum(len(v["complete_displaced"]) for v in variants),
            "bm25_complete_unavailable_after_packing": sum(
                len(v["bm25_complete_unavailable"]) for v in variants),
            "additional_lost_source_exposures": sum(len(v["additional_lost_sources"])
                                                    for v in variants),
            "additional_lost_outputs": sum(len(v["additional_lost_outputs"]) for v in variants),
            "additional_lost_observations": sum(len(v["additional_lost_observations"])
                                                 for v in variants),
            "delivery": dict(sum((Counter(v["delivery_counts"]) for v in variants), Counter())),
            "packing": {level: dict(Counter(v["packing"][level]["mode"] for v in variants))
                        for level in ("lower", "central", "upper")},
            "fits": {level: sum(v["packing"][level]["fits_known_content"] for v in variants)
                     for level in ("lower", "central", "upper")},
            "input_tokens": {"min": min(tokens), "median": statistics.median(tokens),
                             "max": max(tokens)},
        }
    return summary


def run(args, encode, tokenizer):
    started = time.perf_counter()
    output = args.output.resolve()
    require(not output.exists(), "use a fresh output directory")
    manifest, prior = read_json(args.manifest), read_json(args.baseline_replay)
    require(runtime_content_hash() == prior["contract"]["investigation_runtime_hash"],
            "baseline runtime changed")
    require(sha256_bytes(args.manifest.read_bytes()) == prior["contract"]["baseline_manifest_hash"],
            "source manifest drift")
    require(search.MAX_RESULTS == 8 and search.MAX_RESULT_CHARS == 48_000,
            "search response bounds changed")
    require(manifest["invariants"]["references"] == 2
            and manifest["invariants"]["retained_source_chars"] == 24_000,
            "source invariants changed")
    disjoint(output, [repository_root(), args.manifest.parent, args.baseline_replay.parent,
                     *(Path(r["request"]["state_root"]) for r in manifest["rows"])])
    download = read_json(args.model / "download.json")
    sources = {str(p.resolve()): sha256_bytes(p.read_bytes()) for p in (
        args.manifest, args.baseline_replay, args.protocol,
        Path(__file__), Path(__file__).with_name("semantic_history_search.py"),
        Path(__file__).with_name("semantic_history_index.py"),
        Path(__file__).with_name("history_search_replay.py"),
        Path(__file__).with_name("size_only_replay.py"), args.model / "download.json")}
    if args.raw_replay:
        raw = read_json(args.raw_replay)
        require(raw["contract"]["runtime_hash"] == runtime_content_hash(), "raw runtime drift")
        require(raw["contract"]["model"] == download, "raw embedding model drift")
        require(raw["contract"]["target"] == prior["contract"]["target_observation_hash"]
                and raw["contract"]["after_sequence"] == prior["contract"]["after_sequence"],
                "raw comparison target/cutoff drift")
        raw_queries = {(row["row"], q["sequence"]): q["query"]
                       for row in raw["rows"] for q in row["requests"]}
        require(raw_queries == {(row["row"], q["request_sequence"]): q["query"]
                                for row in prior["rows"] for q in row["requests"]},
                "raw comparison query/roster drift")
        sources[str(args.raw_replay.resolve())] = sha256_bytes(args.raw_replay.read_bytes())
    for name, identity in download["files"].items():
        path = args.model / name
        digest = sha256_bytes(path.read_bytes())
        require(digest == "sha256:" + identity["sha256"], "model file changed")
        sources[str(path.resolve())] = digest
    output.mkdir(parents=True)
    journal = DevJournal(output, "run_dev_semantichistory")
    store = ArtifactStore(output / "artifacts")
    contract = {"official": False, "provider_calls": 0, "new_spend_nanos": 0,
        "model_query_choice": "NOT_RUN", "evidence_uptake": "NOT_RUN", "repair_success": "NOT_RUN",
        "runtime_hash": runtime_content_hash(), "sources": dict(sources),
        "search_contract": search.contract(), "model": download, "tokenizer": tokenizer,
        "dependencies": {d.metadata["Name"]: d.version
                         for d in importlib.metadata.distributions(path=[str(args.dependencies)])},
        "protocol": store.put_text(args.protocol.read_text(encoding="utf-8")).model_dump(
            mode="json"),
        "variants": VARIANTS, "after_sequence": prior["contract"]["after_sequence"],
        "target": prior["contract"]["target_observation_hash"], "query": prior["contract"]["query"],
        "network": "socket connections blocked", "tuning_after_results": False,
        "cpu_threads": 4, "batch_size": 8, "packing": "independent-known-content-only"}
    contract["index_projection"] = PROJECTION if args.index_mode == "observed" else "raw-json"
    contract["raw_comparison"] = str(args.raw_replay.resolve()) if args.raw_replay else None
    (output / "manifest.json").write_text(canonical_json(contract) + "\n", encoding="utf-8")
    journal.append("experiment_frozen", contract)
    encoder = LocalEncoder(args.model)
    control_results = controls(encoder)
    journal.append("paraphrase_controls", {"results": control_results})
    cases, opaque = {}, {}
    for row in manifest["rows"]:
        turns, reasoning, reads = load_row(row, contract["after_sequence"])
        verify_baseline(turns)
        cases[row["row_id"]] = turns
        opaque.update(reasoning)
        sources.update(reads)
    estimator = TokenEstimator(encode, opaque, [t for turns in cases.values() for t in turns])
    saved = {(row["row"], q["request_sequence"]): q
             for row in prior["rows"] for q in row["requests"]}
    target, rows = contract["target"], []
    for row in manifest["rows"]:
        root = Path(row["request"]["state_root"])
        events = DevJournal(root, row["request"]["resume_run_id"]).events()
        corpus_type = EvidenceHistory if args.index_mode == "observed" else search.PublicHistory
        reader, corpus, requests = ForkStore(root, events), corpus_type(), []
        for turn in cases[row["row_id"]]:
            corpus.sync(events, reader, before_sequence=turn.sequence + 1)
            query, source = query_for(turn.state)
            previous = saved[row["row_id"], turn.sequence]
            require(query and query == previous["query"], "query drift")
            diff = turn.state["current_diff"]["patch_hash"]
            raw_order = search.PublicHistory.rank(corpus, query)
            with patch.object(corpus, "rank", return_value=raw_order):
                baseline = corpus.search(query, current_diff_hash=diff)
            require(baseline == previous["retrieval"], "baseline retrieval drift")
            lexical, excerpts = corpus.rank(query)
            scores, matches = encoder.score(query, corpus.records,
                body_for=observed_body if args.index_mode == "observed" else None)
            dense = ranked(corpus.records, scores)
            orders = {"bm25": lexical, "dense": dense,
                      "hybrid": fuse(corpus.records, lexical, dense)}
            original_complete = {r["record_id"] for r in baseline["records"]
                                 if r["delivery"] == "complete"}
            record = {"sequence": turn.sequence, "query": query, "query_source": source,
                      "corpus_records": len(corpus.records), "target_acquired": target in scores,
                      "target_visible": target in inventory(turn.wire["input"])[2],
                      "search_available": search_available(turn), "variants": {}}
            for name, order in orders.items():
                with patch.object(corpus, "rank", return_value=(order, excerpts)):
                    result = corpus.search(query, current_diff_hash=diff)
                if name == "bm25" and args.index_mode == "raw":
                    require(result == baseline, "renderer mismatch")
                selected = next((r for r in result["records"] if r["record_id"] == target), None)
                complete = {r["record_id"] for r in result["records"]
                            if r["delivery"] == "complete"}
                value = {"candidate": selected is not None,
                    "complete": target in complete,
                    "target_rank": next((i for i, (_, r) in enumerate(order, 1)
                                         if r["record_id"] == target), None),
                    "complete_gained": sorted(complete - original_complete),
                    "complete_displaced": sorted(original_complete - complete),
                    "delivery_counts": dict(Counter(r["delivery"] for r in result["records"])),
                    "retrieval": store.put_json(result).model_dump(mode="json"), "packing": {}}
                if name == "bm25" and args.index_mode == "raw":
                    value["packing"] = previous["packing"]
                    ref = value["packing"]["central"]["input_artifact"]
                    path = Path(ref["path"])
                    sources[str(path)] = sha256_bytes(path.read_bytes())
                    require(sources[str(path)] == ref["content_hash"], "baseline packing drift")
                    projected = read_json(path)
                else:
                    for level in ("lower", "central", "upper"):
                        packed, items = pack_result(turn, result, estimator, level=level)
                        require(packed["fits_known_content"], "packing exceeds existing limits")
                        if level == "central":
                            projected = items
                            packed["input_artifact"] = store.put_json(items).model_dump(mode="json")
                        value["packing"][level] = packed
                available = available_after(projected, result)
                value["target_available"] = target in available
                value["bm25_complete_unavailable"] = sorted(original_complete - available)
                packed, bp = value["packing"]["central"], previous["packing"]["central"]
                value["additional_lost_sources"] = sorted(source_keys(packed) - source_keys(bp))
                for kind in ("outputs", "observations"):
                    value["additional_lost_" + kind] = sorted(
                        packed["lost_" + kind].keys() - bp["lost_" + kind].keys())
                record["variants"][name] = value
            record["semantic_matches"] = {key: matches[key] for key in {
                *[r["record_id"] for _, r in dense[:8]],
                *[r["record_id"] for _, r in orders["hybrid"][:8]],
                *([target] if target in matches else [])}}
            requests.append(record)
            print(canonical_json({"row": row["row_id"], "sequence": turn.sequence,
                                  "replayed": len(requests)}), flush=True)
        sources.update({p: h for p, h in reader.reads.items() if Path(p).is_file()})
        item = {"row": row["row_id"], "requests": requests}
        item["index_records"] = store.put_json({
            key: {"original": record, **separate(record["body"])}
            for key, record in corpus.records.items()}).model_dump(mode="json")
        rows.append(item)
        journal.append("row_replayed", {"row": row["row_id"],
                                        "result": store.put_json(item).model_dump(mode="json")})
    embeddings = encoder.save(output, store)
    require(runtime_content_hash() == contract["runtime_hash"], "runtime changed during replay")
    require(all(sha256_bytes(Path(p).read_bytes()) == h for p, h in sources.items()),
            "source changed during replay")
    result = {"contract": contract, "summary": summarize(rows), "rows": rows,
              "controls": control_results, "embeddings": embeddings,
              "elapsed_seconds": time.perf_counter() - started,
              "source_files": sources, "source_files_unchanged": True}
    path = output / "result.json"
    path.write_text(canonical_json(result) + "\n", encoding="utf-8")
    journal.append("experiment_completed", {"result_hash": sha256_bytes(path.read_bytes()),
                                           "source_files_verified": len(sources)})
    print(canonical_json(result["summary"]), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("manifest", "baseline-replay", "model", "dependencies", "output", "protocol",
                 "tokenizer-package", "tokenizer-cache"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--index-mode", choices=("raw", "observed"), default="raw")
    parser.add_argument("--raw-replay", type=Path)
    args = parser.parse_args()
    require(args.index_mode == "raw" or args.raw_replay is not None,
            "observed index comparison requires the frozen raw replay")
    sys.path[:0] = [str(args.dependencies.resolve()), str(args.tokenizer_package.resolve())]
    os.environ["TIKTOKEN_CACHE_DIR"] = str(args.tokenizer_cache.resolve())
    import tiktoken

    def forbidden(*args, **kwargs):
        raise RuntimeError("semantic replay forbids network connections")

    with patch("socket.socket.connect", forbidden), patch("socket.socket.connect_ex", forbidden):
        encoding = tiktoken.get_encoding("o200k_base")
        run(args, lambda value: encoding.encode(value, disallowed_special=()), {
            "package": "tiktoken", "version": tiktoken.__version__, "encoding": encoding.name,
            "cache_files": {str(p): sha256_bytes(p.read_bytes())
                            for p in args.tokenizer_cache.iterdir() if p.is_file()}})


if __name__ == "__main__":
    main()
