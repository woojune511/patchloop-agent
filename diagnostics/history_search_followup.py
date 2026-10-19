"""Offline, fixed-query comparison of history search limits and passage ranking."""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from collections import Counter
from pathlib import Path
from unittest.mock import patch

from diagnostics.cleanup_information_checkpoint import ForkStore
from diagnostics.decision_sampler import require
from diagnostics.declaration_checkpoint import disjoint
from diagnostics.history_search_replay import pack_result, query_for, search_available
from diagnostics.size_only_replay import TokenEstimator, inventory, load_row, verify_baseline
from patchloop.artifacts import ArtifactStore
from patchloop.dev import history_search as search
from patchloop.dev.state import DevJournal
from patchloop.runtime import repository_root, runtime_content_hash
from patchloop.util import canonical_json, sha256_bytes, sha256_json

VARIANTS = ("baseline", "bounds_only", "passages", "current")


def load_baseline(path):
    spec = importlib.util.spec_from_file_location("history_search_baseline", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    require(module.MAX_RESULTS == 2 and module.MAX_RESULT_CHARS == 24_000,
            "baseline search bounds differ")
    require(module.contract()["ranking"] == "unicode-identifier-bm25-v1",
            "baseline search ranking differs")
    return module


def outputs(old, new, baseline, query, diff):
    original = old.search(query, current_diff_hash=diff)
    with (patch.object(baseline, "MAX_RESULTS", 8),
          patch.object(baseline, "MAX_RESULT_CHARS", 48_000)):
        bounds = old.search(query, current_diff_hash=diff)
    with patch.object(new, "_visible", set()):
        passages = new.search(query, current_diff_hash=diff)
    current = new.search(query, current_diff_hash=diff)
    return dict(zip(VARIANTS, (original, bounds, passages, current), strict=True))


def delivery(result, target):
    records = result["records"]
    selected = next((r for r in records if r["record_id"] == target), None)
    return {"candidate": selected is not None,
            "complete": selected is not None and selected["delivery"] == "complete",
            "body_chars": len(canonical_json(result)), "hits": len(records),
            "incomplete": sum(r["delivery"] != "complete" for r in records)}


def run(args, encode, tokenizer):
    output = args.output.resolve()
    require(not output.exists(), "use a fresh output directory")
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    prior = json.loads(args.baseline_replay.read_text(encoding="utf-8"))
    target = prior["contract"]["target_observation_hash"]
    after = prior["contract"]["after_sequence"]
    require(manifest["invariants"]["references"] == 2
            and manifest["invariants"]["retained_source_chars"] == 24_000,
            "source reference/source budget differs")
    require(sha256_bytes(args.manifest.read_bytes()) == prior["contract"]["baseline_manifest_hash"],
            "baseline manifest drift")
    disjoint(output, [repository_root(), args.manifest.parent, args.baseline_replay.parent,
                     *(Path(r["request"]["state_root"]) for r in manifest["rows"])])
    baseline = load_baseline(args.baseline_source)
    spec = importlib.util.spec_from_file_location("history_search_candidate", args.candidate_source)
    candidate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(candidate)
    require(candidate.contract()["ranking"] == "passage-coverage-character-rrf-v1",
            "supply the preserved passage prototype, not the selected runtime")
    output.mkdir(parents=True)
    journal = DevJournal(output, "run_dev_historysearchcomparison")
    store = ArtifactStore(output / "artifacts")
    protocol = repository_root() / "docs/history/2026-10-19-history-search-followup.md"
    contract = {"official": False, "provider_calls": 0, "new_spend_nanos": 0,
                "baseline_commit": "d224e1e2ad54e0ea3f783f3edfd2c88dbb63cf4e",
                "baseline_source_hash": sha256_bytes(args.baseline_source.read_bytes()),
                "candidate_source_hash": sha256_bytes(args.candidate_source.read_bytes()),
                "baseline_replay_hash": sha256_bytes(args.baseline_replay.read_bytes()),
                "runtime_hash": runtime_content_hash(),
                "implementation_hash": sha256_bytes(Path(__file__).read_bytes()),
                "protocol": store.put_text(protocol.read_text(encoding="utf-8")).model_dump(
                    mode="json"), "search_contract": candidate.contract(), "variants": VARIANTS,
                "tokenizer": tokenizer, "target": target, "after_sequence": after,
                "query": prior["contract"]["query"], "tuning_after_results": False,
                "model_query_choice": "NOT_RUN", "evidence_uptake": "NOT_RUN",
                "repair_success": "NOT_RUN", "packing": "independent-known-content-only"}
    (output / "manifest.json").write_text(canonical_json(contract) + "\n", encoding="utf-8")
    journal.append("experiment_frozen", contract)
    sources = {str(p.resolve()): sha256_bytes(p.read_bytes()) for p in (
        args.manifest, args.baseline_replay, args.baseline_source, args.candidate_source)}
    cases, opaque = {}, {}
    for row in manifest["rows"]:
        turns, reasoning, reads = load_row(row, after)
        verify_baseline(turns)
        cases[row["row_id"]] = turns
        opaque.update(reasoning)
        sources.update(reads)
    estimator = TokenEstimator(encode, opaque, [t for turns in cases.values() for t in turns])
    saved = {(row["row"], r["request_sequence"]): r
             for row in prior["rows"] for r in row["requests"]}
    rows = []
    for row in manifest["rows"]:
        root = Path(row["request"]["state_root"])
        events = DevJournal(root, row["request"]["resume_run_id"]).events()
        source_store = ForkStore(root, events)
        old, new = baseline.PublicHistory(), candidate.PublicHistory()
        requests = []
        for turn in cases[row["row_id"]]:
            for corpus in (old, new):
                corpus.sync(events, source_store, before_sequence=turn.sequence + 1)
            query, source = query_for(turn.state)
            previous = saved[row["row_id"], turn.sequence]
            require(query == previous["query"], "query drift")
            require(query is not None, "empty query must be reviewed separately")
            diff = turn.state["current_diff"]["patch_hash"]
            variants = outputs(old, new, baseline, query, diff)
            require(variants["baseline"] == previous["retrieval"], "baseline retrieval drift")
            require(set(old.records) == set(new.records), "corpus changed")
            visible = search.PublicHistory()
            visible.ingest(turn.wire["input"], sequence=turn.sequence,
                           turn_id="current", input_hash="current")
            require(new._visible == set(visible.records), "visible record reconstruction drift")
            record = {"sequence": turn.sequence, "query": query, "query_source": source,
                      "target_acquired": target in new.records,
                      "target_visible": target in inventory(turn.wire["input"])[2],
                      "search_available": search_available(turn), "variants": {}}
            original_complete = {r["record_id"] for r in variants["baseline"]["records"]
                                 if r["delivery"] == "complete"}
            for name, result in variants.items():
                assessment = delivery(result, target)
                assessment["already_visible_hits"] = sum(
                    r["record_id"] in new._visible for r in result["records"])
                complete = {r["record_id"] for r in result["records"]
                            if r["delivery"] == "complete"}
                assessment["complete_gained"] = sorted(complete - original_complete)
                assessment["complete_displaced"] = sorted(original_complete - complete)
                for item in result["records"]:
                    if item["delivery"] == "complete":
                        require(sha256_json(item["body"]) == item["record_id"], "partial body")
                assessment["retrieval"] = store.put_json(result).model_dump(mode="json")
                if name == "baseline":
                    assessment["packing"] = previous["packing"]
                else:
                    assessment["packing"] = {}
                    for level in ("lower", "central", "upper"):
                        packed, projected = pack_result(turn, result, estimator, level=level)
                        if level == "central":
                            packed["input_artifact"] = store.put_json(projected).model_dump(
                                mode="json")
                        assessment["packing"][level] = packed
                record["variants"][name] = assessment
            # This is a capability ceiling, never a fabricated model-selected next action.
            if record["variants"]["current"]["candidate"]:
                fetched = new.search(target, current_diff_hash=diff)
                record["target_exact_id_fetch_complete"] = delivery(fetched, target)["complete"]
                record["second_action_headroom"] = search_available(
                    turn, spent_calls=1, spent_actions=1)
            requests.append(record)
        sources.update({p: h for p, h in source_store.reads.items() if Path(p).is_file()})
        item = {"row": row["row_id"], "requests": requests}
        rows.append(item)
        journal.append("row_replayed", {"row": row["row_id"],
                                         "result": store.put_json(item).model_dump(mode="json")})
        print(canonical_json({"row": row["row_id"], "requests": len(requests)}), flush=True)
    require(all(sha256_bytes(Path(p).read_bytes()) == h for p, h in sources.items()),
            "immutable source changed")
    summary = {}
    requests = [r for row in rows for r in row["requests"]]
    for name in VARIANTS:
        missing = [r for r in requests if r["target_acquired"] and not r["target_visible"]]
        selected = [r["variants"][name] for r in requests]
        summary[name] = {
            "missing_opportunities": len(missing),
            "missing_candidate": sum(r["variants"][name]["candidate"] for r in missing),
            "missing_complete": sum(r["variants"][name]["complete"] for r in missing),
            "hits": sum(s["hits"] for s in selected),
            "incomplete": sum(s["incomplete"] for s in selected),
            "already_visible_hits": sum(s["already_visible_hits"] for s in selected),
            "packing_modes": dict(Counter(s["packing"]["central"]["mode"] for s in selected)),
            "fits_known_content": sum(s["packing"]["central"]["fits_known_content"]
                                       for s in selected)}
    result = {"contract": contract, "summary": summary, "rows": rows,
              "source_files": sources, "source_files_unchanged": True}
    path = output / "result.json"
    path.write_text(canonical_json(result) + "\n", encoding="utf-8")
    journal.append("experiment_completed", {"result_hash": sha256_bytes(path.read_bytes()),
                                           "source_files_verified": len(sources)})
    print(canonical_json(summary), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("manifest", "output", "baseline-source", "baseline-replay", "candidate-source",
                 "tokenizer-package", "tokenizer-cache"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.tokenizer_package.resolve()))
    os.environ["TIKTOKEN_CACHE_DIR"] = str(args.tokenizer_cache.resolve())
    import tiktoken

    def forbidden(*args, **kwargs):
        raise RuntimeError("offline history comparison forbids network connections")

    with patch("socket.socket.connect", forbidden), patch("socket.socket.connect_ex", forbidden):
        encoding = tiktoken.get_encoding("o200k_base")
        run(args, lambda text: encoding.encode(text, disallowed_special=()),
            {"package": "tiktoken", "version": tiktoken.__version__, "encoding": encoding.name})


if __name__ == "__main__":
    main()
