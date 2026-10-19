"""Fixed-candidate, provider-free comparison of execution-field bundle delivery."""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import time
from collections import Counter
from pathlib import Path
from unittest.mock import patch

from diagnostics.decision_sampler import require
from diagnostics.history_evidence_audit import coverage, native_loss_keys, source_change, validate
from diagnostics.history_evidence_bundles import LAYOUT, render, skeleton
from diagnostics.history_search_replay import pack_result, query_for
from diagnostics.size_only_replay import TokenEstimator, load_row, verify_baseline
from patchloop.artifacts import ArtifactStore
from patchloop.dev.state import DevJournal
from patchloop.runtime import repository_root, runtime_content_hash
from patchloop.util import canonical_json, sha256_bytes, sha256_json

LEVELS = ("lower", "central", "upper")
ARMS = ("bm25", "dense", "hybrid")


def summarize(rows):
    requests = [q for row in rows for q in row["requests"]]
    output = {}
    for arm in ARMS:
        variants = [q["variants"][arm] for q in requests]
        missing = [
            q["variants"][arm] for q in requests if q["target_acquired"] and not q["target_visible"]
        ]
        output[arm] = {
            "packet_returned_before_after": [
                sum(v[side + "_complete"] for v in missing) for side in ("before", "after")
            ],
            "packet_available_before_after": [
                sum(v[side + "_available"] for v in variants) for side in ("before", "after")
            ],
            "packet_gains": sum(
                not v["before_available"] and v["after_available"] for v in variants
            ),
            "packet_losses": sum(
                v["before_available"] and not v["after_available"] for v in variants
            ),
            **{
                field: sum(len(v[field]) for v in variants)
                for field in ("sources_gained", "sources_lost", "probes_gained", "probes_lost")
            },
            "additional_native_losses": [
                sum(v["additional_native_losses"][i] for v in variants) for i in range(3)
            ],
            "restored_native_exposures": [
                sum(v["restored_native_exposures"][i] for v in variants) for i in range(3)
            ],
            "delivery": dict(sum((Counter(v["delivery"]) for v in variants), Counter())),
            "packing": {
                level: dict(Counter(v["packing"][level]["mode"] for v in variants))
                for level in LEVELS
            },
            "rejected": dict(
                Counter(a["reason"] for v in variants for a in v["admissions"] if not a["admitted"])
            ),
            "max_response_chars": max(v["response_chars"] for v in variants),
            "max_input_tokens": max(
                v["packing"]["central"]["attempts"][-1]["counts_before_unknown_search_reasoning"][
                    "central"
                ]
                for v in variants
            ),
        }
    return output


def run(args, encode):
    started = time.perf_counter()
    require(not args.output.exists(), "use a fresh output directory")
    sources = {}

    def read(path, digest=None):
        data = Path(path).read_bytes()
        actual = sha256_bytes(data)
        require(digest is None or actual == digest, "artifact drift")
        sources[str(Path(path).resolve())] = actual
        return json.loads(data)

    def artifact(ref):
        return read(ref["path"], ref["content_hash"])

    manifest, prior = read(args.manifest), read(args.baseline)
    require(runtime_content_hash() == prior["contract"]["runtime_hash"], "runtime drift")
    require(
        manifest["invariants"]["references"] == 2
        and manifest["invariants"]["retained_source_chars"] == 24_000,
        "reference/source budget drift",
    )
    for name in (
        "history_evidence_bundles.py",
        "history_evidence_audit.py",
        "history_evidence_replay.py",
        "history_search_replay.py",
        "size_only_replay.py",
    ):
        path = Path(__file__).with_name(name)
        sources[str(path.resolve())] = sha256_bytes(path.read_bytes())
    sources[str(args.protocol.resolve())] = sha256_bytes(args.protocol.read_bytes())
    require(not args.output.resolve().is_relative_to(repository_root()), "external output required")
    args.output.mkdir(parents=True)
    store = ArtifactStore(args.output / "artifacts")
    journal = DevJournal(args.output, "run_dev_evidencebundles")
    contract = {
        "official": False,
        "provider_calls": 0,
        "new_spend_nanos": 0,
        "runtime_hash": runtime_content_hash(),
        "layout": LAYOUT,
        "sources": dict(sources),
        "model_query_choice": "NOT_RUN",
        "evidence_uptake": "NOT_RUN",
        "repair_success": "NOT_RUN",
        "rankings": "same saved candidate IDs, order and scores",
        "arms": ARMS,
        "guard": "no additional native losses beyond metadata floor in all three scenarios",
        "network": "socket connections blocked",
        "target": prior["contract"]["target"],
        "protocol": store.put_text(args.protocol.read_text(encoding="utf-8")).model_dump(
            mode="json"
        ),
        "tokenizer": prior["contract"]["tokenizer"],
        "search_contract": prior["contract"]["search_contract"],
    }
    journal.append("experiment_frozen", contract)
    (args.output / "manifest.json").write_text(canonical_json(contract) + "\n", encoding="utf-8")
    cases, opaque = {}, {}
    for row in manifest["rows"]:
        turns, reasoning, reads = load_row(row, prior["contract"]["after_sequence"])
        verify_baseline(turns)
        cases[row["row_id"]] = {t.sequence: t for t in turns}
        opaque.update(reasoning)
        sources.update(reads)
    estimator = TokenEstimator(encode, opaque, [t for row in cases.values() for t in row.values()])
    rows, checks = [], 0
    for old_row in prior["rows"]:
        catalog = artifact(old_row["index_records"])
        row = {"row": old_row["row"], "requests": []}
        for request in old_row["requests"]:
            turn = cases[row["row"]][request["sequence"]]
            require(query_for(turn.state)[0] == request["query"], "query drift")
            entry = {
                k: request[k]
                for k in (
                    "sequence",
                    "query",
                    "target_acquired",
                    "target_visible",
                    "search_available",
                )
            }
            entry["variants"] = {}
            for arm in ARMS:
                old = request["variants"][arm]
                baseline = artifact(old["retrieval"])
                records = {
                    r["record_id"]: catalog[r["record_id"]]["original"] for r in baseline["records"]
                }
                require(
                    all(
                        r["origin"]["first_delivered_sequence"] <= turn.sequence
                        for r in records.values()
                    ),
                    "future candidate",
                )
                cache = {}

                def packed(result, *, cache=cache, turn=turn):
                    key = sha256_json(result)
                    if key not in cache:
                        cache[key] = {
                            level: pack_result(turn, result, estimator, level=level)
                            for level in LEVELS
                        }
                    return cache[key]

                baseline_packed = packed(baseline)
                require(
                    baseline_packed["central"][0]["input_hash"]
                    == old["packing"]["central"]["input_hash"],
                    "baseline packing drift",
                )
                floor = packed(skeleton(baseline))
                floor_keys = {level: native_loss_keys(value[0]) for level, value in floor.items()}

                def accept(result, *, packed=packed, floor_keys=floor_keys):
                    trial = packed(result)
                    return all(
                        p[0]["fits_known_content"]
                        and all(
                            after <= before
                            for after, before in zip(
                                native_loss_keys(p[0]), floor_keys[level], strict=True
                            )
                        )
                        for level, p in trial.items()
                    )

                result, admissions = render(baseline, records, accept=accept)
                checks += validate(result, baseline, records)
                after_packed = packed(result)
                before_coverage = coverage(baseline_packed["central"][1], baseline, records)
                after_coverage = coverage(after_packed["central"][1], result, records)
                before_keys = native_loss_keys(baseline_packed["central"][0])
                after_keys = native_loss_keys(after_packed["central"][0])
                target = contract["target"]
                value = {
                    "before_complete": old["complete"],
                    "after_complete": any(
                        r["record_id"] == target and r["delivery"] == "complete"
                        for r in result["records"]
                    ),
                    "before_available": target in before_coverage["whole"],
                    "after_available": target in after_coverage["whole"],
                    "sources_gained": source_change(
                        before_coverage["facts"], after_coverage["facts"]
                    ),
                    "sources_lost": source_change(
                        after_coverage["facts"], before_coverage["facts"]
                    ),
                    "probes_gained": {
                        k: v
                        for k, v in after_coverage["probes"].items()
                        if k not in before_coverage["probes"]
                    },
                    "probes_lost": {
                        k: v
                        for k, v in before_coverage["probes"].items()
                        if k not in after_coverage["probes"]
                    },
                    "additional_native_losses": [
                        len(a - b) for a, b in zip(after_keys, before_keys, strict=True)
                    ],
                    "restored_native_exposures": [
                        len(b - a) for a, b in zip(after_keys, before_keys, strict=True)
                    ],
                    "retrieval": store.put_json(result).model_dump(mode="json"),
                    "admissions": admissions,
                    "response_chars": len(canonical_json(result)),
                    "delivery": dict(Counter(r["delivery"] for r in result["records"])),
                    "packing": {},
                    "floor_modes": {k: v[0]["mode"] for k, v in floor.items()},
                }
                require(
                    value["before_available"] == old["target_available"], "packet coverage drift"
                )
                for level, (packing, items) in after_packed.items():
                    if level == "central":
                        packing["input_artifact"] = store.put_json(items).model_dump(mode="json")
                    value["packing"][level] = packing
                entry["variants"][arm] = value
            row["requests"].append(entry)
            print(
                canonical_json(
                    {"row": row["row"], "sequence": turn.sequence, "replayed": len(row["requests"])}
                ),
                flush=True,
            )
        rows.append(row)
        journal.append(
            "row_replayed",
            {"row": row["row"], "result": store.put_json(row).model_dump(mode="json")},
        )
    require(
        all(sha256_bytes(Path(p).read_bytes()) == h for p, h in sources.items()), "source drift"
    )
    result = {
        "contract": contract,
        "rows": rows,
        "summary": summarize(rows),
        "exact_values_checked": checks,
        "sources": sources,
        "elapsed_seconds": time.perf_counter() - started,
    }
    (args.output / "result.json").write_text(canonical_json(result) + "\n", encoding="utf-8")
    journal.append(
        "experiment_completed", {"result": store.put_json(result).model_dump(mode="json")}
    )
    print(canonical_json(result["summary"]), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "manifest",
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
        raise RuntimeError("network disabled during evidence replay")

    with (
        patch.object(socket.socket, "connect", offline),
        patch.object(socket.socket, "connect_ex", offline),
        patch.object(socket, "create_connection", offline),
    ):
        tokenizer = tiktoken.get_encoding("o200k_base")
        run(args, lambda text: tokenizer.encode(text, disallowed_special=()))


if __name__ == "__main__":
    main()
